import sys, logging
from lib import bottle, cherrypy, BitcasaUtils
from lib.bottle import route, run, request, get, post, template, response, view, static_file, redirect
from lib.bitcasa import BitcasaException, BitcasaFile
from helpers import utils
bottle.TEMPLATE_PATH.insert(0,'BitcasaFileLister/views/')

log = logging.getLogger("BitcasaFileLister")

@route('/static/<filepath:path>')
def static(filepath):
    return static_file(filepath, root='BitcasaFileLister/statics/')

@route('/')
def welcome():
    """Show welcome screen"""
    redirect("/bitcasafilelister")

@route('/bitcasafilelister')
@route('/bitcasafilelister/')
def show_bitcasa_files():
    """List files in bitcasa"""
    authorization_code = request.query.authorization_code
    is_error = request.query.error
    is_error = is_error.lower() == "true"
    bitcasa_utils = BitcasaUtils()
    if bitcasa_utils.test_auth():
        auth_name="View Files"
        auth_url="/bitcasafilelister/files/"
        msg = "You access token is stored locally. To retrieve base64 paths click view files below"
    else:
        auth_name="Login"
        auth_url="/bitcasafilelister/auth/"
        msg = "Your authentication token is either invalid or not set. Please set one by logging in. After authentication, you will also be able to view your files"
    return template("bitcasafilelister", is_error=is_error, error_msg="",
                        authorization_code=authorization_code, auth_url=auth_url,
                        auth_name=auth_name, msg=msg)

@route('/bitcasafilelister/files')
@route('/bitcasafilelister/files<base64:path>')
def list_bitcasa_files(base64="/"):
    bitcasa_utils = BitcasaUtils()
    client = bitcasa_utils.create_client()
    if not client:
        redirect("../auth")
    else:
        if not base64:
            base64 = "/"
        try:
            folder = client.get_folder(base64)
        except BitcasaException as e:
            if bitcasa_utils.test_auth():
                auth_name="View Files"
                auth_url="/bitcasafilelister/files/"
                msg = "You access token is stored locally. To retrieve base64 paths click view files below"
            else:
                auth_name="Login"
                auth_url="/bitcasafilelister/auth/"
                msg = "Your authentication token is either invalid or not set. Please set one by logging in. After authentication, you will also be able to view your files"

            return template("bitcasafilelister", is_error=True, error_msg=e,
                        auth_url=auth_url, authorization_code="",
                        auth_name=auth_name, msg=msg)
        parent_path = folder.path[:folder.path.rfind('/')]
        if not parent_path:
            parent_path = "/"
        download_url = "https://developer.api.bitcasa.com/v1/files/"
        return template("fileslist", folder=folder, access_token=client.access_token,
                        parent_path=parent_path, download_url=download_url, BitcasaFile=BitcasaFile)

@route('/bitcasafilelister/auth')
@route('/bitcasafilelister/auth/')
def do_bitcasa_auth():
    authorization_code = request.query.authorization_code
    bitcasa_utils = BitcasaUtils()
    client = bitcasa_utils.create_client(force=True, redirect_uri="http://localhost:1115/bitcasafilelister/auth")
    auth_name="View Files"
    auth_url="/bitcasafilelister/files/"
    error_msg = ""
    msg = "You access token is stored locally. To retrieve base64 paths click view files below"
    if authorization_code:
        try:
            client.authenticate(authorization_code)
        except BitcasaException:
            auth_name="Login"
            auth_url="/bitcasafilelister/auth"
            is_error=True
            error_msg = "Failed to authenticate access token %s" % authorization_code
            msg = "Your authentication token is either invalid or not set. Please set one by logging in. After authentication, you will also be able to view your files"
            log.exception(error_msg)
        else:
            is_error=False
            error_msg = "Storing permanent token %s" % client.access_token
            log.info(error_msg)
            try:
                with open(utils.BITCASA_TOKEN, "w") as tokenfile:
                    tokenfile.write(client.access_token)
            except Exception as e:
                auth_name="Login"
                auth_url="/bitcasafilelister/auth"
                is_error = True
                error_msg = "Failed to save permanent token"
                msg = "Your authentication token is either invalid or not set. Please set one by logging in. After authentication, you will also be able to view your files"
                log.exception(error_msg)
        return template("bitcasafilelister", is_error=is_error, error_msg=error_msg,
                        authorization_code=authorization_code, auth_url=auth_url,
                        auth_name=auth_name, msg=msg)
    else:
        redirect(client.login_url)

def start():
    """start server"""
    try:
        run(server="cherrypy", host='0.0.0.0', port=1115, reloader=False)
    except:
        raise

if __name__ == '__main__':
    start()