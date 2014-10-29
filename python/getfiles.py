from bitcasa import BitcasaClient, BitcasaFolder, BitcasaFile
from bitcasa.exception import BitcasaException
import time, os, sys, traceback
import utils
from logger import logger as log
from threads import RunThreaded

class BitcasaDownload:
    def folderRecurse(self, fold, path, tthdnum, depth):
        log.info("Thread [%s]: %s" % (tthdnum, path))
        fulldest = os.path.join(self.dest, path)
        fulltmp = os.path.join(self.tmp, path)
        log.debug("Dest path %s" % fulldest)
        log.debug("Tmp path %s" % fulltmp)
        remainingtries = 3
         #Create temp dir and dest dir if needed
        try:
            if fulltmp:
                try:
                    os.makedirs(fulltmp)
                except OSError:
                    if not os.path.isdir(fulltmp):
                        self.writeErrorDir(tthdnum, fold.name, fulltmp, fold.path, traceback.format_exc())
                        raise

            if not self.local and fulldest:
                try:
                    os.makedirs(fulldest)
                except OSError:
                    if not os.path.isdir(fulldest):
                        self.writeErrorDir(tthdnum, fold.name, fulldest, fold.path, traceback.format_exc())
                        raise
        except OSError:
            return
        except BitcasaException: #This could happen if the api is called when asking for folder properties
            self.writeErrorDir(tthdnum, path, fulltmp, "", traceback.format_exc())
            return

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
                                log.debug("Thread [%s]: Got exit signal while sleeping" % tthdnum)
                        elif not self.end:
                            self.numthreads += 1
                            thread = RunThreaded(item, self.numthreads, fulldest, self, fulltmp)
                            thread.start()
                            self.threads.append(thread)
                        else:
                            log.debug("Thread [%s]: Got exit signal. Stopping loop" % tthdnum)
                            break
                    elif isinstance(item, BitcasaFolder):
                        if (self.depth == None or self.depth > depth) and self.rec:
                            self.folderRecurse(item, os.path.join(path, nm), tthdnum, (depth+1))
                    elif fexists:
                        self.writeSkipped(tthdnum, tfd, pt, nm)

            except BitcasaException:
                remainingtries -= 1
                if remainingtries > 0:
                    time.sleep(10)
                else:
                    log.error("Thread [%s]: error downloading at folder %s" % (tthdnum, path))
            except KeyboardInterrupt:
                self.end = True
                log.info("Thread [%s]: Program received exit signal", tthdnum)
            except: #Hopefully this won't get called
                self.writeError(tthdnum, nm, tfd, pt, traceback.format_exc())
            else:
                #Randomly log progress and speed statistics
                size = utils.convert_size(self.bytestotal)
                speed = utils.get_speed(self.bytestotal, time.time() - self.st)
                log.info("finished %s %s at %s\n" % (path, size, speed))
                remainingtries = 0

    def __init__(self, args):
        log.debug("depth: %s" % args.depth)
        log.debug("tmp: %s" % args.temp)
        log.debug("src: %s" % args.src)
        log.debug("dst: %s" % args.dst)
        log.debug("rec: %s" % args.rec)
        log.debug("local: %s" % args.local)
        log.debug("at: %s" % args.token)
        log.debug("mt: %s" % args.threads)
        #destination directory
        self.dest = args.dst
        #temp directory
        self.tmp = args.temp
        self.successfiles = os.path.join(args.temp, "successfiles.txt")
        self.errorfiles = os.path.join(args.temp, "errorfiles.txt")
        self.skippedfiles = os.path.join(args.temp, "skippedfiles.txt")
        #bittcasa base64 encdoded path
        self.basefolder = args.src
        #Access token
        self.accesstoken = args.token
        self.maxthreads = args.threads
        if self.maxthreads == None or self.maxthreads == 0:
            log.info("Using default max threads value of 5")
            self.maxthreads = 5
        self.local = args.local
        self.rec = args.rec
        self.depth = args.depth
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
        while base is None and remainingtries > 0:
            try:
                base = bitc.get_folder(self.basefolder)
            except BitcasaException as e:
                log.debug("Couldn't get base folder. Assuming rate limit exceeded. Sleeping")
                log.debug(e)
                remainingtries -= 1
                if remainingtries > 0:
                    time.sleep(10)
                else:
                    log.error("Error could not retreive base folder")
                    return
        log.debug("Got base folder")
        log.debug(base.name)

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

        #wait for threads to finish downoading
        for thread in self.threads:
            thread.join()
        #Log final speed and statistics
        log.info("finished %s at %s\n" % (utils.convert_size(self.bytestotal), utils.get_speed(self.bytestotal, time.time() - self.st)))

    def writeSuccess(self, thread, file):
        try:
            with open(self.successfiles, 'a') as myfile:
                myfile.write("%s\n" % file)
        except:
            log.error("Thread [%s]: Error. Could not write to successfiles.txt. Ending" % (thread))
            self.end = True

    def writeSkipped(self, tthdnum, tfd, pt, nm):
        log.info("Thread [%s]: %s already exists. Skipping" % (tthdnum, nm))
        try:
            with open(self.skippedfiles, 'a') as myfile:
                myfile.write("%s %s\n" % (tfd, pt))
        except:
            log.error("Thread [%s]: Error. Could not write to skippedfiles.txt. Ending" % (tthdnum))
            self.end = True

    def writeError(self, tthdnum, nm, tfd, pt, e):
        log.error("Thread [%s]: Error processing file %s\n%s" % (tthdnum, nm, e))
        try:
            with open(self.errorfiles, 'a') as myfile:
                myfile.write("%s %s\n" % (tfd, pt))
        except:
            log.error("Thread [%s]: Error. Could not write to errorfiles.txt. Ending" % (tthdnum))
            self.end = True

    def writeErrorDir(self, tthdnum, nm, tfd, pt, e):
        log.error("Thread [%s]: Error processing folder %s\n%s" % (tthdnum, nm, e))
        try:
            with open(self.errorfiles, 'a') as myfile:
                myfile.write("%s %s\n" % (tfd, pt))
        except:
            log.error("Thread [%s]: Error. Could not write to errorfiles.txt. Ending" % (tthdnum))
            self.end = True
def main():
    args = utils.get_args()

    if args.depth > 0 and args.norecursion:
        log.info("Note: Non 0 depth and --no-recursion parameter present. Assuming recusion")
        args.rec = True
    log.debug("Initializing Bitcasa")
    bitc = BitcasaDownload(args)
    bitc.process()
    log.info("done")


if __name__ == "__main__":
    main()
