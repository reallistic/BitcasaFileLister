from helpers import utils
from threading import Semaphore
import time, logging
from Queue import Queue

log = logging.getLogger("BitcasaFileFetcher")

class Status(object):
    """Status of queuing, downloading, uploading, and copying"""
    def __init__(self, should_exit):
        self.should_exit = should_exit

        self.queues = 0
        self.queuers_active = 0
        self.queue_busy = Semaphore(1)
        self.folder_queue = Queue(0)

        self.down_bytes = 0
        self.down_files = 0
        self.down_active = 0
        self.down_active_b = 0
        self.down_complete = []
        self.down_failed = []
        self.down_busy = Semaphore(1)
        self.down_queue = Queue(0)

        self.up_bytes = 0
        self.up_files = 0
        self.up_active = 0
        self.up_active_b = 0
        self.up_complete = []
        self.up_failed = []
        self.up_busy = Semaphore(1)
        self.up_queue = Queue(0)

        self.copy_files = 0
        self.copy_bytes = 0
        self.copy_active = 0
        self.copy_active_b = 0
        self.copy_complete = []
        self.copy_failed = []
        self.copy_busy = Semaphore(1)
        self.copy_queue = Queue(0)
        self.st = time.time()

    def shutdown(self):
        log.info("Shutting down queues")
        try:
            while self.queues > self.queuers_active:
                self.queues -= 1
                self.folder_queue.task_done()
        except:
            pass

        try:
            while self.down_files > self.down_active:
                self.down_queue.task_done()
        except:
            pass

        try:
            while self.up_files > self.up_active:
                self.up_queue.task_done()
        except:
            pass

        try:
            while self.copy_files > self.copy_active:
                self.copy_queue.task_done()
        except:
            pass

    def join_queues(self):
        while self.queuers_active > 0 and not self.should_exit.is_set():
            self.folder_queue.join()

        while self.down_active > 0 and not self.should_exit.is_set():
            self.down_queue.join()

        while self.copy_active > 0 and not self.should_exit.is_set():
            self.copy_queue.join()

        while self.up_active > 0 and not self.should_exit.is_set():
            self.up_queue.join()

    def queue(self, item=None):
        if item:
            self.queue_busy.acquire()
            self.queues += 1
            self.folder_queue.put(item)
            self.queue_busy.release()
        else:
            item = self.folder_queue.get(True, 20)
            self.queue_busy.acquire()
            self.queuers_active += 1
            self.queue_busy.release()
        return item

    def queuing_done(self):
        self.queue_busy.acquire()
        self.queuers_active -= 1
        self.queues -= 1
        self.queue_busy.release()
        try:
            self.folder_queue.task_done()
        except:
            pass

    def down_fail(self, item):
        self.down_busy.acquire()
        self.down_files -= 1
        self.down_active -= 1
        self.down_active_b -= item["filesize"]
        self.down_bytes -= item["filesize"]
        self.down_failed.append(item)
        self.down_busy.release()
        try:
            self.down_queue.task_done()
        except:
            pass

    def down(self, item=None):
        if item:
            self.down_busy.acquire()
            self.down_files -= 1
            self.down_active -= 1
            self.down_active_b -= item["size_downloaded"]
            self.down_bytes -= item["size_downloaded"]
            self.down_complete.append(item)
            self.down_busy.release()
            try:
                self.down_queue.task_done()
            except:
                pass
        else:
            item = self.down_queue.get(True, 20)
            self.down_busy.acquire()
            self.down_active += 1
            self.down_active_b += item["filesize"]
            self.down_busy.release()
        return item

    def queue_down(self, item):
        self.down_queue.put(item)
        self.down_busy.acquire()
        self.down_files += 1
        self.down_bytes += item["filesize"]
        self.down_busy.release()

    def up_fail(self, item):
        self.up_busy.acquire()
        self.up_files -= 1
        self.up_active -= 1
        self.up_active_b -= item["filesize"]
        self.up_bytes -= item["filesize"]
        self.up_failed.append(item)
        self.up_busy.release()
        try:
            self.up_queue.task_done()
        except:
            pass

    def up(self, item=None):
        if item:
            self.up_busy.acquire()
            self.up_files -= 1
            self.up_active -= 1
            self.up_active_b -= item["size_uploaded"]
            self.up_bytes -= item["size_uploaded"]
            self.up_complete.append(item)
            self.up_busy.release()
            try:
                self.up_queue.task_done()
            except:
                pass
        else:
            item = self.up_queue.get(True, 20)
            self.up_busy.acquire()
            self.up_active += 1
            self.up_active_b += item["filesize"]
            self.up_busy.release()
        return item

    def queue_up(self, item):
        self.up_queue.put(item)
        self.up_busy.acquire()
        self.up_files += 1
        self.up_bytes += item["filesize"]
        self.up_busy.release()

    def copy_fail(self, item):
        self.copy_busy.acquire()
        self.copy_active -= 1
        self.copy_files -= 1
        self.copy_active_b -= item["filesize"]
        self.copy_bytes -= item["filesize"]
        self.copy_failed.append(item)
        self.copy_busy.release()
        try:
            self.copy_queue.task_done()
        except:
            pass

    def copy(self, item=None):
        if item:
            self.copy_busy.acquire()
            self.copy_active -= 1
            self.copy_files -= 1
            self.copy_active_b -= item["size_copied"]
            self.copy_bytes -= item["size_copied"]
            self.copy_complete.append(item)
            self.copy_busy.release()
            try:
                self.copy_queue.task_done()
            except:
                pass
        else:
            item = self.copy_queue.get(True, 20)
            self.copy_busy.acquire()
            self.copy_active_b += item["filesize"]
            self.copy_active += 1
            self.copy_busy.release()
        return item

    def queue_copy(self, item):
        self.copy_queue.put(item)
        self.copy_busy.acquire()
        self.copy_files += 1
        self.copy_bytes += item["filesize"]
        self.copy_busy.release()


    def StatusThread(status, upload, temp, should_exit):
        log.debug("Starting up")
        while not should_exit.is_set():
            time.sleep(120)
            if status.queues > 0:
                log.info("%s folders left to process", status.queues)
            if status.queuers_active > 0:
                log.info("%s folder queuers active", status.queuers_active)
            if status.down_files > 0:
                log.info("%s files, %s left to download", status.down_files, utils.convert_size(status.down_bytes))
            if len(status.down_failed) > 0:
                log.info("%s downloads failed", len(status.down_failed))
            if status.down_active > 0:
                log.info("%s files, %s currently downloading", status.down_active, utils.convert_size(status.down_active_b))
            if upload:
                if status.up_files > 0:
                    log.info("%s files, %s left to upload", status.up_files, utils.convert_size(status.up_bytes))
                if len(status.up_failed) > 0:
                    log.info("%s uploads failed", len(status.up_failed))
                if status.up_active > 0:
                    log.info("%s files, %s currently uploading", status.up_active, utils.convert_size(status.up_active_b))
            elif temp:
                if status.copy_files > 0:
                    log.info("%s files, %s left to move", status.copy_files, utils.convert_size(status.copy_bytes))
                if len(status.copy_failed) > 0:
                    log.info("%s copies failed", len(status.copy_failed))
                if status.copy_active > 0:
                    log.info("%s files, %s currently moving", status.copy_active, utils.convert_size(status.copy_active_b))

            status.final_status(upload, temp)

    def final_status(self, upload, temp, final=False):
        end_time = time.time()
        start_time = self.st
        total_uploaded_b = 0
        total_downloaded_b = 0
        total_copied_b = 0

        total_uploaded_t = 0
        total_downloaded_t = 0
        total_copied_t = 0

        for item in self.up_complete:
            total_uploaded_t += item["timespan"]
            total_uploaded_b += item["size_uploaded"]

        for item in self.down_complete:
            total_downloaded_t += item["timespan"]
            total_downloaded_b += item["size_downloaded"]

        for item in self.copy_complete:
            total_copied_t += item["timespan"]
            total_copied_b += item["size_copied"]

        downspeed = utils.get_speed(total_downloaded_b, total_downloaded_t)
        copyspeed = utils.get_speed(total_copied_b, total_copied_t)
        upspeed = utils.get_speed(total_uploaded_b, total_uploaded_t)
        runspeed = utils.get_speed(total_downloaded_b, (end_time - start_time))
        uprunspeed = utils.get_speed(total_uploaded_b, (end_time - start_time))
        copyrunspeed = utils.get_speed(total_copied_b, (end_time - start_time))
        if final or total_downloaded_t > 0:
            log.info("Total download time: %s", utils.convert_time(total_downloaded_t))
        if upload and (final or total_uploaded_t):
            log.info("Total upload time: %s", utils.convert_time(total_uploaded_t))
        elif temp and (final or total_copied_t):
            log.info("Total copy time: %s", utils.convert_time(total_copied_t))

        log.info("Total run time: %s", utils.convert_time(end_time - start_time))

        if final or total_downloaded_b:
            log.info("Download speed: %s at %s", utils.convert_size(total_downloaded_b), downspeed)
        if upload and (final or total_uploaded_b):
            log.info("Upload speed: %s at %s", utils.convert_size(total_uploaded_b), upspeed)
        elif temp and (final or total_copied_b):
            log.info("Copy speed: %s at %s", utils.convert_size(total_copied_b), copyspeed)
        if final or total_downloaded_b:
            log.info("Overall download speed: %s at %s", utils.convert_size(total_downloaded_b), runspeed)
        if upload and (final or total_uploaded_b):
            log.info("Overall upload speed: %s at %s", utils.convert_size(total_uploaded_b), uprunspeed)
        elif temp and (final or total_copied_b):
            log.info("Overall copy speed: %s at %s", utils.convert_size(total_copied_b), copyrunspeed)