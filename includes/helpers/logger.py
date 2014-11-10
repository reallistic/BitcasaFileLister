import logging, os
from logging.handlers import RotatingFileHandler

def create(name, args):
	logger = logging.getLogger(name)

	maxsize = 1 * 1024* 1024 #1mb
	    
	LOGLEVEL = logging.INFO
	if args.args.verbose:
		LOGLEVEL = logging.DEBUG
	logger.setLevel(LOGLEVEL)

	lFormat = logging.Formatter('%(asctime)s [%(threadName)s][%(levelname)s]: %(message)s', '%m/%d %H:%M:%S')
	logfile = ""
	if args.run_level == args.RUN_LEVEL_MAIN:
		#file logger
		logfile = args.args.logfile
		if not logfile:
		    logfile = '../bitcasafilefetcher.log'
		filehandler = RotatingFileHandler(logfile, maxBytes=maxsize, backupCount=5)
		filehandler.setLevel(LOGLEVEL)
		filehandler.setFormatter(lFormat)
		logger.addHandler(filehandler)
		if os.path.getsize(logfile) > maxsize/2:
			logger.handlers[0].doRollover()
			logger.debug("Log rollover")


	if args.run_level != args.RUN_LEVEL_MAIN or args.args.console:
	    #Console logger
	    consolehandler = logging.StreamHandler()
	    consolehandler.setLevel(LOGLEVEL)
	    consolehandler.setFormatter(lFormat)
	    logger.addHandler(consolehandler)

	logger.info("Logging loaded %s", logfile)
	logger.debug("Debug is set")
	return logger