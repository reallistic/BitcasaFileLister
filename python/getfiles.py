from bitcasa import BitcasaClient, BitcasaFolder, BitcasaFile
from bitcasa.exception import BitcasaException
import time, os, sys, traceback, threading
import utils
from logger import logger as log
from threads import RunThreaded
from unidecode import unidecode
from collections import deque

class FileDownload(object):
    def __init__(self, filename, filepath, filesize, fullpath, filedir):
        self.filename = filename
        self.filepath = filepath
        self.filesize = filesize
        self.fullpath = fullpath
        self.filedir = filedir
        self.thread = None

    def start(self, thread_num, parent):
        item = {
            "filename": self.filename,
            "filepath": self.filepath,
            "filesize": self.filesize,
            "fullpath": self.fullpath,
            "filedir": self.filedir
        }
        log.debug("Starting file download %s", self.filename)
        thread = RunThreaded(item, thread_num, parent)
        thread.start()
        self.thread = thread

    def pause(self):
        thread.pause()

    def resume(self):
        thread.resume()

class DownloadThreaded(threading.Thread):
    def __init__(self, parent):
        threading.Thread.__init__(self, name="Downloader")
        self.parent = parent

    def run(self):
        log.debug("Starting Downloader")
        while not self.parent.done and not self.parent.end:
            if len(self.parent.todownload) > 0:
                next_thread = self.parent.getNextThread()
                while next_thread is None and not self.parent.end:
                    log.debug("Downloader waiting for thread space. %s left to process", len(self.parent.todownload))
                    time.sleep(5)
                    next_thread = self.parent.getNextThread()
                if not self.parent.end:
                    download = self.parent.todownload.popleft()
                    log.debug("Downloader processing %s", download.filename)
                    download.start(next_thread, self.parent)
                    self.parent.threads[next_thread] = download
                else:
                    log.debug("Got exit signal. Not creating any more threads")
                    break
            else:
                time.sleep(10)

        if self.parent.end:
            log.info("Stopping Downloader")
        else:
            log.info("Downloader shutting down")

class QueueThreaded(threading.Thread):
    def __init__(self, qid, parent):
        threading.Thread.__init__(self, name="Queuer "+qid)
        self.parent = parent
        self.qid = qid

    def run(self):
        log.debug("Starting Queuer")
        while not self.parent.done and not self.parent.end and self.parent.moreToQueue():
            if len(self.parent.folders_queue) and self.parent.folders_lock is None:
                self.parent.queuers[int(self.qid)-1]["processing"] = True
                self.parent.folder_lock = self.qid
                folder = self.parent.folders_queue.popleft()
                log.debug("Grabbing folder %s", folder["folder"].name)
                self.parent.folder_lock = None
                try:
                    self.parent.folder_list(folder["folder"], folder["path"], folder["depth"])
                except KeyboardInterrupt:
                    log.warn("Received end signal")
                    self.parent.end = True
                    break
                else:
                    time.sleep(1)

                self.parent.queuers[int(self.qid)-1]["processing"] = False
                time.sleep(5)
            else:
                if len(self.parent.folders_queue) > 1:
                    time.sleep(1)
                else:
                    time.sleep(int(self.qid))

        if self.parent.end:
            self.parent.queuers[int(self.qid)-1]["processing"] = False
            log.info("Stopping Queuer")
        elif self.parent.done:
            log.info("Queuer shutting down")
        else:
            log.info("Queuer shutting down. All folders processed")


