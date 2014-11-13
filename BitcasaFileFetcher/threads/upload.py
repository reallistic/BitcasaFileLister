import time, os, logging
from helpers import utils
from lib.gdrive import GoogleDrive
import requests
from Queue import Empty as EmptyException

log = logging.getLogger("BitcasaFileFetcher")

class UploadError(Exception):
    pass

def upload(queue, should_exit, completed_uploads, results, args):
    log.debug("Starting up")
    g = GoogleDrive()
    while not should_exit.is_set():
        item = queue.get(True)
        if item is None:
            continue
        filename = item["filename"]
        size_bytes = item["filesize"]
        size_str = utils.convert_size(size_bytes)
        temp_file = item["temppath"]
        parent_id = item["filedir"]

        log.info("Uploading %s %s", filename, size_str)
        retriesleft = 10
        while retriesleft > 0 and not should_exit.is_set():
            g.get_service()
            try:
                st = time.time()
                timespan = 0
                log.debug("Uploading file %s to parent %s", filename, parent_id)
                result = g.upload_file(temp_file, filename, parent=parent_id)
                if not result:
                    raise UploadError("Upload failed")

                timespan = (time.time()-st)
                if should_exit.is_set():
                    log.debug("Stopping upload")
                    break
            except:
                retriesleft -= 1
                if retriesleft > 0:
                    g.delete_filebyname(filename, parent=parent_id)
                    log.exception("Error uploading file will retry %s more times", retriesleft)
                else:
                    cleanUpAfterError("Error %s could not be uploaded to" % filename, item, results)
            else:
                retriesleft = 0
                try:
                    os.remove(temp_file)
                except:
                    log.exception("Failed cleaning up temp file %s", temp_file)
                completed_uploads.append({
                    "timespan": timespan,
                    "size_uploaded": size_bytes,
                    "temppath": temp_file
                })
                if args.progress:
                    speed = utils.get_speed(size_bytes, timespan)
                    log.info("%s uploaded at %s", size_str, speed)
                log.info("Finished uploading %s", filename)
                results.writeSuccess(item["fullpath"], result["id"])
        try:
            queue.task_done()
        except ValueError:
            pass
        log.debug("End of thread")
    if should_exit.is_set():
        log.debug("Clearing queue")
        try:
            while True:
                queue.task_done()
        except ValueError:
            pass
    log.debug("Shutting down")

def cleanUpAfterError(e, item, results):
    results.writeError(item["filename"], item["fullpath"], item["filepath"], e)

    log.debug("End of thread")