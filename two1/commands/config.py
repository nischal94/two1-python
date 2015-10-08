import sys
import json

import os
import click
import pkg_resources
from codecs import open
from path import path
from two1.lib.blockchain.twentyone_provider import TwentyOneProvider
from two1.lib.wallet.two1_wallet import Two1Wallet
from two1.lib.wallet import test_wallet
from two1.lib.util.uxstring import UxString

TWO1_USER_FOLDER = os.path.expanduser('~/.two1/')
TWO1_CONFIG_FILE = path(TWO1_USER_FOLDER + 'two1.json')
TWO1_API_HOST = "https://djangobitcoin-devel-e0ble.herokuapp.com"
TWO1_PROD_HOST = "https://dotco-devel-pool2.herokuapp.com"
TWO1_DEV_HOST = "http://127.0.0.1:8000"
TWO1_PYPI_HOST = "https://pypi-3844.21.co"
TWO1_PACKAGE_NAME = "two1"
try:
    TWO1_VERSION = pkg_resources.require("two1")[0].version
except:
    TWO1_VERSION = "undefined"

try:
    TWO1_PATH = os.path.dirname(sys.argv[0])
except:
    TWO1_PATH = None


def str2bool(v):
    return str(v).lower() in ("yes", "true", "t", "1", "on")

# override variables based on environment settings
# if TWO1_DEV is set, we will switch to DEV mode with the following changes
# 1) set the TWO1_HOST to TWO1_DEV_HOST (127.0.0.1:8000) or TWO1_DEV_HOST
#    from the environment
# if TWO1_DEV is not set, use TWO1_PROD_HOST
if str2bool(os.environ.get("TWO1_DEV", default="0")):
    click.echo(click.style("Setting up developer environment.", fg="red"))
    TWO1_HOST = os.environ.get("TWO1_DEV_HOST", default=TWO1_DEV_HOST)
    click.echo("Host: {}".format(TWO1_HOST))
else:
    TWO1_HOST = TWO1_PROD_HOST

'''Primary use case for the following class is the singleton that holds
   all the state & config data required to run commands and subcommands
   for two1 app
'''


class Config(object):

    def __init__(self, config_file=TWO1_CONFIG_FILE, config=None):
        if not os.path.exists(TWO1_USER_FOLDER):
            os.makedirs(TWO1_USER_FOLDER)
        self.file = path(config_file).expand().abspath()
        self.dir = self.file.parent
        self.defaults = {}
        self.load()
        # override config variables
        if config:
            for k, v in config:
                self.defaults[k] = v

        if self.verbose:
            self.vlog("Applied manual config.")
            for k, v in config:
                self.vlog("  {}={}".format(k, v))

        # add wallet object
        if self.defaults.get('testwallet', None) == 'y':
            self.wallet = test_wallet.TestWallet()
        else:
            dp = TwentyOneProvider(TWO1_HOST)

            if not Two1Wallet.is_configured():
                # configure wallet with default options
                click.pause(UxString.create_wallet)

                if not Two1Wallet.configure({'data_provider': dp}):
                    raise click.ClickException(UxString.Error.create_wallet_failed)
                click.pause(UxString.create_wallet_done)

            wallet_path = Two1Wallet.DEFAULT_WALLET_PATH
            self.wallet = Two1Wallet(params_or_file=wallet_path,
                                     data_provider=dp)

    # pulls attributes from the self.defaults dict
    def __getattr__(self, name):
        if name in self.defaults:
            return self.defaults[name]
        else:
            # Default behaviour
            raise AttributeError

    def save(self):
        """Save config file, handling various edge cases."""
        if not self.dir.exists():
            self.dir.mkdir()
        if self.file.isdir():
            print("self.file=" + self.file)
            self.file.rmdir()
        with open(self.file + ".tmp", mode="w", encoding='utf-8') as fh:
            json.dump(self.defaults, fh, indent=2, sort_keys=True)
        # move file if successfully written
        os.rename(self.file + ".tmp", self.file)
        return self

    def load(self):
        """Load config from (1) self.file if extant or (2) from defaults."""
        if self.file.exists() and self.file.isfile():
            try:
                with open(self.file, mode="r", encoding='utf-8') as fh:
                    self.defaults = json.load(fh)
            except:
                print(UxString.Error.file_load % self.file)
                self.defaults = {}

        defaults = dict(username=None,
                        sellprice=10000,
                        contact="two1@21.co",
                        stdout=".two1/two1.stdout",
                        stderr=".two1/two1.stderr",
                        bitin=".bitcoin/wallet.dat",
                        bitout=".bitcoin/wallet.dat",
                        sortby="price",
                        maxspend=20000,
                        verbose=False,
                        mining_auth_pubkey=None,
                        auto_update=False)

        save_config = False
        for key, default_value in defaults.items():
            if key not in self.defaults:
                self.defaults[key] = default_value
                save_config = True

        if save_config:
            self.save()

        return self

    def update_key(self, key, value):
        self.defaults[key] = value
        # might be better to switch to local sqlite for persisting
        # the config
        # self.save()

    # kwargs is styling parameters
    def log(self, msg, *args, **kwargs):
        """Logs a message to stderr."""
        if args:
            msg %= args
        if len(kwargs) > 0:
            out = click.style(msg, **kwargs)
        else:
            out = msg
        click.echo(out, file=sys.stderr)

    def vlog(self, msg, *args):
        """Logs a message to stderr only if verbose is enabled."""
        if self.verbose:
            self.log(msg, *args)

    def log_purchase(self, **kwargs):
        # simple logging to file
        # this can be replaced with pickle/sqlite
        return

    def get_purchases(self):
        # read all right now. TODO: read the most recent ones only
        return []

    def fmt(self):
        pairs = []
        for key in sorted(self.defaults.keys()):
            pairs.append("%s: %s" % (key, self.defaults[key]))
        out = "file: %s\n%s\n""" % (self.file, "\n".join(sorted(pairs)))
        return out

    def __repr__(self):
        return "<Config\n%s>" % self.fmt()

# IMPORTANT: Suppose you want to invoke a command as a function
# for the purpose of testing, eg:
#
# >>> from two1.commands.search import search
# >>> search(silent=True)    
# 
# Then you *may* need to pass ensure=True and make sure that Config can
# self-initialize to a reasonable state purely with default arguments.
#
# The alternative is to make each command itself a thin wrapper around
# a library call with proper defaults (eg search calling search_lib).
# This will work only so long as we don't really need the config
# object within search_lib.
#
# For further details:
# http://click.pocoo.org/5/complex/#ensuring-object-creation
pass_config = click.make_pass_decorator(Config, ensure=False)