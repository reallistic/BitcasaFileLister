import os, logging, webbrowser, time, json
from helpers import utils
from bitcasa import BitcasaClient
from bitcasa import BitcasaException

log = logging.getLogger("BitcasaFileFetcher")

class BitcasaUtils(object):
    def __init__(self):
        self.client = None
        self.token = None
        self.client_id = None
        self.client_secret = None
        self.get_bitcasa_token()

    def get_bitcasa_token(self):
        if os.path.isfile(utils.BITCASA_TOKEN):
            try:
                with open(utils.BITCASA_TOKEN, "r") as tokenfile:
                    self.token = tokenfile.read().rstrip()
                try:
                    tokens_json = json.loads(self.token)
                except ValueError:
                    log.info("Converting bitcasa.ini")
                    log.info("If you are using a custom CLIENTID and CLIENTSECRET please put them in bitcasa.ini")
                    with open(utils.BITCASA_SAMPLE_TOKEN, "r") as sample, open(utils.BITCASA_TOKEN, "w+") as tokenfile:
                        json_sample = json.loads(sample.read())
                        self.client_id = json_sample["bitcasa"]["CLIENTID"]
                        self.client_secret = json_sample["bitcasa"]["CLIENTSECRET"]
                        json_sample["bitcasa"]["TOKEN"] = self.token
                        tokenfile.write(json.dumps(json_sample, indent=4))
                else:
                    self.client_id = tokens_json["bitcasa"]["CLIENTID"]
                    self.client_secret = tokens_json["bitcasa"]["CLIENTSECRET"]
                    self.token = tokens_json["bitcasa"]["TOKEN"]
                    if self.token:
                        log.debug("Got token")
                    else:
                        log.error("No token stored")
            except:
                log.exception("Failed to read Bitcasa token file")
        else:
            log.info("No auth token file found at %s ", os.path.abspath(utils.BITCASA_TOKEN))
        return self.token

    def create_client(self, force=False, redirect_uri=utils.REDIRECT_URI):
        if (self.token or force) and not self.client:
            self.client = BitcasaClient(self.client_id, self.client_secret, redirect_uri, self.token)
        return self.client

    def test_auth(self):
        self.create_client()
        if not self.client:
            return False
        try:
            self.client.get_user_profile()
        except BitcasaException as e:
            if e.code == 9006:
                return True
            else:
                log.exception("Error connecting to bitcasa %s" % e.code)
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
