import argparse
import logging

from snostr.config import Config
from snostr.manager import Manager

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
        logging.getLogger("selenium").setLevel(logging.INFO)
        logging.getLogger("requests").setLevel(logging.INFO)
        logging.getLogger("urllib3").setLevel(logging.INFO)

    return config


def main():
    config = get_config()
    
    if config.save:
        config.save_config()
        return

    if config.twitter:
        manager = Manager(config)
        manager.auto_follow_twitter()

        
if __name__ == "__main__":
    main()
