from Queue import Empty as EmptyException
import logging, traceback, os, urllib, time
from lib.bitcasa import BitcasaClient, BitcasaFolder, BitcasaFile
from lib.bitcasa.exception import BitcasaException
from lib.gdrive import GoogleDrive
from lib.googleapiclient.errors import HttpError
from helpers import utils
log = logging.getLogger("BitcasaFileFetcher")

try:
    WindowsError
except NameError:
    class WindowsError(Exception):
        pass

def folder_traverse(status, results, args, should_exit):
    set_working = False
    log.debug("Starting Queuer")
    if args.upload:
        g = GoogleDrive()
    while not should_exit.is_set():
        folder = None
        try:
            folder = status.queue()
        except EmptyException:
            if status.queuers_active > 0:
                continue
            else:
                log.debug("All folders processed. Shutting down")
                return

        if args.upload:
            folder_list_gdrive(folder, status, results, args, should_exit, g)
        else:
            folder_list(folder, status, results, args, should_exit)
        status.queuing_done()

    log.info("Shutting down")

def get_folder_items(fold, should_exit):
    remainingtries = 5
    apiratecount = 1
    folderitems = None
    while remainingtries > 0 and not should_exit.is_set():
        if apiratecount > 5:
            apiratecount = 5
        try:
            folderitems = fold.items
        except BitcasaException as e:
            if should_exit.is_set():
                break
            remainingtries -= 1
            if e.code in [9006, 429]:
                apiratecount += 1
                remainingtries += 1
                log.warn("API rate limit reached. Will retry")
            elif e.code >= 500 and e.code < 600:
                apiratecount += 1
                remainingtries += 1
                log.warn("Bitcasa error %s getting files. Will retry" % e.code)
            else:
                log.warn("Failed to get folder contents %s. Will retry %s more times", e.code, remainingtries)

            if remainingtries > 0:
               time.sleep(10 * apiratecount)
            else:
                return None
        else:
            remainingtries = 0

    if should_exit.is_set():
        return None
    elif folderitems is None:
        log.error("Failed getting folder items")
    return folderitems

def get_local_items(fold, should_exit, results):
    folderitems = None
    try:
        folderlist = os.listdir(fold.path)
    except OSError:
        log.exception("Failed to get contents of %s", fold.path)
    else:
        folderitems = []
        for item in folderlist:
            fullpath = os.path.join(fold.path, item)
            if should_exit.is_set():
                break
            filesize = None
            try:
                if not os.path.isdir(fullpath):
                    filesize = os.path.getsize(fullpath)
            except OSError:
                log.exception("Error getting file info")
                results.writeError(item, fullpath, "", "Error listing file %s" % item)
                continue
            if filesize is not None:
                bitem = BitcasaFile(None, fullpath, item, None, filesize)
            else:
                bitem = BitcasaFolder(None, item, fullpath)

            folderitems.append(bitem)

    if should_exit.is_set():
        return None
    elif folderitems is None:
        log.error("Failed getting folder items")
    return folderitems


