from snostr.config import Config
from snostr.manager import Manager, Nostr


def test_scrape_nip5():
    np = Manager.scrape_nip5("sldfkjdsk simul@nostrplebs.com sdfdsf@ . df@")
    assert np == "3ef7277dc0870c8c07df0ee66829928301eb95785715a14f032aca534862bae0"


def test_scrape_npub():
    np = Manager.scrape_npub("vv#npub18mmjwlwqsuxgcp7lpmnxs2vjsvq7h9tc2u26zncr9t99xjrzhtsqwx4vcz !")
    assert np == "3ef7277dc0870c8c07df0ee66829928301eb95785715a14f032aca534862bae0"


def test_nostr_connect():
    conf = Config.from_args({"config_dir": "~/.config/snostr"})
    nostr = Nostr(conf)
    nostr.connect()
    nostr.get_contacts()
    assert len(nostr.contacts) > 20
