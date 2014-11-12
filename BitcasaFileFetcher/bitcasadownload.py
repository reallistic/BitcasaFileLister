import time, os, sys, traceback, threading, requests, logging
from helpers import utils, results
from lib.bitcasa import BitcasaException, BitcasaFolder
from threads import DownloadThread, UploadThread, FolderThread, CopyThread
from collections import deque
from lib.gdrive import GoogleDrive
from Queue import Queue

log = logging.getLogger("BitcasaFileFetcher")

class BitcasaDownload(object):
    def __init__(self, args, client, should_exit):
        log.debug("src: %s", args.src)
        log.debug("dst: %s", args.dst)
        log.debug("at: %s", args.token)
        log.debug("tmp: %s", args.temp)
        log.debug("upload: %s", args.upload)
        if args.upload:
            log.debug("provider: %s", args.provider)
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
        self.temp_dir = args.temp
        #bittcasa base64 encdoded path
        self.basefolder = args.src
        if args.single:
            log.debug("Downloading single file. Setting max threads to 1")
            args.threads = 1
            args.folderthreads = 1
        #Recursion
        self.rec = args.rec
        #Recursion max depth
        self.depth = args.depth
        #Log dir
        self.logdir = args.logdir
        #log progress
        self.progress = args.progress
        #Upload to google drive
        self.upload = args.upload
        #Don't log queuer activity
        self.silentqueuer = args.silentqueuer
        #Download a single file
        self.single = args.single

        self.args = args

        #Initialize
        self.should_exit = should_exit
        self.st = time.time()
        self.client = client
        self.session = requests.Session()
        self.results = results.Results(args.logdir, should_exit, args.nofilelog)

        # Analytics
        self.uploadtime = 0
        self.downloadtime = 0
        self.copytime = 0
        self.bytestotal = 0

        # Threads        
        self.download_threads = []
        self.upload_threads = []
        self.copy_threads = []
        self.folder_threads = []

        # item queues
        self.folder_queue = Queue(0)
        self.download_queue = Queue(0)
        self.copy_queue = Queue(0)
        self.upload_queue = Queue(0)

        # completed items
        self.completed_downloads = []
        self.completed_uploads = []
        self.completed_copies = []

        #completed signals
        self.folders_done = threading.Event()


    def process(self, base=None):
        log.debug("Getting base folder")
        remainingtries = 3
        apiratecount = 0
        while base is None and remainingtries > 0 and not self.should_exit.is_set():
            try:
                base = self.client.get_folder(self.basefolder)
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
                    log.error("Error could not retrieve base folder")
                    return
        if self.should_exit.is_set():
            return
        log.debug("Queuing base folder")
        folder = {
            "folder": base,
            "path": "",
            "depth": 0
        }

        next_queue = None
        upload_args = None
        copy_args = None
        if self.upload:
            folder["folder_id"] = self.dest
            next_queue = self.upload_queue
            upload_args = ( self.upload_queue, self.should_exit, self.completed_uploads, self.results, self.args)
        elif self.temp_dir:
            next_queue = self.copy_queue
            copy_args = ( self.copy_queue, self.should_exit, self.completed_copies, self.results, self.args )
        
        download_args = ( self.download_queue, next_queue, self.should_exit, self.folders_done, self.session, self.completed_downloads, self.results, self.args)
        folder_args = ( self.folder_queue, self.download_queue, self.results, self.args, self.should_exit, self.folders_done )
        self.folder_queue.put(folder)
        if not self.args.dryrun:
            log.debug("Starting Queuers and Downloaders")
            for qid in xrange(self.args.threads):
                qid += 1
                download_thread = threading.Thread(target=DownloadThread, args=(download_args,), name="Download %s" % qid)
                download_thread.daemon = True
                download_thread.start()
                self.download_threads.append(download_thread)
        else:
            log.debug("Starting Queuers")

        for qid in xrange(self.args.folderthreads):
            qid += 1
            folder_thread = threading.Thread(target=FolderThread, args=folder_args, name="Queuer %s" % qid)
            folder_thread.daemon = True
            folder_thread.start()
            self.folder_threads.append(folder_thread)

        if not self.args.dryrun and self.upload:
            for qid in xrange(self.args.threads):
                qid += 1
                upload_thread = threading.Thread(target=UploadThread, args=upload_args, name="Upload %s" % qid)
                upload_thread.daemon = True
                upload_thread.start()
                self.upload_threads.append(upload_thread)
        elif not self.args.dryrun and self.temp_dir:
            for qid in xrange(self.args.threads):
                qid += 1
                copy_thread = threading.Thread(target=CopyThread, args=copy_args, name="Move %s" % qid)
                copy_thread.daemon = True
                copy_thread.start()
                self.copy_threads.append(copy_thread)
        
        self.end_process()

    def process_single(self):
        log.debug("Getting file info")
        myfile = None
        remainingtries = 3
        apiratecount = 0
        while myfile is None and remainingtries > 0 and not self.should_exit.is_set():
            try:
                myfile = self.client.get_file_meta(self.basefolder)
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
                    log.error("Error could not retrieve file")
                    return
        log.debug("Got file info")
        fold = BitcasaFolder(self.client, "root", "", items=[myfile])
        self.process(fold)

    def end_process(self):
        # Give the queuers time to catch up
        try:
            if not self.should_exit.is_set():
                time.sleep(10)
        except (KeyboardInterrupt, IOError):
            pass

        self.folder_queue.join()
        self.download_queue.join()
        self.copy_queue.join()
        self.upload_queue.join()
        log.debug("Finished waiting")

        end_time = time.time()
        total_uploaded_b = 0
        total_downloaded_b = 0
        total_copied_b = 0

        total_uploaded_t = 0
        total_downloaded_t = 0
        total_copied_t = 0

        for item in self.completed_uploads:
            total_uploaded_t += item["timespan"]
            total_uploaded_b += item["size_uploaded"]

        for item in self.completed_downloads:
            total_downloaded_t += item["timespan"]
            total_downloaded_b += item["size_downloaded"]

        for item in self.completed_copies:
            total_copied_t += item["timespan"]
            total_copied_b += item["size_copied"]

        #Log final speed and statistics
        if not self.args.dryrun:
            downspeed = utils.get_speed(total_downloaded_b, total_downloaded_t)
            copyspeed = utils.get_speed(total_copied_b, total_copied_t)
            upspeed = utils.get_speed(total_uploaded_b, total_uploaded_t)
            runspeed = utils.get_speed(total_downloaded_b, (end_time - self.st))

            log.info("Total download time: %s", utils.convert_time(total_downloaded_t))
            if self.args.upload:
                log.info("Total upload time: %s", utils.convert_time(total_uploaded_t))
            elif self.temp_dir:
                log.info("Total copy time: %s", utils.convert_time(total_copied_t))

            log.info("Total run time: %s", utils.convert_time(end_time - self.st))

            log.info("Download speed: %s at %s", utils.convert_size(total_downloaded_b), downspeed)
            if self.upload:
                log.info("Upload speed: %s at %s", utils.convert_size(total_uploaded_b), upspeed)
            elif self.temp_dir:
                log.info("Copy speed: %s at %s", utils.convert_size(total_copied_b), copyspeed)

            log.info("Program run speed: %s at %s", utils.convert_size(total_downloaded_b), runspeed)
