import queue
import random
import re
import threading
import time
import json
import uuid
from typing import TYPE_CHECKING, Optional
import logging as log

import nostr
from nostr.event import EventKind, Event
from nostr.filter import Filters, Filter
from nostr.key import PublicKey
from nostr.relay_manager import RelayManager

import requests

from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

if TYPE_CHECKING:
    from snostr.config import Config


class QUEUE_DONE:
    pass


class Nostr:
    def __init__(self, config: "Config"):
        self.follows = set()
        self.need_pub = False
        self.config = config
        self.privk = nostr.key.PrivateKey.from_nsec(self.config.npriv)
        self.pubk = self.privk.public_key
        self.prof_sub = uuid.uuid4().hex
        self.relay = RelayManager()
        self.contacts = None
        self.contacts_event = None
        self.contacts_for_relay = {}
        self.contact_timeout = 0
        self.contacts_last = -1
        
        self.connect()

    def connect(self):
        log.debug("connecting to nostr relays")
        self.relay.add_relay("wss://nostr-pub.wellorder.net")
        self.relay.add_relay("wss://relay.damus.io")
        self.relay.add_relay("wss://relay.nostr.vision")
        filters = Filters([Filter(kinds=[EventKind.CONTACTS],
                                  authors=[self.pubk.hex()])])
        self.relay.add_subscription_on_all_relays(self.prof_sub, filters)
        # 5 seconds to get best old contact list
        self.contact_timeout = time.monotonic() + 10

    def get_contacts(self):
        log.debug("getting existing contacts")
        while time.monotonic() < self.contact_timeout:
            if self.relay.message_pool.has_events():
                event_msg = self.relay.message_pool.get_event()
                if event_msg.event.kind == EventKind.CONTACTS:
                    log.info("got %d contacts from %s", len(event_msg.event.tags), event_msg.url)
                    self.contacts_for_relay[event_msg.url] = event_msg.event.tags
                    if event_msg.event.created_at > self.contacts_last:
                        self.contacts = event_msg.event.tags
                        self.contacts_event = event_msg.event
                        self.contacts_last = event_msg.event.created_at
            if not self.relay.message_pool.has_events():
                time.sleep(0.25)
        log.debug("done getting existing contacts")
        assert self.contacts_event

    def close(self):
        self.relay.close_subscription_on_all_relays(self.prof_sub)
        time.sleep(2)
        self.relay.close_all_relay_connections()

    def follow_hex(self, hex_pub):
        self.follows.add(hex_pub)

    def update_contacts(self):
        key_set = {contact[1] for contact in self.contacts}
        newcnt = 0
        for hex_pub in self.follows:
            if hex_pub not in key_set:
                newcnt += 1
                self.contacts.append(["p", hex_pub])
                self.need_pub = True
        compressed = []
        dups = set()
        for contact in self.contacts:
            if contact[1] in dups:
                log.debug("eliminating dups")
                self.need_pub = True
                continue
            dups.add(contact[1])
            compressed.append(contact)
        self.contacts = compressed

        log.info("%s new follows", newcnt)

    def publish_contacts(self):
        if not self.follows:
            log.debug("no scraped follows")
            return
        time.sleep(3)
        self.get_contacts()
        self.update_contacts()
        if self.need_pub:
            log.info("publishing %s contacts", len(self.contacts))
            ev = Event(kind=EventKind.CONTACTS, tags=self.contacts, content=self.contacts_event.content)
            self.privk.sign_event(ev)
            for url, relay in self.relay.relays.items():
                relay.publish(ev.to_message())

            # wait for publish
            time.sleep(3)

            while self.relay.message_pool.has_notices():
                self.relay.message_pool.get_notice()