class BitcasaDownload(object):
    def getNextThread(self):
        for thread_num in xrange(len(self.threads)):
            if self.threads[thread_num] is None:
                return thread_num
        return None
    def getActiveThreads(self):
        activeThreads = []
        for thread in self.threads:
            if thread and thread.thread:
                activeThreads.append(thread.thread)
        for queue_thread in self.queuers:
            if queue_thread["processing"]:
                activeThreads.append(queue_thread["thread"])
        return activeThreads

    def moreToQueue(self):
        if len(self.folders_queue) > 0:
            return True
        for queue_thread in self.queuers:
            if queue_thread["processing"]:
                return True

        return False

    def folder_list(self, fold, path, depth):
        if self.end:
            log.debug("Received end signal. Stopping folder list")
            return
        if path:
            log.info(path)
        fulldest = os.path.join(self.dest, path)
        remainingtries = 3
         #Create temp dir and dest dir if needed
        while remainingtries > 0:
            try:
                if fulldest:
                    try:
                        os.makedirs(fulldest)
                    except (OSError, IOError):
                        if not os.path.isdir(fulldest):
                            raise
            except:
                remainingtries -=  1
                log.exception("Couldn't create folder %s",fulldest)
                if remainingtries > 0:
                    log.error("Will retry to create folder %s more times", remainingtries)
                    time.sleep(2)
                else:
                    self.writeErrorDir(fold.name, fulldest, fold.path, traceback.format_exc())
                    return
            else:
                remainingtries = 0

        log.debug(fulldest)
        remainingtries = 3
        apiratecount = 0
        while remainingtries > 0 and not self.end:
            if self.end:
                 log.info("Program received exit signal")
                 return
            try:
                folderitems = fold.items
            except BitcasaException as e:
                if self.end:
                 log.info("Program received exit signal")
                 return
                remainingtries -= 1
                if e.code in [9006, 503, 429]:
                    apiratecount += 1
                    remainingtries += 1
                    log.warn("API rate limit reached. Will retry")
                else:
                    log.warn("Failed to get folder contents %s. Will retry %s more times", e.code, remainingtries)

                if remainingtries > 0:
                    try:
                        time.sleep(10 * apiratecount)
                    except KeyboardInterrupt:
                        self.end = True
                        log.info("Program received exit signal")
                        return
                else:
                    log.error("Error downloading at folder %s", path)
                    return
            except KeyboardInterrupt:
                self.end = True
                log.info("Program received exit signal")
                return
            else:
                remainingtries = 0

        for item in folderitems:
            if self.end:
                 log.info("Program received exit signal")
                 return
            remainingtries = 3
            while remainingtries > 0:
                try:
                    if self.end:
                        return
                    nm = item.name
                    try:
                        nm = unidecode(nm)
                        nm = nm.encode('utf-8')
                        nm = "".join(i for i in nm if i not in "\/:*?<>|%\"")
                        nm = nm.strip()
                    except:
                        log.warn("Error encoding to utf-8. Will parse anyway")

                    pt = item.path
                    filesize = None
                    tfd = os.path.join(fulldest, nm)
                    fexists = False
                    if isinstance(item, BitcasaFile):
                        filesize = item.size
                        try:
                            # it is possible that an error here could tell us
                            # downloading later won't be possible but there are 
                            # too many errno's to try and catch that right now
                            fexists = os.path.getsize(tfd) >= filesize
                        except OSError:
                            pass

                    if filesize is not None and not fexists:
                        filedownload = FileDownload(nm, pt, filesize, tfd, fulldest)
                        log.debug("Queuing file download for %s", nm)
                        self.todownload.append(filedownload)
                    elif isinstance(item, BitcasaFolder):
                        if (self.depth == None or self.depth > depth) and self.rec:
                            folder = {
                                "folder": item,
                                "path": os.path.join(path, nm),
                                "depth": (depth+1)
                            }
                            log.debug("Queuing folder listing for %s", nm)
                            self.folders_queue.append(folder)
                    elif fexists:
                        self.writeSkipped(tfd, pt, nm)
                    elif self.end:
                        log.debug("Got exit signal. Discontinue recurse")
                        return
                except KeyboardInterrupt:
                    self.end = True
                    log.info("Program received exit signal")
                except: #Hopefully this won't get called
                    self.writeError(nm, tfd, pt, traceback.format_exc())
                else:
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
        if args.threads is None:
            log.info("Using default max threads value of 5")
            args.threads = 5
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
        self.threads = [None] * args.threads
        self.end = False
        self.st = time.time()
        self.bytestotal = 0
        self.todownload = deque()
        self.folders_queue = deque()
        self.folders_lock = None
        self.downloader = None
        self.queuers = []
        self.done = False
        self.downloadtime = 0
        self.copytime = 0

    def process(self):
        bitc = BitcasaClient(utils.CLIENTID, utils.CLIENTSECRET, "https://rose-llc.com/bitcasafilelist/", self.accesstoken)
        log.debug("Getting base folder")
        base = None
        remainingtries = 3
        if self.test:
            remainingtries = 1
        apiratecount = 0
        while base is None and remainingtries > 0:
            try:
                base = bitc.get_folder(self.basefolder)
            except BitcasaException as e:
                remainingtries -= 1
                if e.code == 9006:
                    apiratecount += 1
                    remainingtries += 1
                    log.warn("API rate limit reached. Will retry")
                else:
                    log.warn("Couldn't get base folder %s. Will retry %s more times", e.code, remainingtries)

                if remainingtries > 0:
                    try:
                        time.sleep(10 * apiratecount)
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
        try:
            with open(self.successfiles, 'w+') as myfile:
                myfile.write("File path\n")
                myfile.write(time.strftime("%Y-%m-%d %H:%M:%S") + " Start\n")

            with open(self.errorfiles, 'w+') as myfile:
                myfile.write("Type||File path||Base64 Path\n")
                myfile.write(time.strftime("%Y-%m-%d %H:%M:%S") + " Start\n")

            with open(self.skippedfiles, 'w+') as myfile:
                myfile.write("File path||Base64 Path\n")
                myfile.write(time.strftime("%Y-%m-%d %H:%M:%S") + " Start\n")
        except:
            log.exception("Error. Could not initialize logging files. Ending")
            return
        log.debug("Queuing base folder")
        folder = {
            "folder": base,
            "path": "",
            "depth": 0
        }
        self.folders_queue.append(folder)
        log.debug("Starting Queuers and Downloader")
        self.downloader = DownloadThreaded(self)
        self.downloader.start()
        for qid in xrange(len(self.threads)):
            qid+=1
            queue_thread = QueueThreaded(str(qid), self)
            self.queuers.append({"thread":queue_thread, "processing":False, "qid":qid})
            queue_thread.start()
        # Give the queuers time to catch up
        try:
            time.sleep(10)

            #wait for threads to finish downoading
            active = self.getActiveThreads()
            while len(active) > 0 or len(self.folders_queue) > 0 or len(self.todownload) >0:
                for thread in active:
                    if thread and thread.isAlive():
                        thread.join(5)
                if len(active) == 0:
                    time.sleep(5)
                active = self.getActiveThreads()

            self.done = True
            for queue_thread in self.queuers:
                if queue_thread["thread"].isAlive():
                    queue_thread["thread"].join(5)

        except KeyboardInterrupt:
            error = True
            while error:
                try:
                    self.end = True
                    log.info("Program received exit signal")
                    active = self.getActiveThreads()
                    for thread in active:
                        if thread and thread.isAlive():
                            log.info("Waiting for download thread %s to shutdown", thread.name)
                            thread.join(1)
                    for queue_thread in self.queuers:
                        if queue_thread["thread"].isAlive():
                            log.info("Wating for queuer to shutdown %s", queue_thread["qid"])
                            queue_thread["thread"].join(1)
                    if self.downloader.isAlive():
                        log.info("Waiting for Downloader to shutdown")
                        self.downloader.join(1)
                except KeyboardInterrupt:
                    pass
                else:
                    error = False
        #Log final speed and statistics
        speed = utils.get_speed(self.bytestotal, self.downloadtime)
        copyspeed = utils.get_speed(self.bytestotal, self.copytime)
        runspeed = utils.get_speed(self.bytestotal, (time.time() - self.st))
        log.info("Total download time: %s", utils.convert_time(self.downloadtime))
        log.info("Total run time: %s", utils.convert_time(time.time() - self.st))
        if self.tmp:
            log.info("Total copy time: %s", utils.convert_time(self.copytime))
        log.info("Download speed: %s at %s", utils.convert_size(self.bytestotal), speed)
        log.info("Run speed: %s at %s", utils.convert_size(self.bytestotal), runspeed)
        if self.tmp:
            log.info("Copy speed: %s at %s", utils.convert_size(self.bytestotal), copyspeed)

    def writeSuccess(self, filept):
        try:
            with open(self.successfiles, 'a') as myfile:
                myfile.write("%s\n" % filept)
        except:
            log.exception("Error. Could not write to %s. Ending", self.successfiles)
            self.end = True

    def writeSkipped(self, tfd, pt, nm):
        log.debug("%s already exists. Skipping", nm)
        try:
            with open(self.skippedfiles, 'a') as myfile:
                myfile.write("%s||%s\n" % (tfd, pt))
        except:
            log.exception("Error. Could not write to %s. Ending", self.skippedfiles)
            self.end = True

    def writeError(self, nm, tfd, pt, e):
        log.error("Error processing file %s\n%s", nm, e)
        try:
            with open(self.errorfiles, 'a') as myfile:
                myfile.write("File||%s||%s\n" % (tfd, pt))
        except:
            log.exception("Error. Could not write to %s. Ending", self.errorfiles)
            self.end = True

    def writeErrorDir(self, nm, tfd, pt, e):
        log.error("Error processing folder %s\n%s", nm, e)
        try:
            with open(self.errorfiles, 'a') as myfile:
                 myfile.write("Folder||%s||%s\n" % (tfd, pt))
        except:
            log.exception("Error. Could not write to %s. Ending", self.errorfiles)
            self.end = True
def main():
    args = utils.get_args()
    log.debug("Initializing Bitcasa")
    bitc = BitcasaDownload(args)
    bitc.process()
    log.info("Done")


if __name__ == "__main__":
    main()
