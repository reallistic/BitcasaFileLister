import threading, thread, time, os, shutil, traceback
import urllib, requests
from logger import logger as log
import utils

BASE_URL = "https://developer.api.bitcasa.com/v1/files/"

class SizeMismatchError(Exception):
    pass

class RunThreaded(threading.Thread):
    def __init__(self, item, tthdnum, fulldest, prt, fulltmp):
        threading.Thread.__init__(self, name=tthdnum)
        #super().__init__(name=tthdnum)
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
        if self.prt.tmp:
            fulltmp = self.fulltmp
        else:
            fulltmp = fulldest
        nm = self.nm
        pt = self.pt
        sz = self.sz
        szb = self.szb
        st = time.time()
        sizecopied = 0
        log.info("%s size %s", nm, sz)
        params = {"access_token":self.prt.accesstoken, "path":pt}
        try:
            nm = nm.encode('utf-8')
        except:
            log.warn("Error encoding to utf-8. Will try download anyway")
        try:
            apidownloaduri = "%s%s?%s" % (BASE_URL, urllib.quote_plus(nm), urllib.urlencode(params))
        except KeyError:
            self.cleanUpAfterError("Error unsupported characters in filename %s" % nm, fulltmp)
        except: #This technically should never happen but technically you never know
            self.cleanUpAfterError(traceback.format_exc(), fulltmp)

        if not os.path.exists(fulldest) or (self.prt.tmp and not os.path.exists(fulltmp)):
            self.cleanUpAfterError("Missing temp or destination parent directory", fulltmp)
        
        destpath = os.path.join(fulldest, nm)
        tmppath = os.path.join(fulltmp, nm)
        self.destpath = destpath
        self.tmppath = tmppath

        log.debug("Downloading file to %s", tmppath)
        retriesleft = 3
        sizemismatched = False
        while retriesleft > 0:
            sizecopied = 0
            progress = time.time() + 60
            try:
                req = requests.get(apidownloaduri, stream=True, timeout=120)
                with open(tmppath, 'wb') as tmpfile:
                    for chunk in req.iter_content(chunk_size=1024+(1024 * 512 * sizemismatched)):
                        sizecopied += len(chunk)
                        if self.prt.end:
                            break
                        if chunk: # filter out keep-alive new chunks
                            tmpfile.write(chunk)
                            if self.prt.progress and progress < time.time():
                                progress = time.time() + 60
                                speed = utils.get_speed(sizecopied, (time.time()-st))
                                log.info("Downloaded %s of %s at %s", utils.convert_size(sizecopied), sz, speed)
                            if sizemismatched:
                                tmpfile.flush()
                                os.fsync(tmpfile.fileno())
                if sizecopied != szb and not self.prt.end:
                    raise SizeMismatchError("Download size mismatch downloaded %s expected %s" % (utils.convert_size(sizecopied), sz))
                elif self.prt.end:
                    self.cleanUpAfterError("Recieved signaled stop during download", fulltmp)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException):
                log.warn("Network error. Will retry %s more times", retriesleft)
                retriesleft -= 1
                if retriesleft > 0:
                    time.sleep(10)
                else:
                    log.error("Error downloading %s", nm)
                    self.cleanUpAfterError("Maximum retries reached", fulltmp)
            except SizeMismatchError:
                log.debug("File size mismatch Will retry %s more times", retriesleft)
                retriesleft -= 1
                sizemismatched = True
                if retriesleft > 0:
                    time.sleep(10)
                else:
                    log.error("Error downloading %s", nm)
                    self.cleanUpAfterError("Maximum retries reached", fulltmp)
            except OSError as e:
                log.error("Error writing to file %s\n%s", nm, e)
                self.cleanUpAfterError(traceback.format_exc(), fulltmp)
            except (requests.exceptions.RequestException, Exception):
                log.error("Error downloading %s", nm)
                self.cleanUpAfterError(traceback.format_exc(), fulltmp)
            except SystemExit:
                raise
            else:
                retriesleft = 0

        if not self.prt.end:
            self.prt.bytestotal += szb
            if self.prt.progress:
                speed = utils.get_speed(szb, (time.time()-st))
                log.info("%s downloaded at %s", sz, speed)
            st = time.time()
            if self.prt.tmp:
                log.info("Copying from temp to dest")
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
                        self.cleanUpAfterError("Recieved signaled stop during copy", destpath)
                except OSError as e:
                    self.cleanUpAfterError("Could not copy %s to destination\n%s" % (nm, e), destpath)
                except SystemExit:
                    raise
                else:
                    if self.prt.progress:
                        speed = utils.get_speed(szb, (time.time()-st))
                        log.info("%s copied at %s", sz, speed)
                    try:
                        os.remove(tmppath)
                    except OSError as e:
                        log.warn("Failed cleaning up tmp file %s\n%s", tmppath, e)
            self.prt.writeSuccess(tthdnum, destpath)
            log.info("Finished download %s", destpath)
            self.prt.numthreads -= 1
        else:
            log.warn("Parent signaled stop")


    def cleanUpAfterError(self, e, path):
        pt = self.pt
        tmppath = self.tmppath
        destpath = self.destpath
        tthdnum = self.tthdnum

        #log file to errorfiles.txt
        self.prt.writeError(tthdnum, self.nm, path, self.pt, e)

        #cleanup destination file
        try:
            if os.path.exists(destpath):
                os.remove(destpath)
        except OSError as ose:
            log.warn("Couldn't clean up file %s\n%s", destpath, ose)

        #cleanup temp file
        try:
            if self.prt.tmp and os.path.exists(tmppath):
                os.remove(tmppath)
        except OSError as ose:
            log.warn("Couldn't clean up file %s\n%s", destpath, ose)

        self.prt.numthreads -= 1
        thread.exit()