class Manager:
    def __init__(self, config: "Config"):
        self.nostr: Optional[Nostr] = None
        self.config = config
        self.config.ensure_config_dir()
        self.twitter_state = {}
        self.load_twitter_state()
        self.nostr = Nostr(self.config)
        self.__browser = None
        self.__twitter_logged_in = False

    def browser(self):
        if not self.__browser:
            # todo, other drivers
            from webdriver_manager.chrome import ChromeDriverManager
            options = Options()
            options.add_argument("--headless")
            self.__browser = webdriver.Chrome(executable_path=ChromeDriverManager().install(), options=options)
        return self.__browser

    def load_twitter_state(self):
        self.twitter_state = self.load_state("twitter")

    def twitter_login(self):
        if self.__twitter_logged_in:
            return
        log.debug("logging in to twitter to get followers")
        self.browser.get("https://twitter.com/login")
        time.sleep(random.uniform(0.5, 2))
        inp = self.wait_for(lambda: self.browser.find_element(By.XPATH, "//input[@autocomplete='username']"), 5)
        assert inp, "no login form found"
        next_button = self.browser.find_element(By.XPATH, "//span[text()[contains(.,'Next')]]")
        assert next_button, "no next button found"
        inp.send_keys(self.config.twitter_user)
        next_button.click()
        pwd = self.wait_for(lambda: self.browser.find_element(By.XPATH, "//input[@type='password']"), 2)
        assert pwd, "no password input found"
        pwd.send_keys(self.config.twitter_password)
        time.sleep(random.uniform(0.1, 0.25))
        pwd.send_keys(Keys.ENTER)
        assert self.wait_for(lambda: not self.browser.find_element(By.XPATH, "//input[@type='password']"), 5,
                             invert=True)
        time.sleep(random.uniform(0.1, 0.25))
        log.debug("login worked")
        self.__twitter_logged_in = True

    def load_state(self, name):
        try:
            with open(self.config.get_path(name)) as fh:
                return json.load(fh)
        except FileNotFoundError:
            return {}

    def save_state(self, obj, name):
        with open(self.config.get_path(name), "w") as fh:
            json.dump(obj, fh)

    def already_seen(self, follower):
        if self.twitter_state_has_follower(follower):
            npub, last = self.get_twitter_follower_state(follower)
            if not last:
                return False
            # allow refresh after a week or whatever
            if time.time() > last + self.config.expire_days * 86400:
                return False
            return True
        return False

    def get_twitter_follower_state(self, follower):
        return self.twitter_state.get("follows", {})[follower]

    def set_twitter_follower_state(self, follower, state):
        self.twitter_state.setdefault("follows", {})[follower] = state

    def auto_follow_twitter(self):
        for follower in self.get_twitter_follows():
            if not self.already_seen(follower):
                self.twitter_login()
                npub = self.scrape_twitter_bio(follower)
                self.set_twitter_follower_state(follower, (npub, time.time()))
                self.save_twitter_state()
                continue
            else:
                npub, _ = self.get_twitter_follower_state(follower)

            if not npub:
                continue

            self.nostr_follow(npub)
        self.nostr.publish_contacts()
        self.nostr.close()

    def save_twitter_state(self):
        self.save_state(self.twitter_state, "twitter")

    def get_twitter_follows(self):
        expire_days = self.config.expire_days
        if self.config.force_follows:
            log.debug("force get follows")
            expire_days = 0
        if self.twitter_state.get("last_got_follows", 0) > (time.time() - (expire_days * 86400)):
            log.debug("not getting latest follows, recent enough")
            return self.twitter_state["follows"]
        self.twitter_login()
        ret = self.scrape_twitter_following()
        self.twitter_state["last_got_follows"] = time.time()
        if self.config.prune_follows:
            self.twitter_state["follows"] = {k: v for k, v in self.twitter_state["follows"].items() if k in ret}
        self.save_twitter_state()
        return self.twitter_state["follows"]

    def scrape_twitter_following(self):
        time.sleep(random.uniform(1, 2))
        log.debug("getting follows")
        self.browser.get("https://twitter.com/" + self.config.twitter_user + "/following")
        time.sleep(random.uniform(2, 3))
        i = 0
        # max pages 1000
        res = set()
        nothing = 0
        while i < 1000:
            try:
                txts = self.get_all_text(By.TAG_NAME, "a")
            except StaleElementReferenceException:
                time.sleep(random.uniform(1, 2))
                txts = self.get_all_text(By.TAG_NAME, "a")
            new_res = 0
            for foll in txts:
                if not foll:
                    continue
                foll = foll.strip()
                if foll[0] != "@":
                    continue
                foll = foll.lstrip("@")
                if foll == self.config.twitter_user:
                    continue
                if foll in res:
                    continue
                res.add(foll)
                new_res += 1
                if foll not in self.twitter_state:
                    self.set_twitter_follower_state(foll, (None, None))
            i = i + 1
            log.debug("follows: new=%s, tot=%s, page=%s", new_res, len(res), i)
            if new_res == 0:
                nothing += 1
                if nothing >= 10:
                    log.debug("no more follows from scrolling")
                    break
            else:
                nothing = 0
            log.debug("scrolling")
            self.browser.execute_script("window.scrollTo(0,document.body.scrollHeight)")
            time.sleep(random.uniform(1, 2))
        return res

    def scrape_twitter_bio(self, follower: str) -> Optional[str]:
        log.debug("getting bio for %s", follower)
        self.browser.get("https://twitter.com/" + follower)
        time.sleep(random.uniform(1, 2))

        txts = self.get_all_text(By.TAG_NAME, "span")

        for txt in txts:
            if "npub" in txt:
                log.debug("got npub for %s", follower)
                return self.scrape_npub(txt)
            if "@" in txt:
                npub = self.scrape_nip5(txt)
                if npub:
                    return npub

    @staticmethod
    def scrape_npub(maybe):
        found = re.search(r"(npub\w+)", maybe)
        if not found:
            return None
        try:
            return PublicKey.from_npub(found[1]).hex()
        except TypeError:
            log.debug("invalid npub: %s", found[1])
            return None

    @staticmethod
    def scrape_nip5(maybe):
        maybe = maybe.strip()
        match = re.search(r"([^@\s]+@\S+[.]\S+)", maybe)
        if not match:
            return None
        maybe = match[1]
        split = maybe.split("@", 1)
        if len(split) != 2:
            return None
        name, base = split
        if not name or not base:
            return None
        log.debug("try nip5 for %s", maybe)
        try:
            res = requests.get(f"https://{base}/.well-known/nostr.json?name={name}", timeout=2)
        except requests.RequestException:
            return None
        if res.status_code != 200:
            return None
        try:
            js = res.json()
            if not js:
                return None
        except requests.exceptions.JSONDecodeError:
            return None
        ret = js.get("names", {}).get(name)
        log.debug("got nip5: '%s'", ret)
        return ret

    def nostr_follow(self, npub: str):
        self.nostr.follow_hex(npub)

    @staticmethod
    def wait_for(func, timeout, invert=False):
        ret = None
        start = time.monotonic()
        while not ret:
            time.sleep(0.1)
            try:
                ret = func()
            except NoSuchElementException:
                ret = None
                if invert:
                    return True
            if ret or time.monotonic() > (start + timeout):
                break
        return ret or invert

    def get_all_text(self, by, arg):
        try:
            return [link.text for link in self.browser.find_elements(by, arg)]
        except StaleElementReferenceException:
            time.sleep(random.uniform(1, 2))
            return [link.text for link in self.browser.find_elements(by, arg)]

    def twitter_state_has_follower(self, follower):
        return follower in self.twitter_state.get("follows", {})
