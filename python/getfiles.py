from bitcasa import BitcasaClient, BitcasaFolder, BitcasaFile
import threading, time, os, errno, sys, shutil


def convertSize(size):
   size_name = ("B","KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size,1024)))
   p = math.pow(1024,i)
   s = round(size/p,2)
   if (s > 0):
       return '%s %s' % (s,size_name[i])
   else:
       return '0B'

def getSpeed(size, tm):
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
            fulldest=self.fulldest
            item=self.item
            tthdnum=self.tthdnum
            fulltmp=self.fulltmp
            nm=item.name
            pt=item.path
            sz=convertSize(item.size)
            szb=item.size
            st=time.time()
            logger("Thread [%s]: %s size %s\n" % (tthdnum,item.name, sz))
            try:
                if not os.path.isdir(fulltmp):
                    os.makedirs(fulltmp)
            except OSError as exc:
                pass
            try:
                if not os.path.isdir(fulldest):
                    os.makedirs(fulldest)
            except OSError as exc:
                pass
            try:
                src = item.read()
                destpath = str("%s%s" % (fulldest,item.name))
                tmppath = str("%s%s" % (fulltmp,item.name))
                myFile = file(tmppath, 'w+')

                for byts in src:
                    if not self.prt.end:
                        myFile.write(byts)
                        self.prt.bytestotal+=len(byts)
                    else:
                        logger("Thread [%s]: Got exit signal. Quiting\n" % tthdnum)
                        break
                myFile.close()
                if not self.prt.end:
                    self.prt.bytestotal+=szb
                    logger("Thread [%s]: %s downloaded at %s\n" % (tthdnum, sz, getSpeed(szb,(time.time()-st))))
                    logger("Thread [%s]: %s copying from temp to dest\n" % (tthdnum,item.name))
                    st=time.time()
                    shutil.copy2(tmppath, destpath)
                    logger("Thread [%s]: %s copied at %s\n" % (tthdnum, sz, getSpeed(szb,time.time()-st)))
                    try:
                        os.remove(tmppath)
                    except OSError, e:
                        pass
                    myFile = file("%ssuccessfiles.txt" % self.prt.tmp, 'a')
                    myFile.write("%s\r\n" % destpath)
                    myFile.close()

                    logger("Thread [%s]: Finished download %s%s\n\n" % (tthdnum,fulldest,item.name))
            except Exception, e:
                try:
                    myFile = file("%serrorfiles.txt" % self.prt.tmp, 'a')
                    myFile.write("%s%s %s\r\n" % (fulldest,nm,pt))
                    myFile.close()
                except IOError, ioe:
                    logger("Error writing to error log. Quiting\n")
                    self.prt.end=True
                    return

                try:
                    os.remove(destpath)
                except OSError, e:
                    pass
                logger("Thread [%s]: Download failed %s%s\n\n" % (tthdnum,fulldest,item.name))

            self.prt.numthreads-=1

    def folderRecurse(self, fold, path, tthdnum):

        logger("Thread [%s]: %s\n" % (tthdnum,path))

        if path.startswith('/') and self.dest.endswith('/'):
            fulldest="%s%s" %(self.dest[:-1], path)
        elif not path.startswith('/') and not self.dest.endswith('/'):
            fulldest="%s/%s" %(self.dest, path)
        else:
            fulldest="%s%s" %(self.dest, path)
        if not fulldest.endswith("/"):
            fulldest+="/"

        if path.startswith('/') and self.tmp.endswith('/'):
            fulltmp="%s%s" %(self.tmp[:-1], path)
        elif not path.startswith('/') and not self.tmp.endswith('/'):
            fulltmp="%s/%s" %(self.tmp, path)
        else:
            fulltmp="%s%s" %(self.tmp, path)
        if not fulltmp.endswith("/"):
            fulltmp+="/"

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
                    tfd = str("%s%s" % (fulldest,item.name))
                    fexists = os.path.isfile(tfd) and os.path.getsize(tfd) >= item.size
                    cnti+=1
                    #logger("Thread [%s]: %s of %s %s%s\n" % (tthdnum,cnti,total,fulldest,nm))
                    if isinstance(item, BitcasaFile) and not fexists:
                        if self.numthreads >= self.maxthreads:
                            while self.numthreads > self.maxthreads and not self.end:
                                #logger("Waiting for download slot\n")
                                time.sleep(5)
                            if not self.end:
                                self.numthreads+=1
                                thread = self.RunThreaded(item, self.numthreads, fulldest, self, fulltmp)
                                thread.start()
                                self.threads.append(thread)
                            else:
                                logger("Got exit signal while sleeping\n")
                        elif not self.end:
                            self.numthreads+=1
                            thread = self.RunThreaded(item, self.numthreads, fulldest, self, fulltmp)
                            thread.start()
                            self.threads.append(thread)
                        else:
                            logger("Got exit signal. Stopping loop\n")
                            break
                    elif isinstance(item, BitcasaFolder):
                        self.folderRecurse(item, "%s/%s" % (path,nm), tthdnum)
                    elif fexists:
                        logger("Thread [%s]: %s already exists. Skipping\n" % (tthdnum,nm))
                        myFile = file("%sskippedfiles.txt" % self.tmp, 'a')
                        myFile.write("%s%s %s\r\n" % (fulldest,nm,pt))
                        myFile.close()

                except Exception, e:
                    myFile = file("%serrorfiles.txt" % self.tmp, 'a')
                    myFile.write("%s%s %s\r\n" % (fulldest,nm,pt))
                    myFile.close()

            logger("finished %s %s at %s\n" % (path, convertSize(self.bytestotal),getSpeed(self.bytestotal,time.time()-self.st)))
            for thread in self.threads:
                thread.join()

    def __init__(self):
        #destination directory
        self.dest=""
        #temp directory
        self.tmp=""
        #bittcasa base64 encdoded path
        self.baseFolder=""
        #Access token
        self.at=""
        self.maxthreads=5
        self.numthreads=0
        self.end=False
        self.cnt=0
        self.threads = []
        self.st=time.time()
        self.bytestotal=0

        #Not used
        self.maxsleepcycles = 3

    def process(self):
        bc = BitcasaClient("758ab3de", "5669c999ac340185a7c80c28d12a4319", "https://rosekings.com/bitcasafilelist/", self.at)
        logger("Getting base folder\n")
        base = bc.get_folder(self.baseFolder)

        logger("Starting recursion\n")
        self.folderRecurse(base, "", 0)

        myFile = file("%ssuccessfiles.txt" % self.tmp, 'w+')
        myFile.write("")
        myFile.close()
        myFile = file("%serrorfiles.txt" % self.tmp, 'w+')
        myFile.write("")
        myFile.close()
        myFile = file("%sskippedfiles.txt" % self.tmp, 'w+')
        myFile.write("")
        myFile.close()

def logger(msg):
    myfile = file("runlog.txt", "a")
    myfile.write(msg)
    myfile.close()

logger("Initializing Bitcasa\n")
b = BitcasaDownload()
b.process()
logger("done\n")
