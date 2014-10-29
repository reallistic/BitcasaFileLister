import threading, thread, time, os, shutil, traceback
import urllib, requests
from logger import logger as log
import utils

BASE_URL = "https://developer.api.bitcasa.com/v1/files/"

class SizeMismatchError(Exception):
    pass

class RunThreaded(threading.Thread):
    def __init__(self, item, tthdnum, fulldest, prt, fulltmp):
        threading.Thread.__init__(self)
        self.item = item
        self.nm = item.name
        self.pt = item.path
        self.szb = item.size
        self.sz = utils.convert_size(item.size)
        self.tthdnum = tthdnum
        self.fulldest = fulldest
        self.prt = prt
        self.fulltmp = fulltmp
        self.destpath = ""
        self.tmppath = ""

    def run(self):
        fulldest = self.fulldest
        tthdnum = self.tthdnum
        fulltmp = self.fulltmp
        nm = self.nm
        pt = self.pt
        sz = self.sz
        szb = self.szb
        st = time.time()
        sizecopied = 0
        log.info("Thread [%s]: %s size %s" % (tthdnum, nm, sz))
        params = {"access_token":self.prt.accesstoken, "path":pt}
        try:
            nm = nm.encode('utf-8')
        except:
            log.warn("Error encoding to utf-8. Will try download anyway")
        try:
            apidownloaduri = "%s%s?%s" % (BASE_URL, urllib.quote_plus(nm), urllib.urlencode(params))
        except KeyError:
            self.cleanUpAfterError("Thread[%s]: Error unsupported characters in filename %s" % (tthdnum, nm))
        except: #This technically should never happen but technically you never know
            self.cleanUpAfterError(traceback.format_exc())

        if not os.path.exists(fulldest) or not os.path.exists(fulltmp):
            self.cleanUpAfterError("Parent directory does not exist")
        
        destpath = os.path.join(fulldest, nm)
        tmppath = os.path.join(fulltmp, nm)
        self.destpath = destpath
        self.tmppath = tmppath

        log.debug("Thread [%s]: %s" % (tthdnum, apidownloaduri))
        log.debug("Thread [%s]: Downloading file to %s" % (tthdnum, tmppath))
        retriesleft = 3
        while retriesleft > 0:
            sizecopied = 0
            try:
                req = requests.get(apidownloaduri, stream=True, timeout=120)
                with open(tmppath, 'wb') as tmpfile:
                    for chunk in req.iter_content(chunk_size=1024):
                        sizecopied += len(chunk)
                        if self.prt.end:
                            break
                        if chunk: # filter out keep-alive new chunks
                            tmpfile.write(chunk)
                            tmpfile.flush()
                            os.fsync(tmpfile.fileno())
                if sizecopied != szb and not self.prt.end:
                    raise SizeMismatchError("Download size mismatch downloaded %s expected %s" % (sizecopied, szb))
                elif self.prt.end:
                    self.cleanUpAfterError("Thread [%s]: Recieved signaled stop during download" % tthdnum)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException):
                log.debug("Thread [%s]: Network error. Will retry %s more times" % (tthdnum, retriesleft))
                retriesleft -= 1
                if retriesleft > 0:
                    time.sleep(10)
                else:
                    log.error("Thread [%s]: error downloading %s" % (tthdnum, nm))
                    self.cleanUpAfterError("Maximum retries reached")
            except SizeMismatchError:
                log.debug("Thread [%s]: File size mismatch Will retry %s more times" % (tthdnum, retriesleft))
                retriesleft -= 1
                if retriesleft > 0:
                    time.sleep(10)
                else:
                    log.error("Thread [%s]: error downloading %s" % (tthdnum, nm))
                    self.cleanUpAfterError("Maximum retries reached")
            except OSError:
                log.error("Thread [%s]: error writing to file %s" % (tthdnum, nm))
                self.cleanUpAfterError(traceback.format_exc())
            except (requests.exceptions.RequestException, Exception):
                log.error("Thread [%s]: error downloading %s" % (tthdnum, nm))
                self.cleanUpAfterError(traceback.format_exc())
            except SystemExit:
                raise
            else:
                retriesleft = 0

        log.debug("Thread [%s]: Download finished." % tthdnum)
        if not self.prt.end:
            self.prt.bytestotal += szb
            speed = utils.get_speed(szb, (time.time()-st))
            log.debug("Thread [%s]: %s downloaded at %s" % (tthdnum, sz, speed))
            st = time.time()
            if not self.prt.local:
                log.debug("Thread [%s]: %s copying from temp to dest" % (tthdnum, nm))
                try:
                    shutil.copy2(tmppath, destpath)
                    with open(tmppath, "rb") as f:
                        with open(destpath, "wb") as fo:
                            for line in f:
                                if not self.prt.end:
                                    fo.write(line)
                                else:
                                    break
                    if self.prt.end:
                        self.cleanUpAfterError("Thread [%s]: Recieved signaled stop during copy")
                except OSError:
                    self.cleanUpAfterError("Thread [%s]: Could not copy %s to destination" % (tthdnum, nm))
                except SystemExit:
                    raise
                else:
                    speed = utils.get_speed(szb, (time.time()-st))
                    log.debug("Thread [%s]: %s copied at %s" % (tthdnum, sz, speed))
                    self.prt.writeSuccess(tthdnum, fulldest)
                    log.info("Thread [%s]: Finished download %s" % (tthdnum, destpath))
                    self.prt.numthreads -= 1
                    try:
                        os.remove(tmppath)
                    except OSError:
                        log.warn("Failed cleaning up tmp file %s" % tmppath)
        else:
            log.warn("Thread [%s]: Parent signaled stop")


    def cleanUpAfterError(self, e):
        pt = self.pt
        tmppath = self.tmppath
        destpath = self.destpath
        tthdnum = self.tthdnum

        #log file to errorfiles.txt
        self.prt.writeError(tthdnum, self.nm, destpath, self.pt, e)

        #cleanup destination file
        try:
            if os.path.exists(destpath):
                os.remove(destpath)
        except OSError:
            log.warn("Thread [%s]: Couldn't clean up file %s" % (tthdnum, destpath))

        #cleanup temp file
        try:
            if os.path.exists(tmppath) and destpath != tmppath:
                os.remove(tmppath)
        except OSError:
            log.warn("Thread [%s]: Couldn't clean up file %s" % (tthdnum, destpath))

        log.error("Thread [%s]: Download failed %s\n%s" % (tthdnum, tmppath, e))

        self.prt.numthreads -= 1
        thread.exit()