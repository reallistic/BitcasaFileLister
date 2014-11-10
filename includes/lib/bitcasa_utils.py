import os, logging, webbrowser, time
from helpers import utils
from bitcasa import BitcasaClient
from bitcasa import BitcasaException

log = logging.getLogger("BitcasaFileFetcher")

class BitcasaUtils(object):
    def __init__(self):
        self.client = None
        self.token = None
        self.get_bitcasa_token()

    def get_bitcasa_token(self):
        if os.path.isfile(utils.BITCASA_TOKEN):
            try:
                with open(utils.BITCASA_TOKEN, "r") as tokenfile:
                    self.token = tokenfile.read()
            except:
                log.exception("Failed to read Bitcasa token file")
        else:
            log.info("No auth token file found at %s ", os.path.abspath(utils.BITCASA_TOKEN))
        return self.token

    def create_client(self, force=False, redirect_uri=utils.REDIRECT_URI):
        if (self.token or force) and not self.client:
            self.client = BitcasaClient(utils.CLIENTID, utils.CLIENTSECRET, redirect_uri, self.token)
        return self.client

    def test_auth(self):
        self.create_client()
        if not self.client:
            return False
        try:
            self.client.get_folder("/")
        except:
            return False
        else:
            return True

    def do_oauth(self):
        if not self.client:
            self.create_client(True)
        log.info("Please navigate to the following url:")
        log.info(self.client.login_url)
        time.sleep(3)
        webbrowser.open(self.client.login_url)