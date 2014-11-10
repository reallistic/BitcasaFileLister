from Queue import Empty as EmptyException
import logging, traceback, os, urllib, time
from lib.bitcasa import BitcasaClient, BitcasaFolder, BitcasaFile
from lib.bitcasa.exception import BitcasaException
from lib.gdrive import GoogleDrive
from helpers import utils
log = logging.getLogger("BitcasaFileFetcher")

def folder_traverse(folder_queue, download_queue, results, args, should_exit, is_done):
    log.debug("Starting Queuer")
    if args.upload:
        g = GoogleDrive()
    while not should_exit.is_set():
        folder = None
        try:
            folder = folder_queue.get(True, 20)
        except EmptyException:
            log.debug("All folders processed. Shutting down")
            is_done.set()
            return

        if not args.silentqueuer:
            log.debug("Grabbing folder %s", folder["folder"].name)
        if args.upload:
            folder_list_gdrive(folder, folder_queue, download_queue, results, args, should_exit, g)
        else:
            folder_list(folder, folder_queue, download_queue, results, args, should_exit)
        try:
            folder_queue.task_done()
        except ValueError:
            pass
        
    if should_exit.is_set():
        log.debug("Clearing queue")
        try:
            while True:
                folder_queue.task_done()
        except ValueError:
            pass
    log.info("Shutting down")

def get_folder_items(fold, should_exit):
    remainingtries = 5
    apiratecount = 0
    folderitems = None
    while remainingtries > 0 and not should_exit.is_set():
        if apiratecount > 5:
            apiratecount = 5
        try:
            folderitems = fold.items
        except BitcasaException as e:
            if should_exit.is_set():
                return None
            remainingtries -= 1
            if e.code in [9006, 429]:
                apiratecount += 1
                remainingtries += 1
                log.warn("API rate limit reached. Will retry")
            elif e.code >= 500 and e.code < 600:
                apiratecount += 1
                remainingtries += 1
                log.warn("Bitcasa error. Will retry")
            else:
                log.warn("Failed to get folder contents %s. Will retry %s more times", e.code, remainingtries)

            if remainingtries > 0:
               time.sleep(10 * apiratecount)
            else:
                return None
        else:
            remainingtries = 0

    if folderitems is None:
        log.error("Failed getting folder items")
    return folderitems

def folder_list_gdrive(folder, folder_queue, download_queue, results, args, should_exit, g):
    fold = folder["folder"]
    path = folder["path"]
    folder_id = folder["folder_id"]
    depth = folder["depth"]

    if should_exit.is_set():
        log.debug("Stopping folder list")
        return
    if not args.silentqueuer and path:
        log.info(path)

    folderitems = get_folder_items(fold, should_exit)
    if folderitems is None:
        log.error("Error downloading at folder %s", path)
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
            encnm = nm.replace("'","\\'")
            base64_path = item.path
            filesize = None
            needtoupload = False
            tfd = os.path.join(path, nm)
            if isinstance(item, BitcasaFile):
                filesize = item.size
                needtoupload = g.need_to_upload(encnm, folder_id, filesize)
                if needtoupload:
                    if not args.silentqueuer:
                        log.debug("Queuing file download for %s", nm)
                    filedownload = {
                        "filename": nm,
                        "filepath": base64_path,
                        "filesize": filesize,
                        "fullpath": tfd,
                        "filedir": folder_id
                    }
                    download_queue.put(filedownload)
                else:
                    results.writeSkipped(tfd, base64_path, nm)

            elif isinstance(item, BitcasaFolder):
                if args.rec and (not args.depth or args.depth > depth):
                    g_fold = g.get_folder_byname(encnm, parent=folder_id, createnotfound=True)
                    remainingtries = 3
                    while not should_exit.is_set() and g_fold is None and remainingtries > 0:
                        remainingtries -= 1
                        log.error("Will retry to get/create %s %s more times", nm, remainingtries)
                        time.sleep(5)
                        g_fold = g.get_folder_byname(nm, parent=folder_id, createnotfound=True)
                    if should_exit.is_set():
                        log.debug("Stopping folder list")
                        return
                    if g_fold is None:
                        log.error("Failed to get/create folder")
                        return
                    if not args.silentqueuer:
                        log.debug("Queuing folder listing for %s", nm)
                    folder = {
                        "folder": item,
                        "depth": (depth+1),
                        "path": tfd,
                        "folder_id": g_fold["id"]
                    }
                    folder_queue.put(folder)
        except: #Hopefully this won't get called
            results.writeError(encnm, tfd, base64_path, traceback.format_exc())

def folder_list(folder, folder_queue, download_queue, results, args, should_exit):
    fold = folder["folder"]
    path = folder["path"]
    depth = folder["depth"]

    if should_exit.is_set():
        log.debug("Stopping folder list")
        return
    if path and not args.silentqueuer:
        log.info(path)
    fulldest = os.path.abspath(os.path.join(args.dst, path))
    remainingtries = 3
     #Create temp dir and dest dir if needed
    while fulldest and remainingtries > 0:
        if should_exit.is_set():
            log.debug("Stopping folder list")
            return
        try:
            try:
                os.makedirs(fulldest)
            except (OSError, IOError):
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
    if folderitems is None:
        log.error("Error downloading at folder %s", path)
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

                if fexists:
                    results.writeSkipped(tfd, base64_path, nm)
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
                    download_queue.put(filedownload)
            elif isinstance(item, BitcasaFolder):
                if args.rec and (not args.depth or args.depth > depth):
                    if not args.silentqueuer:
                        log.debug("Queuing folder listing for %s", nm)
                    folder = {
                        "folder": item,
                        "path": os.path.join(path, nm),
                        "depth": (depth+1)
                    }
                    folder_queue.put(folder)

        except: #Hopefully this won't get called
            results.writeError(nm, tfd, base64_path, traceback.format_exc())