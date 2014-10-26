from bitcasa import BitcasaClient, BitcasaFolder, BitcasaFile
import threading, time, os, errno, sys, shutil, math
import argparse, wget, urllib, uuid
import logger
BASE_URL = "https://developer.api.bitcasa.com/v1/files/"
log = None

def convertSize(size):
    if size <= 0:
        return '0B'
    size_name = ("B","KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size,1024)))
    p = math.pow(1024,i)
    s = round(size/p,2)
    if (s > 0):
        return '%s %s' % (s,size_name[i])
    else:
        return '0B'

def getSpeed(size, tm):
    if size <= 0 or tm <= 0:
        return "0B/s"
    speed = round(size/tm, 2)
    speed = convertSize(speed)
    return str(speed+"/s")

class BitcasaDownload:
    class RunThreaded(threading.Thread):
        def __init__(self, item, tthdnum, fulldest, prt, fulltmp):
            threading.Thread.__init__(self)
            self.item = item
            self.tthdnum = tthdnum
            self.fulldest=fulldest
            self.prt = prt
            self.fulltmp = fulltmp

        def run(self):
            global BASE_URL, log

            fulldest=self.fulldest
            item=self.item
            tthdnum=self.tthdnum
            fulltmp=self.fulltmp
            nm=item.name
            pt=item.path
            sz=convertSize(item.size)
            szb=item.size
            st=time.time()
            log.info("Thread [%s]: %s size %s" % (tthdnum,item.name, sz))
            params = {"access_token":self.prt.at, "path":pt}
            apidownloaduri = "%s%s?%s" % (BASE_URL,urllib.quote_plus(nm),urllib.urlencode(params))
            try:
                if not os.path.isdir(fulltmp):
                    os.makedirs(fulltmp)
            except:
                log.error("Thread [%s]: error creating dirs for file %s via wget" % (tthdnum, item.name))
                raise
            if not self.prt.local:
                try:
                    if not os.path.isdir(fulldest):
                        os.makedirs(fulldest)
                except:
                    log.error("Thread [%s]: error creating dirs for file %s via wget" % (tthdnum, item.name))
                    raise
                    
            try:
                destpath = os.path.join(fulldest,item.name)
                tmppath = os.path.join(fulltmp,item.name)
                log.debug("Thread [%s]: %s" % (tthdnum, apidownloaduri))
                log.debug("Thread [%s]: Downloading file to %s" % (tthdnum, tmppath))
                try:
                    wget.download(apidownloaduri,out=tmppath)
                except:
                    log.error("Thread [%s]: error downloading %s via wget" % (tthdnum, item.name))
                    raise

                log.debug("Thread [%s]: Download finished." % tthdnum)
                if not self.prt.end:
                    self.prt.bytestotal+=szb
                    log.debug("Thread [%s]: %s downloaded at %s" % (tthdnum, sz, getSpeed(szb,(time.time()-st))))
                    log.debug("Thread [%s]: %s copying from temp to dest" % (tthdnum,item.name))
                    st=time.time()
                    if not self.prt.local:
                        shutil.copy2(tmppath, destpath)
                        log.debug("Thread [%s]: %s copied at %s" % (tthdnum, sz, getSpeed(szb,time.time()-st)))
                        try:
                            os.remove(tmppath)
                        except OSError, e:
                            log.warn("Failed cleaning up tmp file %s" % tmppath)
                            pass
                    myFile = file("%ssuccessfiles.txt" % self.prt.tmp, 'a')
                    myFile.write("%s\n" % destpath)
                    myFile.close()

                    log.info("Thread [%s]: Finished download %s" % (tthdnum,destpath))
            except Exception, e:
                try:
                    myFile = file("%serrorfiles.txt" % self.prt.tmp, 'a')
                    myFile.write("%s%s %s\n" % (fulldest,nm,pt))
                    myFile.close()
                    if os.path.isfile(tmppath):
                        os.remove(tmppath)
                except IOError, ioe:
                    log.error("Error writing to error log. Quiting")
                    self.prt.end=True
                    return
                try:
                    os.remove(destpath)
                except OSError, e:
                    pass
                log.error("Thread [%s]: Download failed %s\n%s" % (tthdnum,tmppath, e.strerror))

            self.prt.numthreads-=1

    def folderRecurse(self, fold, path, tthdnum, depth):
        global log

        log.info("Thread [%s]: %s" % (tthdnum,path))
        fulldest = os.path.join(self.dest, path)
        fulltmp = os.path.join(self.tmp, path)
        log.debug("Dest path %s" % fulldest)
        log.debug("Tmp path %s" % fulltmp)
        if isinstance(fold, BitcasaFolder):
            total = len(fold.items)
            cnti=0
            for item in fold.items:
                if self.end:
                    return
                self.cnt+=1
                try:
                    nm = item.name
                    pt = item.path
                    tfd = os.path.join(fulldest, item.name)
                    fexists = os.path.isfile(tfd) and os.path.getsize(tfd) >= item.size
                    cnti+=1
                    if isinstance(item, BitcasaFile) and not fexists:
                        if self.numthreads >= self.maxthreads:
                            while self.numthreads > self.maxthreads and not self.end:
                                time.sleep(5)
                            if not self.end:
                                self.numthreads+=1
                                thread = self.RunThreaded(item, self.numthreads, fulldest, self, fulltmp)
                                thread.start()
                                self.threads.append(thread)
                            else:
                                log.debug("Got exit signal while sleeping")
                        elif not self.end:
                            self.numthreads+=1
                            thread = self.RunThreaded(item, self.numthreads, fulldest, self, fulltmp)
                            thread.start()
                            self.threads.append(thread)
                        else:
                            log.debug("Got exit signal. Stopping loop")
                            break
                    elif isinstance(item, BitcasaFolder):
                        if (self.depth == None or self.depth > depth) and self.rec:
                            self.folderRecurse(item, os.path.join(path, nm), tthdnum, (depth+1))
                    elif fexists:
                        log.info("Thread [%s]: %s already exists. Skipping" % (tthdnum,nm))
                        myFile = file("%sskippedfiles.txt" % self.tmp, 'a')
                        myFile.write("%s%s %s\r\n" % (fulldest,nm,pt))
                        myFile.close()

                except Exception as e:
                    log.error("Thread [%s]: Error processing file %s\n%s" % (tthdnum, nm, e.strerror))
                    with open(os.path.join(self.tmp, 'errorfiles.txt'), 'a') as myFile:
                        myFile.write("%s%s %s\r\n" % (fulldest, nm, pt))
            #Randomly log progress and speed statistics
            log.info("finished %s %s at %s\n" % (path, convertSize(self.bytestotal),getSpeed(self.bytestotal,time.time()-self.st)))
    def __init__(self, depth, tmp, src, dst, rec, local, at, mt):
        global log
        log.debug(" depth: %s\n tmp: %s\n src: %s\n dst: %s\n rec: %s\n local: %s\n at: %s\n mt: %s" % (depth, tmp, src, dst, rec, local, at, mt))
        #destination directory
        self.dest=dst
        #temp directory
        self.tmp=tmp
        #bittcasa base64 encdoded path
        self.baseFolder=src
        #Access token
        self.at=at
        self.maxthreads=mt
        if self.maxthreads == None or self.maxthreads == 0:
            log.info("Using default max threads value of 5")
            self.maxthreads=5
        self.local=local
        self.rec=rec
        self.depth=depth
        self.numthreads=0
        self.end=False
        self.cnt=0
        self.threads = []
        self.st=time.time()
        self.bytestotal=0

        #Not yet used
        self.maxsleepcycles = 3

    def process(self):
        global log
        bc = BitcasaClient("758ab3de", "5669c999ac340185a7c80c28d12a4319","https://rose-llc.com/bitcasafilelist/", self.at)
        log.debug("Getting base folder")
        base = bc.get_folder(self.baseFolder)

        #initialize logfiles
        try:
            if not os.path.isdir(self.tmp):
                os.makedirs(self.tmp)
        except OSError as exc:
            pass
        myFile = file("%ssuccessfiles.txt" % self.tmp, 'w+')
        myFile.write(time.strftime("%Y-%m-%d %H:%M:%S") + "")
        myFile.close()
        myFile = file("%serrorfiles.txt" % self.tmp, 'w+')
        myFile.write(time.strftime("%Y-%m-%d %H:%M:%S") + "")
        myFile.close()
        myFile = file("%sskippedfiles.txt" % self.tmp, 'w+')
        myFile.write(time.strftime("%Y-%m-%d %H:%M:%S") + "")
        myFile.close()

        log.debug("Starting recursion")
        self.folderRecurse(base, "", 0,0)
        #wait for threads to finish downoading
        for thread in self.threads:
            thread.join()
        #Log final speed and statistics
        log.info("finished %s at %s\n" % (convertSize(self.bytestotal),getSpeed(self.bytestotal,time.time()-self.st)))

"""def log.info(msg):
    myfile = file(_log, "a")
    myfile.write(msg)
    myfile.close()
"""

def main(argv):
    global log
    parser = argparse.ArgumentParser()
    parser.add_argument("src", help="The Bitcasa base64 path for file source")
    parser.add_argument("dst", help="The final destination root dir or your files")
    parser.add_argument("token", help="The access token from Bitcasa. To get one navigate to https://rose-llc.com/bitcasafilelist")
    parser.add_argument("-t","--temp", help="The temp dir to store downloaded files. (Should be a local folder)")
    parser.add_argument("-l","--log", help="Full path to log file")
    parser.add_argument("--depth", type=int, help="Specify depth of folder traverse. 0 is same as --norecursion")
    parser.add_argument("-m", "--threads", type=int, help="Specify the max number of threads to use for downloading. Default is 5")
    parser.add_argument("--local", help="Only store file locally. Do not use temp dir", action="store_true")
    parser.add_argument("--norecursion", help="Do not go below the src folder. (Same as --depth=0)", action="store_true")
    parser.add_argument("--verbose", help="increase output verbosity", action="store_true")
    args = parser.parse_args()


    _log = ""
    if (args.log == None or args.log == "") and not args.local:
        _log = args.temp+"runlog.txt"
    elif (args.log == None or args.log == "") and args.local:
        _log = args.dst+"runlog.txt"
    elif args.log != None and args.log != "":
        _log = args.log

    #initialize logger log
    log = logger.setup(logfile=_log, debug=args.verbose)

    rec= not args.norecursion
    if args.depth > 0 and args.norecursion:
        log.info("Note: Non 0 depth and --no-recursion parameter present. Assuming recusion")
        rec=True
    if (args.temp == "" and not args.local) or args.dst=="" or args.src=="" or args.token=="":
        sys.stderr.write("Please supply access token, temp, source, and destination locations. If this is a local copy, then specify -l or --local")
        sys.exit(2)
    elif args.temp != None and args.temp != "" and args.local:
        log.info("Local specified. Ignoring temp")
        args.temp = args.dst
    elif args.local:
        args.temp = args.dst
    log.debug("Initializing Bitcasa")
    b = BitcasaDownload(args.depth, args.temp, args.src, args.dst, rec, args.local, args.token, args.threads)
    b.process()
    log.info("done")


if __name__ == "__main__":
    main(sys.argv[1:])
