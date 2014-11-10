import thread, time, os, logging
from hashlib import sha1
import requests
from helpers import utils

log = logging.getLogger("BitcasaFileFetcher")

BASE_URL = "https://developer.api.bitcasa.com/v1/files/"

from Queue import Empty as EmptyException

class SizeMismatchError(Exception):
    pass

try:
    WindowsError
except NameError:
    class WindowsError(Exception):
        pass

def download(args):
    log.debug("Starting up")
    queue, next_queue, should_exit, is_prev_done, session, completed_downloads, results, command_args = args
    progress = command_args.progress
    upload = command_args.upload
    while not should_exit.is_set():
        item = None
        try:
            item = queue.get(True, 20)
        except EmptyException:
            if not is_prev_done.is_set():
                item = None
            else:
                log.debug("Nothing more to download. Shutting down")
                return

        if item is None:
            continue

        filename = item["filename"]
        size_bytes = item["filesize"]
        size_str = utils.convert_size(size_bytes)
        temp_dir = item["filedir"]
        temp_file = item["fullpath"]
        log.info("%s size %s", filename, size_str)
        timespan = 0
         #TODO: Add a tuple to the download call in get files

        if command_args.temp:
            temp_dir = command_args.temp
            temp_file = os.path.join(temp_dir, filename)

        apidownloaduri = "%smyfile.ext?access_token=%s&path=%s" % (BASE_URL, command_args.token, item["filepath"])

        if (not upload and not os.path.exists(item["filedir"])) or (command_args.temp and not os.path.exists(temp_dir)):
            cleanUpAfterError("Missing temp or destination parent directory", item, results)
            continue

        if command_args.temp:
            filehash = sha1("blob " + str(size_bytes) + "\0" + temp_file)
            tmpname = filehash.hexdigest()
            temp_file = os.path.join(command_args.temp, tmpname)
            item["temppath"] = temp_file

        log.debug("Downloading file to %s", temp_file)
        retriesleft = 10
        apiratecount = 0
        while retriesleft > 0 and not should_exit.is_set():
            if apiratecount > 5:
                apiratecount = 5
            try:
                mode = "wb"
                filecomplete = False
                seek = 0
                sizecopied = 0
                try:
                    seek = os.path.getsize(temp_file)
                    if seek > size_bytes:
                        seek = 0
                    elif seek == size_bytes:
                        log.info("Found temp. Nothing to download")
                        filecomplete = True
                    elif seek > 0:
                        sizecopied += seek
                        log.info("continuing download")
                        mode = "ab"
                except:
                    pass
                if not filecomplete:
                    req = session.get(apidownloaduri, stream=True, timeout=120, headers={'Range':"bytes=%s-" % seek})
                    req.raise_for_status()
                    with open(temp_file, mode) as tmpfile:
                        st = time.time()
                        cr = st
                        progress_time = st + 60
                        timespan = 0
                        chunk_size = 1024 * 1024
                        for chunk in req.iter_content(chunk_size=chunk_size):
                            cr = time.time()
                            if should_exit.is_set() or not chunk:
                                break
                            tmpfile.write(chunk)
                            sizecopied += len(chunk)
                            if progress and progress_time < cr:
                                progress_time = cr + 60
                                speed = utils.get_speed(sizecopied-seek, (cr-st))
                                sizecopied_str = utils.convert_size(sizecopied)
                                time_left = utils.get_remaining_time(sizecopied-seek, size_bytes-sizecopied, (cr-st))
                                log.info(filename)
                                log.info("Downloaded %s of %s at %s. %s left", sizecopied_str, size_str, speed, time_left)
                        
                        if should_exit.is_set():
                            log.info("Stopping download")
                            break
                        elif sizecopied != size_bytes:
                            raise SizeMismatchError("Download size mismatch downloaded %s expected %s" % (sizecopied, size_bytes))
                        else:
                            timespan = (cr-st)

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.RequestException):
                retriesleft -= 1
                if req.status_code == 429:
                    apiratecount += 1
                    retriesleft += 1
                    log.warn("API rate limit reached. Will retry")
                else:
                    log.exception("Network error %s. Will retry %s more times", req.status_code, retriesleft)
                if retriesleft > 0:
                    time.sleep(10 * apiratecount)
                else:
                    log.error("Error downloading %s", filename)
                    cleanUpAfterError("Maximum retries reached", item, results)
            except SizeMismatchError:
                retriesleft -= 1
                log.exception("%s File size mismatch. Will retry %s more times", filename, retriesleft)
                if retriesleft > 0:
                    time.sleep(10)
                else:
                    cleanUpAfterError("Error downloading %s Maximum retries reached" % filename, item, results)
            except:
                retriesleft -= 1
                if retriesleft > 0:
                    log.exception("Error downloading %s. Will retry %s more times", filename, retriesleft)
                    time.sleep(10 * apiratecount)
                else:
                    cleanUpAfterError("An unknown error occurred", item, results)
            else:
                retriesleft = 0
                if timespan <= 0:
                    timespan = 1
                completed_downloads.append({
                    "timespan": timespan,
                    "size_downloaded": sizecopied,
                    "temppath": temp_file
                })
                if next_queue:
                    log.info("Finished download %s in %s", filename, utils.convert_time(timespan))
                    log.debug("Adding to next queue")
                    next_queue.put(item)
                else:
                    log.info("Finished download %s in %s", item["fullpath"], utils.convert_time(timespan))
                    results.writeSuccess(item["fullpath"])
                if progress:
                    speed = utils.get_speed(sizecopied-seek, timespan)
                    log.info("%s downloaded at %s", size_str, speed)
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