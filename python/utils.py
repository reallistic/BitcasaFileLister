CLIENTID = "758ab3de"
CLIENTSECRET = "5669c999ac340185a7c80c28d12a4319"

import math, sys, argparse, os, webbrowser, hashlib
from bitcasa import BitcasaClient
from bitcasa.exception import BitcasaException
from unidecode import unidecode
import tempfile

def convert_size(size):
    if size <= 0:
        return '0B'
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size, 1024)))
    power = math.pow(1024, i)
    size = round(size/power, 2)
    if size > 0:
        return '%s %s' % (size, size_name[i])
    else:
        return '0B'

def convert_time(secs):
    if secs <= 0:
        return '%s secs' % secs
    size_name = ("secs", "minutes", "hours", "days")
    i = int(math.floor(math.log(secs, 60)))
    one_day = 60*60*24
    if i > 2 or secs >= one_day:
        power = math.pow(60, 2)
        elapsed = round((secs/power)/24, 2)
        i = 3
    else:
        power = math.pow(60, i)
        elapsed = round(secs/power, 2)
    if elapsed > 0:
        return '%s %s' % (elapsed, size_name[i])
    else:
        return '%s secs' % secs

def get_speed(size, time):
    if size <= 0 or time <= 0:
        return "0B/s"
    speed = round(size/time, 2)
    speed = convert_size(speed)
    return str(speed+"/s")

def md5sum(filename, blocksize=65536):
    hasher = hashlib.md5()
    with open(filename, "r+b") as f:
        for block in iter(lambda: f.read(blocksize), ""):
            hasher.update(block)
    return hasher.hexdigest()

def get_log_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("src", help="The Bitcasa base64 path for file source", default="", nargs="?")
    parser.add_argument("dst", help="The final destination root dir or your files.\
        Note: if using with --gdrive this needs to be the root folder id", default="./", nargs="?")
    parser.add_argument("-l", "--log", help="Full path to log file")
    parser.add_argument("--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("--noconsole", dest="console", help="do not log to console", action="store_false")
    parser.add_argument("--testauth", dest="test", help="test capability to connect to infinite drive", action="store_true")
    parser.add_argument("-t", "--temp", dest="temp", help="The temp dir to store downloaded files.\
        Note: this option is mandatory when --gdrive is present")
    parser.add_argument("--gdrive", help="Upload files directly to google drive", action="store_true")
    args, unknown = parser.parse_known_args()
    if not args.log and args.temp:
        args.log = os.path.join(args.temp, "runlog.txt")
        args.logdir = args.temp
    elif not args.log and not args.temp and not args.gdrive:
        args.log = os.path.join(args.dst, "runlog.txt")
        args.logdir = args.dst
    elif not args.log and not args.temp and args.gdrive:
        args.log = "runlog.txt"
        args.logdir = "."
    #initialize temp dir
    try:
        if not os.path.isdir(args.logdir):
            os.makedirs(args.logdir)
    except:
        sys.stderr.write("Error creating log directory\n")
        raise
    return args

def get_decoded_name(nm):
    needunidecode = False
    tempname = "".join(i for i in nm if i not in "\/:*?<>|%\"")
    tempname = tempname.strip()
    tempname = os.path.join(tempfile.gettempdir(), tempname)
    try:
        open(tempname, 'a').close()
    except:
        needunidecode = True
    finally:
        try:
            os.remove(tempname)
        except:
            pass
    try:
        if needunidecode:
            nm = unidecode(nm)
        nm = nm.encode('utf-8')
        nm = "".join(i for i in nm if i not in "\/:*?<>|%\"")
        nm = nm.strip()
    except:
        raise
    return nm

def get_args():
    bitc = BitcasaClient(CLIENTID, CLIENTSECRET, "https://rose-llc.com/bitcasafilelist/")
    if "--oauth" in sys.argv:
        sys.stdout.write("%s\n" % bitc.login_url)
        webbrowser.open(bitc.login_url)
        sys.exit(1)
    elif "--clientcreds" in sys.argv:
        print "CLIENTID %s" % CLIENTID
        print "CLIENTSECRET %s" % CLIENTSECRET
        sys.exit(1)
    elif "--settoken" in sys.argv:
        token = sys.argv[2]
        try:
            bitc.authenticate(token)
        except BitcasaException:
            sys.stderr.write("Failed to authenticate access token %s\n" % token)
            sys.stderr.write("Navigate to the below url to get a new one\n")
            sys.stderr.write("%s\n" % bitc.login_url)
        else:
            sys.stdout.write("Storing permanent token %s\n" % bitc.access_token)
            try:
                with open("token.ini", "w") as tokenfile:
                    tokenfile.write(bitc.access_token)
            except OSError:
                sys.stderr.write("Failed to save permanent token\n")
                raise
        finally:
            sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("--settoken", dest="token", help="Set the access token from Bitcasa. You only need to do this once.")
    parser.add_argument("src", help="The Bitcasa base64 path for file source")
    parser.add_argument("dst", help="The final destination root dir or your files.\
        Note: if using with --gdrive this needs to be the root folder id")
    parser.add_argument("-t", "--temp", help="The temp dir to store downloaded files.\
        Note: this option is mandatory when --gdrive is present")
    parser.add_argument("-l", "--log", help="Full path to log file")
    parser.add_argument("--depth", type=int, help="Specify depth of folder traverse. 0 is same as --norecursion")
    parser.add_argument("-m", "--threads", dest="threads", type=int, help="Specify the max number of threads to use for downloading. Default is 5")
    parser.add_argument("--silentqueuer", help="Silence queuer output", action="store_true")
    parser.add_argument("-s", "--single", dest="single", help="download a single file", action="store_true")
    parser.add_argument("--gdrive", help="Upload files directly to google drive", action="store_true")
    parser.add_argument("--norecursion", dest="rec", help="Do not go below the src folder. (Same as --depth=0)", action="store_false")
    parser.add_argument("--noconsole", dest="console", help="do not log to console", action="store_false")
    parser.add_argument("--oauth", help="Get the url to authenticate and retrieve an access token", action="store_true")
    parser.add_argument("--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("--testauth", dest="test", help="test capability to connect to infinite drive", action="store_true")
    parser.add_argument("-p", "--progress", dest="progress", help="Log download progress every 60 secs", action="store_true")
    parser.add_argument('--version', help="Displays version and exits", action='version', version='%(prog)s 0.5.4')
    args = parser.parse_args()

    if not os.path.isfile("token.ini"):
        sys.stderr.write("Please retrive an access token using the following command.\n")
        sys.stderr.write("python getfiles.py --oauth\n")
        sys.exit(2)
    else:
        try:
            with open("token.ini", "r") as tokenfile:
                args.token = tokenfile.read()
        except OSError:
            sys.stderr.write("Failed to retrieve permanent token\n")
            raise
    if args.gdrive and not args.temp:
        sys.stderr.write("In order to use google drive you must specify a temp dir\n")
        sys.exit(2)

    if not args.log and args.temp:
        args.log = os.path.join(args.temp, "runlog.txt")
        args.logdir = args.temp
    elif not args.log and not args.temp:
        args.log = os.path.join(args.dst, "runlog.txt")
        args.logdir = args.dst
    #initialize temp dir
    try:
        if not os.path.isdir(args.logdir):
            os.makedirs(args.logdir)
    except:
        sys.stderr.write("Error creating temp directory\n")
        raise

    if args.depth > 0 and not args.rec:
        sys.stdout.write("Note: Non 0 depth and --no-recursion parameter present. Assuming recusion")
        args.rec = True
    return args