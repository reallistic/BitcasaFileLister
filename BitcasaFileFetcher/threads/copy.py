import time, os, shutil, logging, codecs
from helpers import utils
from Queue import Empty as EmptyException
log = logging.getLogger("BitcasaFileFetcher")
try:
    WindowsError
except NameError:
    class WindowsError(Exception):
        pass

def copy(queue, should_exit, completed_copies, results, args):
    log.debug("Starting up")
    while not should_exit.is_set():
        item = queue.get(True)
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
        while retriesleft > 0 and not should_exit.is_set():
            try:
                mode = "w"
                filecomplete = False
                try:
                    seek = os.path.getsize(destpath)
                    tmpsize = os.path.getsize(tmppath)
                    if seek > tmpsize:
                        seek = 0
                    elif seek == tmpsize:
                        filecomplete = True
                    elif seek > 0:
                        mode = "a"
                except:
                    pass
                if not filecomplete:
                    timespan = 0
                    st = time.time()
                    progress = st + 60
                    cr = st
                    with codecs.open(tmppath, 'r', 'utf-8') as f, codecs.open(destpath, mode, 'utf-8') as fo:
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
                if should_exit.is_set():
                    log.info("Stopping Move")
            except: 
                retriesleft -= 1
                if retriesleft > 0:
                    log.exception("Error moving file will retry %s more times", retriesleft)
                else:
                    log.exception("Error file could not be moved to %s", destpath)
                    results.writeError(item["filename"], item["fullpath"], item["filepath"], "Move failed")
            else:
                retriesleft = 0
                if args.progress:
                    speed = utils.get_speed(sizecopied-seek, timespan)
                    log.info("%s %s moved at %s", filename, size_str, speed)
                try:
                    os.remove(tmppath)
                except:
                    log.exception("Failed cleaning up temp file %s", tmppath)

                results.writeSuccess(destpath, item["filepath"])
                completed_copies.append({
                    "timespan": timespan,
                    "size_copied": sizecopied,
                    "temppath": tmppath,
                    "destpath": destpath
                })
                log.info("Finished moving %s", filename)
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
    log.info("Shutting down")
    
