import httplib2, webbrowser, sys, time, logging, os
sys.path.insert(1, "BitcasaFileFetcher/lib/")
from datetime import datetime
from googleapiclient import errors
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from oauth2client.client import OAuth2WebServerFlow, AccessTokenRefreshError, flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow as RunFlow
from helpers import utils

log = logging.getLogger("BitcasaFileFetcher")
logger = logging.getLogger("oauth2client.util")
logger.setLevel(logging.CRITICAL)

GRDIVE_SECRETS = "gdrive_secrets.ini"
REDIRECT_URI = "https://rose-llc.com/bitcasafilelist/google/"
OAUTH_SCOPE = "https://www.googleapis.com/auth/drive"

class GoogleDrive(object):
    """Wrapper to the google drive api"""
    def __init__(self):
        self.storage = None
        self.credentials = None
        self.http = None
        self.service = None
        self.get_credentials()

    def get_credentials(self):
        if self.storage is None:
            self.storage = Storage(utils.GDRIVE_CREDS)
        
        self.credentials = self.storage.get()
        return self.credentials

    def test_auth(self, file_id="root"):
        try:
            root = self.get_service().files().get(fileId=file_id).execute()
        except:
            log.exception("Couldn't connect to Google drive")
            return False
        else:
            return True


    def upload_file(self, filepath, filename, parent="root"):
        try:
            media_body = MediaFileUpload(filepath, resumable=True, mimetype="", chunksize=-1)
            body = {
                'title': filename,
                'parents': [{'id': parent}],
                'mimeType': ""
            }

            return self.get_service().files().insert(body=body, media_body=media_body).execute()
        except:
            log.exception("Error uploading file %s", filepath)
            return False


    def check_file_exists(self, filename, parent="root"):
        try:
            children = self.get_service().children().list(folderId=parent, q="title = '%s'" % filename).execute()
            items = children.get('items', [])
            original = None
            for child in items:
                child_file = self.get_service().files().get(fileId=child["id"]).execute()
                if original is None:
                    original = child_file
                else:
                    o = time.strptime(original["createdDate"], "%Y-%d-%mT%H:%M:%S.%fZ")
                    t = time.strptime(child_file["createdDate"], "%Y-%d-%mT%H:%M:%S.%fZ")
                    if t < o:
                        original = child_file
            if original is None:
                return False
            else:
                return original
        except errors.HttpError:
            log.exception("Error checking for file")
            return None

    def delete_filebyname(self, filename, parent="root"):
        myfile = self.check_file_exists(filename, parent=parent)
        retriesleft = 3
        while myfile is None and retriesleft > 0:
            time.sleep(10)
            retriesleft -= 1
            if retriesleft > 0:
                myfile = self.check_file_exists(filename, parent=parent)
            else:
                log.error("Error checking if file exists. Will retry %s more times", retriesleft)
                return False
        if myfile:
            log.debug("deleting file %s", filename)
            self.delete_file(myfile["id"])
        else:
            log.debug("Could find file %s to delete", filename)


    def need_to_upload(self, filename, folder_id, size_bytes):
        if size_bytes <= 0:
            return False
        myfile = self.check_file_exists(filename, parent=folder_id)
        retriesleft = 3
        while myfile is None and retriesleft > 0:
            time.sleep(10)
            retriesleft -= 1
            if retriesleft > 0:
                myfile = self.check_file_exists(filename, parent=folder_id)
            else:
                log.error("Error checking if file exists. Will retry %s more times", retriesleft)
                return False
        if myfile and int(myfile["fileSize"]) == size_bytes:
            return False
        elif myfile:
            log.debug("Filesize incorrect deleting", filename)
            self.delete_file(myfile["id"])
            return True
        else:
            return True

    def get_folder_byname(self, foldername, parent="root", createnotfound=False):
        try:
            children = self.get_service().children().list(folderId=parent, q="title = '%s' and mimeType = 'application/vnd.google-apps.folder'" % foldername).execute()
            items = children.get('items', [])
            
            original = None
            for child in items:
                child_file = self.get_service().files().get(fileId=child["id"]).execute()
                if original is None:
                    original = child_file
                else:
                    o = time.strptime(original["createdDate"], "%Y-%d-%mT%H:%M:%S.%fZ")
                    t = time.strptime(child_file["createdDate"], "%Y-%d-%mT%H:%M:%S.%fZ")
                    if t < o:
                        original = child_file

            if original is None:
                if createnotfound:
                    log.info("No items by the name of %s found. Creating", foldername)
                    body = {
                        'title': foldername,
                        'mimeType':'application/vnd.google-apps.folder'
                    }
                    if parent != "root":
                        body['parents'] = [{'id':parent}]
                    return self.get_service().files().insert(body=body).execute()
                else:
                    log.info("No items by the name of %s found", foldername)
                    return False
            else:
                return original
        except errors.HttpError:
            log.exception("Error getting or creating folder")
            return None


    def delete_file(self, fileid):
        try:
            self.get_service().files().delete(fileId=fileid)
        except errors.HttpError:
            log.exception("Error deleting file")
            return False

    @property
    def token_expired(self):
        if self.credentials is None:
            return True
        return self.credentials.access_token_expired

    def auth(self, promptForAuth):
        """Authorize an http client, asking the user if required.
        """
        if self.token_expired:
            if self.can_token_refresh:
                log.debug("Trying to refresh auth token")
                try:
                    self.credentials.refresh(self.http)
                except:
                    log.debug("Auth token refresh failed. New auth needed")
                    self.credentials = None
                    if promptForAuth:
                        self.get_service(True)
                    else:
                        raise
            elif promptForAuth:
                flow = flow_from_clientsecrets(utils.GDRIVE_SECRETS, scope='https://www.googleapis.com/auth/drive')
                flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
                flow.params['access_type'] = 'offline'
                flow.params['approval_prompt'] = 'force'
                url = flow.step1_get_authorize_url()
                webbrowser.open(url)
                code = raw_input("Enter token ")
                self.credentials = flow.step2_exchange(code)
            else:
                raise AccessTokenRefreshError("Access token unable to refresh please re-authenticate")
            log.info("Storing Google credentials")
            self.storage.put(self.credentials)
        self.credentials.authorize(self.http)

    @property
    def can_token_refresh(self):
        return self.credentials is not None and self.credentials.refresh_token is not None

    def get_service(self, promptForAuth=False):
        if self.service is None or self.token_expired:
            if self.http is None:
                self.http = httplib2.Http()
            self.auth(promptForAuth)
            self.service =  build('drive', 'v2', http=self.http)

        return self.service

if __name__ == '__main__':
    g = GoogleDrive()
    try:
        root = g.get_service(True).files().get(fileId="root").execute()
    except:
        log.exception("Error connecting to Google drive")
        sys.exit(2)
    else:
        log.info("Successfully connected to Google drive")
    