import argparse, os, sys, threading, signal, time
insert_path = os.path.abspath("./includes/")
sys.path.append(insert_path)
insert_path = os.path.abspath("./includes/lib/")
sys.path.append(insert_path)
from helpers import logger
from bitcasa import BitcasaClient
from bitcasa import BitcasaException

should_exit = threading.Event()

class Args(object):
    """
    Argument parser wrapper class
    run_level: The argv parsed run_level
        {main, test, oauth, authorize}
    """
    RUN_LEVEL_MAIN = "main"
    RUN_LEVEL_TEST = "test"
    RUN_LEVEL_OAUTH = "oauth"
    LOGFILENAME = "bitcasafilefetcher.log"

    def __init__(self):
        self.run_level = None
        self.args = None

    def set_log_file(self):
        """given parsed arguments figure out the log dir"""
        if self.args.log:
            logfile = self.args.log
            logdir = os.path.dirname(self.args.log)
        elif self.args.temp:
            logfile = os.path.join(self.args.temp, Args.LOGFILENAME)
            logdir = self.args.temp
        elif self.args.dst:
            logfile = os.path.join(self.args.dst, Args.LOGFILENAME)
            logdir = self.args.dst
        else:
            # By setting this to none all sub commands will
            # not log to a file
            logfile = None
            logdir = None

        try:
            if logdir and not os.path.isdir(logdir):
                os.makedirs(logdir)
        except:
            sys.stderr.write("Error creating temp directory\n")
            raise

        self.args.logfile = os.path.abspath(logfile)
        self.args.logdir = logdir

    def parse(self):
        """Parse the command line arguments"""
        parser = argparse.ArgumentParser(
            prog="BitcasaFileFetcher",
            description="Download files from bitcasa recursively")
        subparsers = parser.add_subparsers()

        providerprt = argparse.ArgumentParser(
            prog="BitcasaFileLister", add_help=False)

        providerprt.add_argument(
            "--provider", help="The provider in question (Default is bitcasa)",
            choices=['bitcasa', 'gdrive'], default='bitcasa')

        oauthparser = subparsers.add_parser(
            "oauth", help="Program to retrieve the oauth url for a provider",
            parents=[providerprt])
        oauthparser.add_argument(
            "-v", "--verbose", help="increase output verbosity", action="count")
        oauthparser.set_defaults(func=self.run_oauth)

        testsparser = subparsers.add_parser(
            "testauth", help="Program to test provider authentication",
            parents=[providerprt])
        testsparser.add_argument(
            "basefolder", metavar="basefolder",
            help="The base folder to attempt to list")
        testsparser.add_argument(
            "-v", "--verbose", help="increase output verbosity", action="count")
        testsparser.set_defaults(func=self.run_test)

        mainparser = argparse.ArgumentParser(
            prog="main", add_help=False)
        mainparser.add_argument(
            "src", help="The Bitcasa base64 path for file source")
        mainparser.add_argument(
            "dst", help="The final destination root dir or your files")
        mainparser.add_argument(
            "-l", "--log", help="Full path to log file")
        mainparser.add_argument(
            "-m", "--threads", help="Number of simultaneous downloads. (5)",
            type=int, default=5)
        main_group = mainparser.add_mutually_exclusive_group()
        main_group.add_argument(
            "--norecursion", dest="rec", action="store_false",
            help="Do not go below the src folder. (Same as --depth 0)", default=True)
        main_group.add_argument(
            "--depth", type=int, help="The depth of folder traversal")
        mainparser.add_argument("--silentqueuer", help="Silence queuer output", action="store_true")
        mainparser.add_argument("-s", "--single", dest="single", help="download a single file", action="store_true")
        mainparser.add_argument(
            "--noconsole", dest="console", help="do not log to console",
            action="store_false", default=True)
        mainparser.add_argument(
            "-v", "--verbose", help="increase output verbosity", action="count")
        mainparser.add_argument(
            "-p", "--progress", dest="progress", action="store_true",
            help="Log file download progress every 60 secs")
        mainparser.add_argument(
            '--version', help="Displays version and exits",
            action='version', version='%(prog)s 0.6.1')

        downparser = subparsers.add_parser("download", parents=[mainparser],
            help="Program to download files from bitcasa to local/network storage")
        downparser.add_argument(
            "-t", "--temp", help="The dir for temp files. (A local folder)")
        downparser.set_defaults(func=self.run_download)

        upparser = subparsers.add_parser("upload", parents=[mainparser],
            help="Program to download files from bitcasa and upload to remote storage")
        upparser.add_argument(
            "-t", "--temp", help="The dir for temp files. (A local folder)", required=True)
        upparser.add_argument(
            "--provider", help="The remote storage provider in question (default is gdrive)",
            choices=['gdrive'], default='gdrive')
        upparser.set_defaults(func=self.run_upload)

        self.args = parser.parse_args()
        self.args.func()

        return self.args

    def run_download(self):
        """Run the main program checks"""
        self.run_level = Args.RUN_LEVEL_MAIN
        self.args.upload = False
        self.set_log_file()

    def run_upload(self):
        self.run_download()
        self.args.upload = True

    def run_test(self):
        """run authentication tests on a specific provider"""
        self.run_level = Args.RUN_LEVEL_TEST

    def run_oauth(self):
        """perform oauth flow"""
        self.run_level = Args.RUN_LEVEL_OAUTH
    

