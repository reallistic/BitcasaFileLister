import time, os, shutil, logging, errno
from helpers import utils
from Queue import Empty as EmptyException
log = logging.getLogger("BitcasaFileFetcher")
try:
    WindowsError
except NameError:
    class WindowsError(Exception):
        pass

def copy(status, should_exit, results, args):
    log.debug("Starting up")
    while not should_exit.is_set():
        try:
            item = status.copy()
        except EmptyException:
            if status.queuers_active or status.down_active:
                continue
            else:
                log.debug("Nothing left to move. Shutting down")

        if item is None:
            continue
        filename = item["filename"]
        size_bytes = item["filesize"]
        size_str = utils.convert_size(size_bytes)
        tmppath = item["temppath"]
        destpath = item["fullpath"]
        timespan = 0

        log.info("Moving %s %s", filename, size_str)
        retriesleft = 3
        sizecopied = 0
        seek = 0
        copy_failed = True
        while retriesleft > 0 and not should_exit.is_set():
            try:
                mode = "wb"
                filecomplete = False
                try:
                    seek = os.path.getsize(destpath)
                    tmpsize = os.path.getsize(tmppath)
                    if seek > tmpsize:
                        seek = 0
                    elif seek == tmpsize:
                        filecomplete = True
                    elif seek > 0:
                        mode = "ab"
                except:
                    pass
                if not filecomplete:
                    timespan = 0
                    st = time.time()
                    progress = st + 60
                    cr = st
                    with open(tmppath, 'rb') as f, open(destpath, mode) as fo:
                        if seek:
                            f.seek(seek)
                        while not should_exit.is_set():
                            piece = f.read(1024)
                            cr = time.time()
                            if args.progress and progress < cr:
                                progress = cr + 60
                                speed = utils.get_speed(sizecopied-seek, (cr-st))
                                log.info("%s Moved %s of %s at %s", filename, utils.convert_size(sizecopied), size_str, speed)
                            if piece:
                                fo.write(piece)
                                sizecopied += len(piece)
                            else:
                                break
                    timespan = (cr-st)
            except IOError as e:
                if e.errno == errno.ENOSPC:
                    log.critical("No space left on target disk. Exiting")
                    should_exit.set()
                else:
                    retriesleft -= 1
                    if retriesleft > 0:
                        log.exception("Error downloading %s. Will retry %s more times", filename, retriesleft)
                        time.sleep(10)
                    else:
                        log.exception("Error file could not be moved to %s", destpath)
                        results.writeError(item["filename"], item["fullpath"], item["filepath"], "Move failed")
            except: 
                retriesleft -= 1
                if retriesleft > 0:
                    log.exception("Error moving file will retry %s more times", retriesleft)
                    time.sleep(10)
                else:
                    log.exception("Error file could not be moved to %s", destpath)
                    results.writeError(item["filename"], item["fullpath"], item["filepath"], "Move failed")
            else:
                if not should_exit.is_set():
                    copy_failed = False
                    retriesleft = 0
                    if args.progress:
                        speed = utils.get_speed(sizecopied-seek, timespan)
                        log.info("%s %s moved at %s", filename, size_str, speed)
                    try:
                        os.remove(tmppath)
                    except:
                        log.exception("Failed cleaning up temp file %s", tmppath)

                    results.writeSuccess(destpath, item["filepath"])
                    status.copy({
                        "timespan": timespan,
                        "size_copied": sizecopied,
                        "temppath": tmppath,
                        "destpath": destpath
                    })
                    log.info("Finished moving %s", filename)
                else:
                    results.writeError(item["filename"], item["fullpath"], item["filepath"], "Move stopped")

        if copy_failed:
            status.copy_fail(item)

        log.debug("End of thread")

    log.info("Shutting down")
    
