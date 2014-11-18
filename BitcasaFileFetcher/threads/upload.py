import time, os, logging
from helpers import utils
from lib.gdrive import GoogleDrive
from lib.googleapiclient.errors import HttpError
from Queue import Empty as EmptyException

log = logging.getLogger("BitcasaFileFetcher")

class UploadError(Exception):
    pass

def upload(status, should_exit, results, args):
    log.debug("Starting up")
    g = GoogleDrive()
    while not should_exit.is_set():
        apiratecount = 1
        try:
            item = status.up()
        except EmptyException:
            if status.queuers_active or status.down_active:
                continue
            else:
                log.debug("Nothing left to upload. Shutting down")
        if item is None:
            continue
        filename = item["filename"]
        size_bytes = item["filesize"]
        size_str = utils.convert_size(size_bytes)
        temp_file = item["temppath"]
        parent_id = item["filedir"]

        log.info("Uploading %s %s", filename, size_str)
        retriesleft = 10
        up_failed=True
        while retriesleft > 0 and not should_exit.is_set():
            if apiratecount > 5:
                apiratecount = 5
            try:
                g.get_service()
                needtoupload = g.need_to_upload(filename, parent_id, size_bytes)
                if needtoupload:
                    st = time.time()
                    timespan = 0
                    log.debug("Uploading file %s to parent %s", filename, parent_id)
                    result = g.upload_file(temp_file, filename, parent=parent_id)
                    if not result:
                        raise UploadError("Upload failed")
                    timespan = (time.time()-st)
            except HttpError as e:
                retriesleft -= 1
                if e.resp.status == 403:
                    apiratecount += 1
                    retriesleft += 1
                    log.warn("Google API rate limit reached. Will retry")
                else:
                    log.exception("Error uploading file will retry %s more times", retriesleft)

                if retriesleft > 0:
                    time.sleep(10 * apiratecount)
                else:
                    results.writeError(item["filename"], item["fullpath"], item["filepath"], "Error %s could not be uploaded" % filename)
            except:
                retriesleft -= 1
                if retriesleft > 0:
                    log.exception("Error uploading file will retry %s more times", retriesleft)
                    time.sleep(10 * apiratecount)
                else:
                    results.writeError(item["filename"], item["fullpath"], item["filepath"], "Error %s could not be uploaded" % filename)
            else:
                retriesleft = 0
                up_failed = False
                if not args.local:
                    try:
                        os.remove(temp_file)
                    except:
                        log.exception("Failed cleaning up temp file %s", temp_file)
                status.up({
                    "timespan": timespan,
                    "size_uploaded": size_bytes,
                    "temppath": temp_file
                })
                if args.progress:
                    speed = utils.get_speed(size_bytes, timespan)
                    log.info("%s uploaded at %s", size_str, speed)
                log.info("Finished uploading %s", filename)
                results.writeSuccess(item["fullpath"], result["id"])

        if up_failed:
            status.up_fail(item)
        log.debug("End of thread")

    log.debug("Shutting down")