import threading, thread, time, os, shutil, traceback
from hashlib import sha1
import urllib, requests
from logger import logger as log
import utils

BASE_URL = "https://developer.api.bitcasa.com/v1/files/"

class SizeMismatchError(Exception):
    pass

class RunThreaded(threading.Thread):
    def __init__(self, item, thread_num, parent):
        threading.Thread.__init__(self, name=(thread_num+1))
        self.nm = item["filename"]
        self.base64path = item["filepath"]
        self.size_bytes = item["filesize"]
        self.size_str = utils.convert_size(self.size_bytes)
        self.thread_num = thread_num
        self.fulldest = item["filedir"]

        self.prt = parent
        self.destpath = item["fullpath"]
        self.tmppath = ""

    def run(self):
        sizecopied = 0
        if self.prt.tmp:
            fulltmp = self.prt.tmp
        else:
            fulltmp = self.fulldest

        params = {"access_token":self.prt.accesstoken, "path":self.base64path}
        
        log.info("%s size %s", self.nm, self.size_str)

        try:
            apidownloaduri = "%s%s?%s" % (BASE_URL, urllib.quote_plus(self.nm), urllib.urlencode(params))
        except KeyError:
            self.cleanUpAfterError("Error unsupported characters in filename %s" % self.nm, self.destpath)
        except: 
        #This technically should never happen but technically you never know
            self.cleanUpAfterError(traceback.format_exc(), self.destpath)

        if not os.path.exists(self.fulldest) or (self.prt.tmp and not os.path.exists(fulltmp)):
            self.cleanUpAfterError("Missing temp or destination parent directory", self.destpath)
        
        self.tmppath = os.path.join(fulltmp, self.nm)

        if self.prt.tmp:
            filehash = sha1("blob " + str(self.size_bytes) + "\0" + self.tmppath)
            tmpname = filehash.hexdigest()
            self.tmppath = os.path.join(self.prt.tmp, tmpname)

        log.debug("Downloading file to %s", self.tmppath)
        retriesleft = 3
        sizemismatched = False
        failsize = False
        while retriesleft > 0:
            sizecopied = 0
            progress = time.time() + 60
            apiratecount = 0
            try:
                with open(self.tmppath, 'wb') as tmpfile:
                    st = time.time()
                    timespan = 0
                    req = requests.get(apidownloaduri, stream=True, timeout=120)
                    chunk_size  = 1024
                    #if not sizemismatched:
                    chunk_size += 1024 * 1024
                    for chunk in req.iter_content(chunk_size=chunk_size):
                        sizecopied += len(chunk)
                        if self.prt.end:
                            break
                        if chunk: # filter out keep-alive new chunks
                            tmpfile.write(chunk)
                            if self.prt.progress and progress < time.time():
                                progress = time.time() + 60
                                speed = utils.get_speed(sizecopied, (time.time()-st))
                                log.info("%s\nDownloaded %s of %s at %s", self.nm, utils.convert_size(sizecopied), self.size_str, speed)
                            #if sizemismatched:
                            #    tmpfile.flush()
                            #    os.fsync(tmpfile.fileno())
                    timespan = (time.time()-st)
                if sizecopied != self.size_bytes and not self.prt.end:
                    raise SizeMismatchError("Download size mismatch downloaded %s expected %s" % (sizecopied, self.size_bytes))
                elif self.prt.end:
                    self.cleanUpAfterError("Recieved signaled stop during download", self.destpath)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException):
                retriesleft -= 1
                if req.status_code == 429:
                    apiratecount += 1
                    retriesleft += 1
                    log.warn("API rate limit reached. Will retry")
                else:
                    log.warn("Network error. Will retry %s more times", retriesleft)
                if retriesleft > 0:
                    time.sleep(10 * apiratecount)
                else:
                    log.error("Error downloading %s", self.nm)
                    self.cleanUpAfterError("Maximum retries reached", self.destpath)
            except SizeMismatchError:
                retriesleft -= 1
                log.exception("%s File size mismatch. Will retry %s more times", self.nm, retriesleft)
                sizemismatched = True
                if retriesleft == 2:
                    failsize = sizecopied
                elif failsize and failsize != sizecopied:
                    failsize = False

                if retriesleft > 0:
                    time.sleep(10)
                elif failsize:
                    log.warn("%s\nRecieved incorrect file size %s instead of %s 3 times. Saving anyway", self.nm, sizecopied, self.size_bytes)
                else:
                    log.error("Error downloading %s", self.nm)
                    self.cleanUpAfterError("Maximum retries reached", self.destpath)
            except (IOError, OSError, WindowsError):
                log.exception("Error writing to file %s", self.nm)
                self.cleanUpAfterError(traceback.format_exc(), self.destpath)
            except (requests.exceptions.RequestException, Exception):
                log.error("Error downloading %s", self.nm)
                self.cleanUpAfterError(traceback.format_exc(), self.destpath)
            except SystemExit:
                self.cleanUpAfterError("Received signal exit", self.destpath)
                raise
            except:
                if req.status_code in [429, 503]:
                    apiratecount += 1
                    retriesleft += 1
                    log.warn("API rate limit reached. Will retry")
                else:
                    log.exception("Error downloading %s. Will retry %s more times", self.nm, retriesleft)

                if retriesleft > 0:
                    time.sleep(10 * apiratecount)
                else:
                    self.cleanUpAfterError("An unknown error occured", self.destpath)
            else:
                retriesleft = 0
                self.prt.downloadtime += timespan
                if self.prt.progress:
                    speed = utils.get_speed(self.size_bytes, timespan)
                    log.info("%s downloaded at %s", self.size_str, speed)

        if self.prt.end:
            log.warn("Parent signaled stop")
            return
        self.prt.bytestotal += self.size_bytes
        if self.prt.tmp:
            log.info("Copying from temp to dest")
            retriesleft = 3
            while retriesleft > 0:
                try:
                    st = time.time()
                    timespan = 0
                    with open(self.tmppath, 'rb') as f, open(self.destpath, "wb") as fo:
                        while True and not self.prt.end:
                            piece = f.read(1024)
                            if piece:
                                fo.write(piece)
                            else:
                                break

                    timespan = (time.time()-st)
                    if self.prt.end:
                        self.cleanUpAfterError("Recieved signaled stop during copy", self.destpath)
                except (IOError, OSError, WindowsError) as e:
                    retriesleft -= 1
                    if retriesleft > 0:
                        self.delete_dest()
                        log.exception("Error copying file wil retry %s more times", retriesleft)
                    else:
                        log.exception("Error file could not be copied to %s", self.destpath)
                        self.cleanUpAfterError(traceback.format_exc(), self.destpath)
                except SystemExit:
                    self.cleanUpAfterError("Received signal exit", self.destpath)
                    raise
                except: 
                    #This technically should never happen but technically you never know
                    retriesleft -= 1
                    if retriesleft > 0:
                        self.delete_dest()
                        log.exception("Error copying file wil retry %s more times", retriesleft)
                    else:
                        log.exception("Error file could not be copied to %s", self.destpath)
                        self.cleanUpAfterError(traceback.format_exc(), self.destpath)
                else:
                    retriesleft = 0
                    self.prt.copytime += timespan
                    if self.prt.progress:
                        speed = utils.get_speed(self.size_bytes, timespan)
                        log.info("%s copied at %s", self.size_str, speed)
                    try:
                        os.remove(self.tmppath)
                    except (IOError, OSError) as e:
                        log.warn("Failed cleaning up tmp file %s\n%s", self.tmppath, e)
        self.prt.writeSuccess(self.destpath)
        log.info("Finished download %s in ", self.destpath)
        log.debug("End of thread")
        self.prt.threads[self.thread_num] = None

    def cleanUpAfterError(self, e, path):

        # log file to errorfiles.txt
        self.prt.writeError(self.nm, path, self.base64path, e)

        self.delete_dest

        #cleanup temp file
        try:
            if self.prt.tmp and os.path.exists(self.tmppath):
                os.remove(self.tmppath)
        except OSError as ose:
            log.exception("Couldn't clean up file %s", self.tmppath)
        log.debug("End of thread")
        self.prt.threads[self.thread_num] = None
        thread.exit()

    def delete_dest(self):
        #cleanup destination file
        try:
            if os.path.exists(self.destpath):
                os.remove(self.destpath)
        except:
            log.exception("Couldn't clean up file %s", self.destpath)