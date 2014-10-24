import logging
from logging.handlers import RotatingFileHandler

def setup(logfile = None, debug = False):
    logger = logging.getLogger(__name__)
    if not logfile or logfile == "":
        logfile = 'bitcasafilelister.log'

    maxsize = 1 * 1024* 1024 #1mb
        
    LOGLEVEL = logging.INFO
    if debug:
    	LOGLEVEL = logging.DEBUG
    logger.setLevel(LOGLEVEL)

    #file logger
    lh = RotatingFileHandler(logfile, maxBytes=maxsize, backupCount=5)
    lh.setLevel(LOGLEVEL)
    fmt = logging.Formatter('%(asctime)s [%(name)s][%(levelname)s]: %(message)s', '%m/%d/%Y %I:%M:%S')
    lh.setFormatter(fmt)
    logger.addHandler(lh)

    #Console logger
    ch = logging.StreamHandler()
    ch.setLevel(LOGLEVEL)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    logger.info("Logging loaded")
    if debug:
    	logger.debug("Debug is set")
    return logger