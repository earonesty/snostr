import argparse
import logging

from snostr.config import Config
from snostr.manager import Manager

log = logging.getLogger("snostr")

def get_config():
    parser = argparse.ArgumentParser(
        prog = 'snostr',
        description = 'Social network scrape + nostr integration',
    )

    Config.add_args(parser)

    args = parser.parse_args()
    
    config = Config.from_args(vars(args))

    if config.debug:
        logging.getLogger().setLevel(logging.DEBUG)

        # too noisy
        logging.getLogger("selenium").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.INFO)
        logging.getLogger("urllib3").setLevel(logging.INFO)

    return config


def main():
    config = get_config()
    
    if config.save:
        config.save_config()
        return

    if config.self_test:
        try:
            manager = Manager(config)
            manager.browser.get("https://www.google.com")
        finally:
            manager.close()
        return

    did = False

    if config.twitter:
        try:
            manager = Manager(config)
            manager.auto_follow_twitter()
            log.debug("done auto follow twitter")
        finally:
            log.debug("quit browser")
            manager.close()
        did=True

    if not did:
        print("Nothing to do")
        
if __name__ == "__main__":
    main()
