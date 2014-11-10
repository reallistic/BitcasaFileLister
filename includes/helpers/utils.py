CLIENTID = "758ab3de"
CLIENTSECRET = "5669c999ac340185a7c80c28d12a4319"
REDIRECT_URI = "http://localhost:1115/bitcasafilelister/auth/"

import math, os, hashlib, logging, tempfile, chardet
BITCASA_TOKEN = os.path.abspath("bitcasa.ini")
GDRIVE_CREDS = os.path.abspath("gdrive.ini")
GDRIVE_SECRETS = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../lib", "gdrive_secrets.ini"))

log = logging.getLogger("BitcasaFileFetcher")

def get_remaining_time(size_down, size_left, time):
    if size_down <= 0 or size_left <= 0 or time <= 0:
        return "unknown time"

    remaining = (time*size_left)/size_down

    return convert_time(remaining)

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
    elif secs <= 1:
        return "1 sec"
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

def get_decoded_name(nm):
    nm = "".join(i for i in nm if i not in "\/:*?<>|%\"")
    nm = nm.strip()
    nm = nm.decode(chardet.detect(nm)["encoding"]).encode('utf-8')
    return nm
