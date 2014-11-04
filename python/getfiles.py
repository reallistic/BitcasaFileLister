from bitcasa import BitcasaClient, BitcasaFolder, BitcasaFile
from bitcasa.exception import BitcasaException
import time, os, sys, traceback, threading
import utils
from logger import logger as log
from threads import RunThreaded
from collections import deque
from gdrive import GoogleDrive

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

class DownloadThreaded(threading.Thread):
    def __init__(self, parent):
        threading.Thread.__init__(self, name="Downloader")
        self.parent = parent

    def run(self):
        log.debug("Starting Downloader")
        while not self.parent.done and not self.parent.end:
            if len(self.parent.todownload) > 0:
                next_thread = self.parent.getNextThread()
                waited = 0
                size_str = "0B"
                while next_thread is None and not self.parent.end:
                    if self.parent.progress and waited % 3 == 0:
                        size_str = utils.convert_size(self.total_size)
                        log.info("%s files and %s left to process", self.total_files, size_str)
                    waited += 1
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

    @property
    def total_size(self):
        total = 0
        for dwn in self.parent.todownload:
            total += dwn.filesize
        return total

    @property
    def total_files(self):
        return len(self.parent.todownload)

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
                if not self.parent.silentqueuer:
                    log.debug("Grabbing folder %s", folder["folder"].name)
                self.parent.folder_lock = None
                try:
                    if self.parent.gdrive:
                        self.parent.folder_list_gdrive(folder["folder"], folder["path"], folder["folder_id"], folder["depth"])
                    else:
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
    def __init__(self, args):
        log.debug("src: %s", args.src)
        log.debug("dst: %s", args.dst)
        log.debug("at: %s", args.token)
        log.debug("tmp: %s", args.temp)
        log.debug("gdrive: %s", args.gdrive)
        log.debug("logdir: %s", args.logdir)
        log.debug("rec: %s", args.rec)
        log.debug("depth: %s", args.depth)
        log.debug("mt: %s", args.threads)
        log.debug("p: %s", args.progress)
        log.debug("silentqueuer: %s", args.silentqueuer)
        log.debug("single: %s", args.single)
        #destination directory
        self.dest = args.dst
        #temp directory
        self.tmp = args.temp
        self.successfiles = os.path.join(args.logdir, "successfiles.csv")
        self.errorfiles = os.path.join(args.logdir, "errorfiles.csv")
        self.skippedfiles = os.path.join(args.logdir, "skippedfiles.csv")
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
        #Upload to google drive
        self.gdrive = args.gdrive
        #Don't log queuer activity
        self.silentqueuer = args.silentqueuer
        #Download a single file
        self.single = args.single

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
        self.g = None

    def getNextThread(self):
        for thread_num in xrange(len(self.threads)):
            if self.threads[thread_num] is None:
                return thread_num
        return None
    def getActiveThreads(self):
        activeThreads = []
        for thread in self.threads:
            if thread and thread.thread and thread.thread.isAlive():
                activeThreads.append(thread.thread)
        for queue_thread in self.queuers:
            if queue_thread["thread"].isAlive() and queue_thread["processing"]:
                activeThreads.append(queue_thread["thread"])
        return activeThreads

    def moreToQueue(self):
        if len(self.folders_queue) > 0:
            return True
        for queue_thread in self.queuers:
            if queue_thread["processing"]:
                return True

        return False

    def get_folder_items(self, fold, path):
        remainingtries = 3
        apiratecount = 0
        folderitems = None
        while remainingtries > 0 and not self.end:
            if self.end:
                 log.info("Program received exit signal")
                 return False
            try:
                folderitems = fold.items
            except BitcasaException as e:
                if self.end:
                    log.info("Program received exit signal")
                    return False
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
                        return False
                else:
                    log.error("Error downloading at folder %s", path)
                    return False
            except KeyboardInterrupt:
                self.end = True
                log.info("Program received exit signal")
                return False
            else:
                remainingtries = 0
        if folderitems is None:
            log.error("Filed to get folder items")
            return False
        return folderitems

    def folder_list_gdrive(self, fold, path, folder_id, depth):
        if self.end:
            log.debug("Received end signal. Stopping folder list")
            return
        if not self.silentqueuer:
            log.info(path)

        folderitems = self.get_folder_items(fold, path)
        if not folderitems:
            return
        g = self.g
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
                        nm = utils.get_decoded_name(nm)
                    except:
                        log.warn("Error encoding to utf-8. Will parse anyway")

                    base64_path = item.path
                    filesize = None
                    needtoupload = False
                    tfd = os.path.join(path, nm)
                    if isinstance(item, BitcasaFile):
                        filesize = item.size
                        needtoupload = g.need_to_upload(nm, folder_id, filesize)

                    if filesize is not None and needtoupload:
                        filedownload = FileDownload(nm, base64_path, filesize, tfd, folder_id)
                        if not self.silentqueuer:
                            log.debug("Queuing file download for %s", nm)
                        self.todownload.append(filedownload)
                    elif isinstance(item, BitcasaFolder):
                        if (self.depth == None or self.depth > depth) and self.rec:
                            g_fold = g.get_folder_byname(nm, parent=folder_id, createnotfound=True)
                            remainingtries = 3
                            while g_fold is None and remainingtries > 0:
                                remainingtries -= 1
                                log.error("Will retry to get/create %s %s more times", nm, remainingtries)
                                time.sleep(10)
                                g_fold = g.get_folder_byname(nm, parent=folder_id, createnotfound=True)
                            if g_fold is None:
                                log.error("Failed to get/create folder")
                                return
                            folder = {
                                "folder": item,
                                "depth": (depth+1),
                                "path": tfd,
                                "folder_id": g_fold["id"]
                            }
                            if not self.silentqueuer:
                                log.debug("Queuing folder listing for %s", nm)
                            self.folders_queue.append(folder)
                    elif not needtoupload:
                        self.writeSkipped(tfd, base64_path, nm)
                    elif self.end:
                        log.debug("Got exit signal. Discontinue recurse")
                        return
                except KeyboardInterrupt:
                    self.end = True
                    log.info("Program received exit signal")
                except: #Hopefully this won't get called
                    self.writeError(nm, tfd, base64_path, traceback.format_exc())
                else:
                    remainingtries = 0



    def folder_list(self, fold, path, depth):
        if self.end:
            log.debug("Received end signal. Stopping folder list")
            return
        if path and not self.silentqueuer:
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
        if not self.silentqueuer:
            log.debug(fulldest)
        folderitems = self.get_folder_items(fold, path)
        if not folderitems:
            return
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
                        nm = utils.get_decoded_name(nm)
                    except:
                        log.warn("Error encoding to utf-8. Will parse anyway")

                    base64_path = item.path
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
                        filedownload = FileDownload(nm, base64_path, filesize, tfd, fulldest)
                        if not self.silentqueuer:
                            log.debug("Queuing file download for %s", nm)
                        self.todownload.append(filedownload)
                    elif isinstance(item, BitcasaFolder):
                        if (self.depth == None or self.depth > depth) and self.rec:
                            folder = {
                                "folder": item,
                                "path": os.path.join(path, nm),
                                "depth": (depth+1)
                            }
                            if not self.silentqueuer:
                                log.debug("Queuing folder listing for %s", nm)
                            self.folders_queue.append(folder)
                    elif fexists:
                        self.writeSkipped(tfd, base64_path, nm)
                    elif self.end:
                        log.debug("Got exit signal. Discontinue recurse")
                        return
                except KeyboardInterrupt:
                    self.end = True
                    log.info("Program received exit signal")
                except: #Hopefully this won't get called
                    self.writeError(nm, tfd, base64_path, traceback.format_exc())
                else:
                    remainingtries = 0

    def process(self):
        log.debug("Initializing Bitcasa")
        bitc = BitcasaClient(utils.CLIENTID, utils.CLIENTSECRET, "https://rose-llc.com/bitcasafilelist/", self.accesstoken)
        if self.gdrive:
            log.debug("initializing GoogleDrive")
            self.g = GoogleDrive()
            if not self.g.test_auth():
                log.error("Unable to authenticate with google drive")
                return
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
                    time.sleep(10 * apiratecount)
                else:
                    log.error("Error could not retreive base folder")
                    return
        log.debug("Got base folder")
        if self.test:
            log.info("Nothing downloaded because this is a test")
            return

        log.debug("Queuing base folder")
        folder = {
            "folder": base,
            "path": "",
            "depth": 0
        }
        if self.gdrive:
            folder["folder_id"] = self.dest
        self.folders_queue.append(folder)
        log.debug("Starting Queuers and Downloader")
        self.downloader = DownloadThreaded(self)
        self.downloader.start()
        for qid in xrange(len(self.threads)):
            qid+=1
            queue_thread = QueueThreaded(str(qid), self)
            self.queuers.append({"thread":queue_thread, "processing":False, "qid":qid})
            queue_thread.start()
        self.end_process()

    def process_single(self):
        log.debug("Initializing Bitcasa")
        bitc = BitcasaClient(utils.CLIENTID, utils.CLIENTSECRET, "https://rose-llc.com/bitcasafilelist/", self.accesstoken)
        if self.gdrive:
            log.debug("initializing GoogleDrive")
            self.g = GoogleDrive()
            if not self.g.test_auth():
                log.error("Unable to authenticate with google drive")
                return
        log.debug("Getting file info")
        myfile = None
        remainingtries = 3
        if self.test:
            remainingtries = 1
        apiratecount = 0
        while myfile is None and remainingtries > 0:
            try:
                myfile = bitc.get_file_meta(self.basefolder)
            except BitcasaException as e:
                remainingtries -= 1
                if e.code == 9006:
                    apiratecount += 1
                    remainingtries += 1
                    log.warn("API rate limit reached. Will retry")
                else:
                    log.warn("Couldn't get file %s. Will retry %s more times", e.code, remainingtries)

                if remainingtries > 0:
                    time.sleep(10 * apiratecount)
                else:
                    log.error("Error could not retreive file")
                    return
        log.debug("Got file info")
        nm = myfile.name
        try:
            nm = utils.get_decoded_name(nm)
        except:
            log.warn("Error encoding to utf-8. Will parse anyway")
        if self.gdrive:
            filedownload = FileDownload(nm, myfile.path, myfile.size, nm, self.dest)
        else:
            tfd = os.path.join(self.dest, nm)
            filedownload = FileDownload(nm, myfile.path, myfile.size, tfd, self.dest)
        if not self.silentqueuer:
            log.debug("Queuing file download for %s", nm)
        self.todownload.append(filedownload)
        log.debug("Starting Downloader")
        self.downloader = DownloadThreaded(self)
        self.downloader.start()
        self.end_process()

    def end_process(self):
        # Give the queuers time to catch up
        error = True
        exit_signal = False
        while error:
            try:
                time.sleep(10)

                #wait for threads to finish downoading
                active = self.getActiveThreads()
                interval = time.time() + 60
                while len(active) > 0 or self.moreToQueue() or len(self.todownload) >0:
                    for thread in active:
                        if exit_signal:
                            log.info("Waiting for thread %s to shutdown", thread.name)
                        thread.join(5)
                    if not exit_signal:
                        time.sleep(15)
                        if self.progress and interval < time.time():
                            speed = utils.get_speed(self.bytestotal, self.downloadtime)
                            log.info("Downloaded %s at %s", utils.convert_size(self.bytestotal), speed)
                            interval = time.time() + 60
                    active = self.getActiveThreads()
                self.done = True
                while self.downloader.isAlive():
                    log.info("Waiting for Downloader to shutdown")
                    self.downloader.join(5)
            except KeyboardInterrupt:
                log.info("Program received exit signal")
                exit_signal = True
                error = True
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
        log.info("Done")

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
            return


    def writeSuccess(self, filept):
        try:
            with open(self.successfiles, 'a') as myfile:
                myfile.write("%s\n" % filept)
        except:
            log.exception("Error. Could not write to %s. Ending", self.successfiles)
            self.end = True

    def writeSkipped(self, tfd, base64_path, nm):
        log.debug("%s already exists. Skipping", nm)
        try:
            with open(self.skippedfiles, 'a') as myfile:
                myfile.write("%s||%s\n" % (tfd, base64_path))
        except:
            log.exception("Error. Could not write to %s. Ending", self.skippedfiles)
            self.end = True

    def writeError(self, nm, tfd, base64_path, e):
        log.error("Error processing file %s\n%s", nm, e)
        try:
            with open(self.errorfiles, 'a') as myfile:
                myfile.write("File||%s||%s\n" % (tfd, base64_path))
        except:
            log.exception("Error. Could not write to %s. Ending", self.errorfiles)
            self.end = True

    def writeErrorDir(self, nm, tfd, base64_path, e):
        log.error("Error processing folder %s\n%s", nm, e)
        try:
            with open(self.errorfiles, 'a') as myfile:
                 myfile.write("Folder||%s||%s\n" % (tfd, base64_path))
        except:
            log.exception("Error. Could not write to %s. Ending", self.errorfiles)
            self.end = True
def main():
    try:
        args = utils.get_args()
        bitc = BitcasaDownload(args)
        bitc.create_log_files()
        if args.single:
            bitc.process_single()
        else:
            bitc.process()
    except KeyboardInterrupt:
        log.info("Program received exit signal")


if __name__ == "__main__":
    main()
