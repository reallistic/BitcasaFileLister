import logging
from logging.handlers import RotatingFileHandler
import utils

logger = logging.getLogger(__name__)
args = utils.get_args()
logfile = args.log
if not logfile or logfile == "":
    logfile = 'bitcasafilelister.log'

maxsize = 1 * 1024* 1024 #1mb
    
LOGLEVEL = logging.INFO
if args.verbose:
	LOGLEVEL = logging.DEBUG
logger.setLevel(LOGLEVEL)

#file logger
filehandler = RotatingFileHandler(logfile, maxBytes=maxsize, backupCount=5)
filehandler.setLevel(LOGLEVEL)
lFormat = logging.Formatter('%(asctime)s [%(name)s][%(levelname)s]: %(message)s', '%m/%d/%Y %I:%M:%S')
filehandler.setFormatter(lFormat)
logger.addHandler(filehandler)

if args.console:
    #Console logger
    consolehandler = logging.StreamHandler()
    consolehandler.setLevel(LOGLEVEL)
    consolehandler.setFormatter(lFormat)
    logger.addHandler(consolehandler)

logger.info("Logging loaded")
if args.verbose:
	logger.debug("Debug is set")