import time, os, sys, traceback, threading, requests, logging
from helpers import utils, results
from lib.bitcasa import BitcasaException, BitcasaFolder, BitcasaFile
from threads import DownloadThread, UploadThread, FolderThread, CopyThread
from collections import deque
from lib.gdrive import GoogleDrive
from Queue import Queue
from status import Status

log = logging.getLogger("BitcasaFileFetcher")

class BitcasaDownload(object):
    def __init__(self, args, client, should_exit):
        log.debug("source dir: %s", args.src)
        log.debug("destination dir: %s", args.dst)
        log.debug("temp dir: %s", args.temp)
        log.debug("upload: %s", args.upload)
        if args.upload:
            log.debug("provider: %s", args.provider)
        log.debug("log dir: %s", args.logdir)
        log.debug("recursion: %s", args.rec)
        log.debug("depth: %s", args.depth)
        log.debug("max folder threads: %s", args.folderthreads)
        log.debug("max download threads: %s", args.threads)
        log.debug("progress: %s", args.progress)
        log.debug("silent queuer: %s", args.silentqueuer)
        log.debug("single: %s", args.single)

        #bittcasa base64 encdoded path
        self.basefolder = args.src
        if args.single:
            log.debug("Downloading single file. Setting max threads to 1")
            args.threads = 1
            args.folderthreads = 1

        self.args = args

        #Initialize
        self.should_exit = should_exit
        self.client = client
        self.session = requests.Session()
        self.results = results.Results(args.logdir, should_exit, args.nofilelog)

        # Threads        
        self.download_threads = []
        self.upload_threads = []
        self.copy_threads = []
        self.folder_threads = []

        self.status = Status(should_exit)
        self.shutdown_sent = False

    def shutdown(self):
        if not self.shutdown_sent:
            self.shutdown_sent = True
            self.status.shutdown()

    def get_status(self):
        return self.status

    def process(self, base=None):
        log.debug("Getting base folder")
        if self.args.upload and self.args.local and base is None:
            base = BitcasaFolder(None, "root", self.basefolder)
        else:
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

        if self.args.upload:
            folder["folder_id"] = self.args.dst
        
        step2_args = ( self.status, self.should_exit, self.results, self.args )
        download_args = ( self.status, self.should_exit, self.session, self.results, self.args)
        folder_args = ( self.status, self.results, self.args, self.should_exit )

        self.status.queue(folder)
        if not self.args.dryrun and not self.args.local:
            log.debug("Starting Downloaders")
            for qid in xrange(self.args.threads):
                qid += 1
                download_thread = threading.Thread(target=DownloadThread, args=download_args, name="Download %s" % qid)
                download_thread.daemon = True
                download_thread.start()
                self.download_threads.append(download_thread)
        
        log.debug("Starting Queuers")
        for qid in xrange(self.args.folderthreads):
            qid += 1
            folder_thread = threading.Thread(target=FolderThread, args=folder_args, name="Queuer %s" % qid)
            folder_thread.daemon = True
            folder_thread.start()
            self.folder_threads.append(folder_thread)

        if not self.args.dryrun and self.args.upload:
            log.debug("Starting Uploaders")
            for qid in xrange(self.args.threads):
                qid += 1
                upload_thread = threading.Thread(target=UploadThread, args=step2_args, name="Upload %s" % qid)
                upload_thread.daemon = True
                upload_thread.start()
                self.upload_threads.append(upload_thread)
        elif not self.args.dryrun and self.args.temp:
            log.debug("Starting Movers")
            for qid in xrange(self.args.threads):
                qid += 1
                copy_thread = threading.Thread(target=CopyThread, args=step2_args, name="Move %s" % qid)
                copy_thread.daemon = True
                copy_thread.start()
                self.copy_threads.append(copy_thread)
        
        if self.args.progress:
            self.status_thread = threading.Thread(target=self.status.StatusThread, args=(self.args.upload, self.args.temp, self.should_exit), name="Progress")
            self.status_thread.daemon = True
            self.status_thread.start()
        self.end_process()

    def process_single(self):
        log.debug("Getting file info")
        myfile = None
        if self.args.upload and self.args.local:
            size = 0
            name = ""
            try:
                if os.path.isdir(self.basefolder):
                    raise OSError("Incorrect file")
                size = os.path.getsize(self.basefolder)
                name = os.path.basename(self.basefolder)
            except OSError:
                log.exception("Error getting file")
                return
            myfile = BitcasaFile(None, self.basefolder, name, None, size)
            fold = BitcasaFolder(None, "root", "", items=[myfile])
        else:
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
            fold = BitcasaFolder(self.client, "root", "", items=[myfile])
        log.debug("Got file info")
        self.process(fold)

    def end_process(self):
        # Give the queuers time to catch up
        try:
            if not self.should_exit.is_set():
                time.sleep(10)
        except (KeyboardInterrupt, IOError):
            pass

        self.status.join_queues()
        log.debug("Finished waiting")

        #Log final speed and statistics
        if not self.args.dryrun:
            self.status.final_status(self.args.upload, self.args.temp, final=True)