def folder_list_gdrive(folder, status, results, args, should_exit, g):
    fold = folder["folder"]
    path = folder["path"]
    folder_id = folder["folder_id"]
    depth = folder["depth"]

    if should_exit.is_set():
        log.debug("Stopping folder list")
        return
    if not args.silentqueuer and path:
        log.info(path)

    if args.local:
        folderitems = get_local_items(fold, should_exit, results)
    else:
        folderitems = get_folder_items(fold, should_exit)
    if folderitems is None:
        log.error("Error downloading at folder %s", path)
        if args.local:
            results.writeError(folder["folder"].name, path, folder_id, "")
        else:
            results.writeError(folder["folder"].name, path, folder["folder"].path, "")
        return
    for item in folderitems:
        if should_exit.is_set():
            log.debug("Stopping folder list")
            return
        try:
            nm = item.name
            try:
                nm = utils.get_decoded_name(nm)
            except:
                log.warn("Error removing special characters. Will try and parse anyway")

            base64_path = item.path
            filesize = None
            needtoupload = False
            tfd = os.path.join(path, nm)
            if isinstance(item, BitcasaFile):
                filesize = item.size
                retriesleft = 10
                apiratecount = 1
                while not should_exit.is_set() and retriesleft > 0:
                    try:
                        needtoupload = g.need_to_upload(nm, folder_id, filesize)
                    except HttpError as e:
                        retriesleft -= 1
                        if e.resp.status == 403:
                            apiratecount += 1
                            retriesleft += 1
                            log.warn("Google API rate limit reached. Will retry")
                        else:
                            log.exception("Error checking if %s exists will retry %s more times", nm, retriesleft)

                        if retriesleft > 0:
                            time.sleep(10 * apiratecount)
                        else:
                            results.writeError(nm, tfd, base64_path, "Error queuing file %s" % nm)
                    except:
                        retriesleft -= 1
                        log.exception("Error checking if %s exists will retry %s more times", nm, retriesleft)
                        if retriesleft > 0:
                            time.sleep(10 * apiratecount)
                        else:
                            results.writeError(nm, tfd, base64_path, "Error queuing file %s" % nm)
                    else:
                        retriesleft = 0
                if should_exit.is_set():
                    log.debug("Stopping folder list")
                    return
                if needtoupload:
                    if args.dryrun:
                        if not args.silentqueuer:
                            log.debug("%s %s", nm, filesize)
                        results.writeSuccess(tfd, base64_path)
                    else:
                        filedownload = {
                            "filename": nm,
                            "filepath": base64_path,
                            "filesize": filesize,
                            "fullpath": tfd,
                            "filedir": folder_id
                        }
                        if args.local:
                            if not args.silentqueuer:
                                log.debug("Queuing file download for %s", nm)
                            filedownload["temppath"] = base64_path
                            status.queue_up(filedownload)
                        else:
                            if not args.silentqueuer:
                                log.debug("Queuing file upload for %s", nm)
                            status.queue_down(filedownload)
                else:
                    results.writeSkipped(tfd, base64_path, nm)

            elif isinstance(item, BitcasaFolder):
                cnf = not args.dryrun
                if should_exit.is_set():
                    log.debug("Stopping folder list")
                    return
                if not args.rec or ( args.depth and args.depth <= depth ):
                    continue
                retriesleft = 10
                apiratecount = 1
                while not should_exit.is_set() and retriesleft > 0:
                    try:
                        g_fold = g.get_folder_byname(nm, parent=folder_id, createnotfound=True)
                    except HttpError as e:
                        retriesleft -= 1
                        if e.resp.status == 403:
                            apiratecount += 1
                            retriesleft += 1
                            log.warn("Google API rate limit reached. Will retry")
                        else:
                            log.exception("Will retry to get/create %s %s more times", nm, retriesleft)

                        if retriesleft > 0:
                            time.sleep(10 * apiratecount)
                        else:
                            results.writeError(nm, tfd, base64_path, "Failed to get/create folder %s" % nm)
                            continue
                    except:
                        retriesleft -= 1
                        log.error("Will retry to get/create %s %s more times", nm, retriesleft)
                        if retriesleft > 0:
                            time.sleep(10 * apiratecount)
                        else:
                            results.writeError(nm, tfd, base64_path, "Failed to get/create folder %s" % nm)
                            continue
                    else:
                        retriesleft = 0

                if should_exit.is_set():
                    log.debug("Stopping folder list")
                    return
                if not args.silentqueuer:
                    log.debug("Queuing folder listing for %s", nm)
                folder = {
                    "folder": item,
                    "depth": (depth+1),
                    "path": tfd,
                    "folder_id": g_fold["id"]
                }
                status.queue(folder)
        except:
            results.writeError(nm, tfd, base64_path, traceback.format_exc())

def folder_list(folder, status, results, args, should_exit):
    fold = folder["folder"]
    path = folder["path"]
    depth = folder["depth"]

    if should_exit.is_set():
        log.debug("Stopping folder list")
        return
    elif path and not args.silentqueuer:
        log.info(path)
    fulldest = os.path.abspath(os.path.join(args.dst, path))
    remainingtries = 3
     #Create temp dir and dest dir if needed
    while not args.dryrun and fulldest and remainingtries > 0:
        if should_exit.is_set():
            log.debug("Stopping folder list")
            return
        try:
            try:
                os.makedirs(fulldest)
            except (OSError, IOError, WindowsError):
                if not os.path.isdir(fulldest):
                    raise
        except:
            remainingtries -= 1
            log.exception("Couldn't create folder %s",fulldest)
            if remainingtries > 0:
                log.error("Will retry to create folder %s more times", remainingtries)
                time.sleep(2)
            else:
                results.writeErrorDir(fold.name, fulldest, fold.path, traceback.format_exc())
                return
        else:
            remainingtries = 0
    if not args.silentqueuer:
        log.debug(fulldest)
    folderitems = get_folder_items(fold, should_exit)
    if should_exit.is_set():
        log.debug("Stopping folder list")
        return
    elif folderitems is None:
        log.error("Error downloading at folder %s", path)
        results.writeError(folder["folder"].name, path, folder["folder"].path, "")
        return
    for item in folderitems:
        if should_exit.is_set():
            log.debug("Stopping folder list")
            return
        try:
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

                if should_exit.is_set():
                    log.debug("Stopping folder list")
                    return
                elif fexists:
                    results.writeSkipped(tfd, base64_path, nm)
                else:
                    if args.dryrun:
                        if not args.silentqueuer:
                            log.debug("%s %s", nm, filesize)
                        results.writeSuccess(tfd, base64_path)
                    else:
                        if not args.silentqueuer:
                            log.debug("Queuing file download for %s", nm)
                        filedownload = {
                            "filename": nm,
                            "filepath": base64_path,
                            "filesize": filesize,
                            "fullpath": tfd,
                            "filedir": fulldest
                        }
                        status.queue_down(filedownload)
            elif isinstance(item, BitcasaFolder):
                if should_exit.is_set():
                    log.debug("Stopping folder list")
                    return
                elif args.rec and (not args.depth or args.depth > depth):
                    if not args.silentqueuer:
                        log.debug("Queuing folder listing for %s", nm)
                    folder = {
                        "folder": item,
                        "path": os.path.join(path, nm),
                        "depth": (depth+1)
                    }
                    status.queue(folder)

        except: #Hopefully this won't get called
            results.writeError(nm, tfd, base64_path, traceback.format_exc())