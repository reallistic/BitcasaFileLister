import httplib2, webbrowser, sys
from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from oauth2client.client import OAuth2WebServerFlow, AccessTokenRefreshError
from oauth2client.file import Storage
from apiclient import errors
from datetime import datetime
import time
import logging
from logger import logger as log
logger = logging.getLogger("oauth2client.util")
logger.setLevel(logging.CRITICAL)

CLIENT_ID = '209996072777-uqfb5rt8acelm9isq225ljrls85jb7dl.apps.googleusercontent.com'
CLIENT_SECRET = 'nc_lKEIwyE3iXKy0fNiLP699'

OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'
REDIRECT_URI = 'https://rose-llc.com/bitcasafilelist/google/'

class GoogleDrive(object):
    """Wrapper to the google drive api"""
    def __init__(self):
        self.credentials = GoogleDrive.get_credentials()
        

    @staticmethod
    def authorize_token(code, flow=None):
        if flow is None:
            flow = OAuth2WebServerFlow(CLIENT_ID, CLIENT_SECRET, OAUTH_SCOPE, REDIRECT_URI)
        credentials = flow.step2_exchange(code)
        storage = Storage('gdrive.ini')
        try:
            storage.put(credentials)
        except RuntimeError as e:
            log.error("Error storing credentials")
            log.error(e)
        else:
            log.info("Stored google drive credentials Successfully")
        

    @staticmethod
    def do_oauth():
        flow = OAuth2WebServerFlow(CLIENT_ID, CLIENT_SECRET, OAUTH_SCOPE, REDIRECT_URI)
        url = flow.step1_get_authorize_url()
        log.info(url)
        webbrowser.open(url)
        code = raw_input("Enter token ")
        GoogleDrive.authorize_token(code, flow)

    @staticmethod
    def get_credentials():
        storage = Storage('gdrive.ini')
        credentials = storage.get()
        return credentials

    def test_auth(self, folder_id="root"):
        try:
            http = httplib2.Http()
            http = self.credentials.authorize(http)

            drive_service = build('drive', 'v2', http=http)
            drive_service.children().list(folderId=folder_id).execute()
        except (errors.HttpError, AccessTokenRefreshError):
            log.exception("Connection test failed")
            return False
        except:
            log.exception("Connection test failed")
            return False
        else:
            log.info("Connection test successfull")
            return True


    def upload_file(self, filepath, filename, parent="root"):
        try:
            http = httplib2.Http()
            http = self.credentials.authorize(http)

            drive_service = build('drive', 'v2', http=http)

            media_body = MediaFileUpload(filepath, resumable=True, mimetype="")
            body = {
                'title': filename,
                'parents': [{'id': parent}],
                'mimeType': ""
            }

            drive_service.files().insert(body=body, media_body=media_body).execute()
            return True
        except:
            log.exception("Error uploading file %s", filepath)
            return False


    def check_file_exists(self, filename, parent="root"):
        try:
            http = httplib2.Http()
            http = self.credentials.authorize(http)

            drive_service = build('drive', 'v2', http=http)
            children = drive_service.children().list(folderId=parent, q="title = '%s'" % filename).execute()
            items = children.get('items', [])
            original = None
            for child in items:
                child_file = drive_service.files().get(fileId=child["id"]).execute()
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
            self.delete_file(myfile["id"])


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
            self.delete_file(myfile["id"])
            return True
        else:
            return True

    def get_folder_byname(self, foldername, parent="root", createnotfound=False):
        try:
            http = httplib2.Http()
            http = self.credentials.authorize(http)

            drive_service = build('drive', 'v2', http=http)
            children = drive_service.children().list(folderId=parent, q="title = '%s' and mimeType = 'application/vnd.google-apps.folder'" % foldername).execute()
            items = children.get('items', [])
            
            original = None
            for child in items:
                child_file = drive_service.files().get(fileId=child["id"]).execute()
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
                    return drive_service.files().insert(body=body).execute()
                else:
                    log.info("No items by the name of %s found", foldername)
                    return None
            else:
                return original
        except errors.HttpError:
            log.exception("Error getting or creating folder")
            return None


    def delete_file(self, fileid):
        try:
            http = httplib2.Http()
            http = self.credentials.authorize(http)

            drive_service = build('drive', 'v2', http=http)
            drive_service.files().delete(fileId=fileid)
        except errors.HttpError:
            log.exception("Error deleting file")
            return False


if __name__ == '__main__':
    g = GoogleDrive()
    if "--oauth" in sys.argv or not g.credentials or not g.test_auth():
        GoogleDrive.do_oauth()
    else:
        print "auth already available"
