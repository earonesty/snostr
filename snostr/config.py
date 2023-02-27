import json
import os.path
import yaml


class Config:
    debug = False
    twitter: str = None
    npriv: str = None
    expire_days: float = 7

    # saved keys
    _saved = ("debug", "twitter", "npriv", "expire_days")

    prune_follows = True
    force_follows = False
    config_dir: str = "~/.config/snostr"
    save = False
    show = False

    def __init__(self, **kws):
        self.__dict__.update(kws)
        self.__cdir = os.path.expanduser(os.path.join(self.config_dir))
        uid, pwd = self.twitter.split(":", 1)
        self.__twitter_user = uid
        self.__twitter_password = pwd

    @staticmethod
    def add_args(parser):
        parser.add_argument("--config-dir", "-c", help="Storage & config directory", default=Config.config_dir)
        parser.add_argument("--twitter", "-t", help="Twitter username:password")
        parser.add_argument("--npriv", "-k", help="Nostr private key file")
        parser.add_argument("--debug", "-D", help="Debug mode", default=False, action="store_true")

        parser.add_argument("--save", "-s", help="Save args from cli", action="store_true")
        parser.add_argument("--show", help="Show config", action="store_true")

    def get_path(self, base=None):
        if not base:
            return self.__cdir
        return os.path.join(self.__cdir, base)

    @classmethod
    def from_args(cls, args):
        conf = cls.read_config(args)
        return cls(**conf)

    @staticmethod
    def get_filename(config_dir):
        return os.path.expanduser(os.path.join(config_dir, "conf"))

    def __repr__(self):
        conf = {k: v for k, v in self.__dict__.items() if k[0] != "_"}
        return f"Config({conf})"

    def save_config(self):
        self.ensure_config_dir()
        filename = self.get_filename(self.config_dir)
        with open(filename, "w") as fp:
            yaml.dump({k: v for k, v in self.__dict__.items() if k in self._saved}, fp)

    @classmethod
    def read_config(cls, args):
        filename = cls.get_filename(args["config_dir"])

        try:
            with open(filename, "r") as fp:
                try:
                    conf = yaml.safe_load(fp)
                except ValueError:
                    conf = json.load(fp)
        except FileNotFoundError:
            conf = {}

        conf.update({k: v for k, v in args.items() if v is not None})

        return conf

    @property
    def twitter_user(self):
        return self.__twitter_user

    @property
    def twitter_password(self):
        return self.__twitter_password

    def ensure_config_dir(self):
        os.makedirs(self.get_path(), exist_ok=True)
