from bitcasa import BitcasaClient, BitcasaFolder, BitcasaFile
from bitcasa.exception import BitcasaException
import time, os, sys, traceback
import utils
from logger import logger as log
from threads import RunThreaded

class BitcasaDownload:
    def folderRecurse(self, fold, path, tthdnum, depth):
        if self.end:
            return
        log.info(path)
        fulldest = os.path.join(self.dest, path)
        fulltmp = ""
        remainingtries = 3
         #Create temp dir and dest dir if needed
        try:
            if self.tmp:
                fulltmp = os.path.join(self.tmp, path)
                try:
                    os.makedirs(fulltmp)
                except OSError:
                    if not os.path.isdir(fulltmp):
                        self.writeErrorDir(tthdnum, fold.name, fulltmp, fold.path, traceback.format_exc())
                        raise

            if fulldest:
                try:
                    os.makedirs(fulldest)
                except OSError:
                    if not os.path.isdir(fulldest):
                        self.writeErrorDir(tthdnum, fold.name, fulldest, fold.path, traceback.format_exc())
                        raise
        except OSError:
            return
        except BitcasaException: #This could happen if the api is called when asking for folder properties
            self.writeErrorDir(tthdnum, path, fulldest, "", traceback.format_exc())
            return

        log.debug("Dest path %s", fulldest)
        if self.tmp:
            log.debug("Tmp path %s", fulltmp)

        while remainingtries > 0:
            try:
                tfd = ""
                nm = ""
                pt = ""
                for item in fold.items:
                    if self.end:
                        return
                    nm = item.name
                    pt = item.path
                    filesize = None
                    tfd = os.path.join(fulldest, nm)
                    fexists = False
                    if isinstance(item, BitcasaFile):
                        filesize = item.size
                        fexists = os.path.isfile(tfd) and os.path.getsize(tfd) >= filesize
                    if filesize is not None and not fexists:
                        if self.numthreads >= self.maxthreads:
                            while self.numthreads >= self.maxthreads and not self.end:
                                time.sleep(5)
                            if not self.end:
                                self.numthreads += 1
                                thread = RunThreaded(item, self.numthreads, fulldest, self, fulltmp)
                                thread.start()
                                self.threads.append(thread)
                            else:
                                log.debug("Got exit signal. Not creating any more threads")
                        elif not self.end:
                            self.numthreads += 1
                            thread = RunThreaded(item, self.numthreads, fulldest, self, fulltmp)
                            thread.start()
                            self.threads.append(thread)
                        else:
                            log.debug("Got exit signal. Stopping loop")
                            break
                    elif not self.end and isinstance(item, BitcasaFolder):
                        if (self.depth == None or self.depth > depth) and self.rec:
                            self.folderRecurse(item, os.path.join(path, nm), tthdnum, (depth+1))
                    elif not self.end and fexists:
                        self.writeSkipped(tthdnum, tfd, pt, nm)
                    elif self.end:
                        log.debug("Got exit signal. Discontinue recurse")
                        return

            except (BitcasaException, ValueError) as e:
                remainingtries -= 1
                log.warn("Possible rate limit issue. Will retry %s more times", remainingtries)
                log.warn(e)
                if remainingtries > 0:
                    time.sleep(10)
                else:
                    log.error("Error downloading at folder %s", path)
            except KeyboardInterrupt:
                self.end = True
                log.info("Program received exit signal")
            except: #Hopefully this won't get called
                self.writeError(tthdnum, nm, tfd, pt, traceback.format_exc())
            else:
                #Randomly log progress and speed statistics
                size = utils.convert_size(self.bytestotal)
                speed = utils.get_speed(self.bytestotal, time.time() - self.st)
                if self.progress and self.bytestotal > 0:
                    log.info("Downloaded %s at %s", size, speed)
                remainingtries = 0

    def __init__(self, args):
        log.debug("src: %s", args.src)
        log.debug("dst: %s", args.dst)
        log.debug("at: %s", args.token)
        log.debug("tmp: %s", args.temp)
        log.debug("logdir: %s", args.logdir)
        log.debug("rec: %s", args.rec)
        log.debug("depth: %s", args.depth)
        log.debug("mt: %s", args.threads)
        log.debug("p: %s", args.progress)
        #destination directory
        self.dest = args.dst
        #temp directory
        self.tmp = args.temp
        self.successfiles = os.path.join(args.logdir, "successfiles.txt")
        self.errorfiles = os.path.join(args.logdir, "errorfiles.txt")
        self.skippedfiles = os.path.join(args.logdir, "skippedfiles.txt")
        #bittcasa base64 encdoded path
        self.basefolder = args.src
        #Access token
        self.accesstoken = args.token
        self.maxthreads = args.threads
        if self.maxthreads == None or self.maxthreads == 0:
            log.info("Using default max threads value of 5")
            self.maxthreads = 5
        #Recursion
        self.rec = args.rec
        #Recursion max depth
        self.depth = args.depth
        #Test only
        self.test = args.test
        #Log dir
        self.logdir = args.logdir
        #log progress
        self.progress = args.progress

        #Initialize
        self.numthreads = 0
        self.end = False
        self.threads = []
        self.st = time.time()
        self.bytestotal = 0

    def process(self):
        bitc = BitcasaClient(utils.CLIENTID, utils.CLIENTSECRET, "https://rose-llc.com/bitcasafilelist/", self.accesstoken)
        log.debug("Getting base folder")
        base = None
        remainingtries = 3
        if self.test:
            remainingtries = 1
        while base is None and remainingtries > 0:
            try:
                base = bitc.get_folder(self.basefolder)
            except (BitcasaException, ValueError) as e:
                log.info("Couldn't get base folder. Will retry %s more times", remainingtries)
                log.debug(e)
                remainingtries -= 1
                if remainingtries > 0:
                    try:
                        time.sleep(10)
                    except KeyboardInterrupt:
                        log.info("Got exit signal. Goodbye")
                        return
                else:
                    log.error("Error could not retreive base folder")
                    return
        log.debug("Got base folder")
        if self.test:
            log.info("Nothing downloaded because this is a test")
            return
        myfile = file(self.successfiles, 'w+')
        myfile.write(time.strftime("%Y-%m-%d %H:%M:%S") + " Start\n")
        myfile.close()
        myfile = file(self.errorfiles, 'w+')
        myfile.write(time.strftime("%Y-%m-%d %H:%M:%S") + " Start\n")
        myfile.close()
        myfile = file(self.skippedfiles, 'w+')
        myfile.write(time.strftime("%Y-%m-%d %H:%M:%S") + " Start\n")
        myfile.close()

        log.debug("Starting recursion")
        self.folderRecurse(base, "", 0, 0)
        try:
            #wait for threads to finish downoading
            while len(self.threads) > 0:
                thread = self.threads.pop()
                if thread.isAlive():
                    thread.join(5)

        except KeyboardInterrupt:
            self.end = True
            log.info("Program received exit signal")
        #Log final speed and statistics
        if self.progress and self.bytestotal > 0:
            speed = utils.get_speed(self.bytestotal, time.time() - self.st)
            log.info("Downloaded %s at %s", utils.convert_size(self.bytestotal), speed)

    def writeSuccess(self, thread, filept):
        try:
            with open(self.successfiles, 'a') as myfile:
                myfile.write("%s\n" % filept)
        except OSError as e:
            log.error("Error. Could not write to %s. Ending\n%s", self.successfiles, e)
            self.end = True

    def writeSkipped(self, tthdnum, tfd, pt, nm):
        log.info("%s already exists. Skipping", nm)
        try:
            with open(self.skippedfiles, 'a') as myfile:
                myfile.write("%s %s\n" % (tfd, pt))
        except OSError as e:
            log.error("Error. Could not write to %s. Ending\n%s", self.skippedfiles, e)
            self.end = True

    def writeError(self, tthdnum, nm, tfd, pt, e):
        log.error("Error processing file %s\n%s", nm, e)
        try:
            with open(self.errorfiles, 'a') as myfile:
                myfile.write("%s %s\n" % (tfd, pt))
        except OSError as e:
            log.error("Error. Could not write to %s. Ending\n%s", self.errorfiles, e)
            self.end = True

    def writeErrorDir(self, tthdnum, nm, tfd, pt, e):
        log.error("Error processing folder %s\n%s", nm, e)
        try:
            with open(self.errorfiles, 'a') as myfile:
                myfile.write("%s %s\n" % (tfd, pt))
        except OSError as e:
            log.error("Error. Could not write to %s. Ending\n%s", self.errorfiles, e)
            self.end = True
def main():
    args = utils.get_args()
    log.debug("Initializing Bitcasa")
    bitc = BitcasaDownload(args)
    bitc.process()
    log.info("Done")


if __name__ == "__main__":
    main()
