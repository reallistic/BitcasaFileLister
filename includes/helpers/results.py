import os, logging, time
log = logging.getLogger("BitcasaFileFetcher")

class Results(object):
    def __init__(self, logdir, should_exit):
        self.successfiles = os.path.join(logdir, "successfiles.csv")
        self.errorfiles = os.path.join(logdir, "errorfiles.csv")
        self.skippedfiles = os.path.join(logdir, "skippedfiles.csv")
        self.should_exit = should_exit
        self.create_log_files()
    
    def writeSuccess(self, filept):
        try:
            with open(self.successfiles, 'a') as myfile:
                myfile.write("%s\n" % filept)
        except:
            log.exception("Error. Could not write to %s. Ending", self.successfiles)
            self.should_exit.set()

    def writeSkipped(self, tfd, base64_path, nm):
        log.debug("%s already exists. Skipping", nm)
        try:
            with open(self.skippedfiles, 'a') as myfile:
                myfile.write("%s||%s\n" % (tfd, base64_path))
        except:
            log.exception("Error. Could not write to %s. Ending", self.skippedfiles)
            self.should_exit.set()

    def writeError(self, nm, tfd, base64_path, e):
        log.error("Error processing file %s\n%s", nm, e)
        try:
            with open(self.errorfiles, 'a') as myfile:
                myfile.write("File||%s||%s\n" % (tfd, base64_path))
        except:
            log.exception("Error. Could not write to %s. Ending", self.errorfiles)
            self.should_exit.set()

    def writeErrorDir(self, nm, tfd, base64_path, e):
        log.error("Error processing folder %s\n%s", nm, e)
        try:
            with open(self.errorfiles, 'a') as myfile:
                 myfile.write("Folder||%s||%s\n" % (tfd, base64_path))
        except:
            log.exception("Error. Could not write to %s. Ending", self.errorfiles)
            self.should_exit.set()

    def create_log_files(self):
        try:
            log.debug("Creating file %s", self.successfiles)
            with open(self.successfiles, 'w+') as myfile:
                myfile.write("File path\n")
                myfile.write(time.strftime("%Y-%m-%d %H:%M:%S") + " Start\n")
            log.debug("Creating file %s", self.errorfiles)
            with open(self.errorfiles, 'w+') as myfile:
                myfile.write("Type||File path||Base64 Path\n")
                myfile.write(time.strftime("%Y-%m-%d %H:%M:%S") + " Start\n")
            log.debug("Creating file %s", self.skippedfiles)
            with open(self.skippedfiles, 'w+') as myfile:
                myfile.write("File path||Base64 Path\n")
                myfile.write(time.strftime("%Y-%m-%d %H:%M:%S") + " Start\n")
        except:
            log.exception("Error. Could not initialize logging files. Ending")
            self.should_exit.set()