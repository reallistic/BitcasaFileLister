import math, sys, argparse, os
from bitcasa import BitcasaClient

CLIENTID = "758ab3de"
CLIENTSECRET = "5669c999ac340185a7c80c28d12a4319"

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

def get_speed(size, time):
    if size <= 0 or time <= 0:
        return "0B/s"
    speed = round(size/time, 2)
    speed = convert_size(speed)
    return str(speed+"/s")

def get_args():
    if "--oauth" in sys.argv:
        bitc = BitcasaClient(CLIENTID, CLIENTSECRET, "https://rose-llc.com/bitcasafilelist/")
        print bitc.login_url
        sys.exit(1)
    parser = argparse.ArgumentParser()
    parser.add_argument("src", help="The Bitcasa base64 path for file source")
    parser.add_argument("dst", help="The final destination root dir or your files")
    parser.add_argument("token", help="The access token from Bitcasa. To get one navigate to https://rose-llc.com/bitcasafilelist")
    parser.add_argument("-t", "--temp", help="The temp dir to store downloaded files. (Should be a local folder)")
    parser.add_argument("-l", "--log", help="Full path to log file")
    parser.add_argument("--depth", type=int, help="Specify depth of folder traverse. 0 is same as --norecursion")
    parser.add_argument("-m", "--threads", type=int, help="Specify the max number of threads to use for downloading. Default is 5")
    parser.add_argument("--local", help="Only store file locally. Do not use temp dir", action="store_true")
    parser.add_argument("--norecursion", help="Do not go below the src folder. (Same as --depth=0)", action="store_true")
    parser.add_argument("--noconsole", help="do not log to console", action="store_true")
    parser.add_argument("--oauth", help="do not log to console", action="store_true")
    parser.add_argument("--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument('--version', help="Displays version and exits", action='version', version='%(prog)s 0.5.0')
    args = parser.parse_args()

    if (args.log == None or args.log == "") and not args.local:
        args.log = os.path.join(args.temp, "runlog.txt")
    elif (args.log == None or args.log == "") and args.local:
        args.log = os.path.join(args.dst, "runlog.txt")

    if (args.temp == "" and not args.local) or args.dst == "" or args.src == "" or args.token == "":
        sys.stderr.write("Please supply access token, temp, source, and destination locations. If this is a local copy, then specify -l or --local\n")
        sys.exit(2)
    elif args.temp != None and args.temp != "" and args.local:
        sys.stdout.write("Local specified. Ignoring temp\n")
        args.temp = args.dst
    elif args.local:
        args.temp = args.dst
    #initialize temp dir
    try:
        if not os.path.isdir(args.temp):
            os.makedirs(args.temp)
    except:
        sys.stderr.write("Error creating temp directory\n")
        raise
    args.rec = not args.norecursion
    args.console = not args.noconsole

    return args