def main():
    global log, utils
    args = Args()
    args.parse()
    log = logger.create("BitcasaFileFetcher", args)
    from helpers import utils
    from getfiles import BitcasaDownload
    from lib import BitcasaUtils
    from lib.gdrive import GoogleDrive

    if args.run_level == Args.RUN_LEVEL_MAIN:
        bitcasa_utils = BitcasaUtils()
        if bitcasa_utils.test_auth():
            args.args.token = bitcasa_utils.token
        else:
            log.error("Bitcasa Access token not set or invalid. Use the following commands to get one.")
            log.info("python BitcasaFileLister")
            return
        if args.args.upload:
            if args.args.provider == "gdrive":
                g = GoogleDrive()
                if not g.test_auth():
                    log.error("Google Drive Access token not set or invalid. Use the following command to get one.")
                    log.info("python BitcasaFileFetcher oauth --provider gdrive")
                    return
        log.debug("Initializing Bitcasa")
        bitc = BitcasaDownload(args.args, bitcasa_utils.create_client(), should_exit)
        if should_exit.is_set():
            log.info("Exiting")
            return
        input_thread = threading.Thread(target=handle_input, name="Handle Exit")
        input_thread.daemon = True
        input_thread.start()
        if args.args.single:
            bitc.process_single()
        else:
            bitc.process()
    elif args.run_level == Args.RUN_LEVEL_OAUTH:
        if args.args.provider == "bitcasa":
            run_server()
        elif args.args.provider == "gdrive":
            g = GoogleDrive()
            try:
                g.get_service(True)
            except:
                log.exception("Error authenticating to Google drive")

    elif args.run_level == Args.RUN_LEVEL_TEST:
        if args.args.provider == "bitcasa":
            bitcasa_utils = BitcasaUtils()
            if bitcasa_utils.test_auth():
                log.info("Connected to Bitcasa successfully")
            else:
                log.info("Error connecting to Bitcasa")
        elif args.args.provider == "gdrive":
            g = GoogleDrive()
            if g.test_auth():
                log.info("Connected to Google Drive successfully")
            else:
                log.info("Error connecting to Google drive")
    else:
        log.error("An error occurred processing your command. Please check the syntax and try again")
            
     
    log.info("Done")

def run_server():
    from subprocess import call
    call(["python", "BitcasaFileLister"])

def handle_input():
    log.debug("Watching for exit")
    answer = ""
    try:
        while answer.lower() != "y":
            if answer == "":
                answer = "n"
                answer = raw_input()
            else:
                answer = raw_input("Would you like to shutdown? [y/n]\n")
            if answer == "y":
                log.info("Received exit signal")
                should_exit.set()
    except (KeyboardInterrupt, IOError, EOFError):
        log.info("Received exit signal")
        should_exit.set()

def handle_exit_signal(signum, frame):
    log.info("Received exit signal")
    should_exit.set()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, handle_exit_signal)
    main()