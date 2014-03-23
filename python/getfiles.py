from bitcasa import BitcasaClient, BitcasaFolder, BitcasaFile
import threading, time, os, errno, sys, shutil

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
            sz=float(item.size/1024/1024)
            print "Thread [%s]: %s size %smb\n" % (tthdnum,item.name, sz)
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
                    else:
                        print "Thread [%s]: Got exit signal. Quiting" % tthdnum
                        break
                myFile.close()
                if not self.prt.end:
                    print "Thread [%s]: %s copying from temp to dest" % (tthdnum,item.name)
                    shutil.copy2(tmppath, destpath)
                    try:
                        os.remove(tmppath)
                    except OSError, e:
                        pass
                    myFile = file("%ssuccessfiles.txt" % self.prt.tmp, 'a')
                    myFile.write("%s\r\n" % destpath)
                    myFile.close()

                    print "Thread [%s]: Finished download %s%s\n\n" % (tthdnum,fulldest,item.name)
            except Exception, e:
                try:
                    myFile = file("%serrorfiles.txt" % self.prt.tmp, 'a')
                    myFile.write("%s%s %s\r\n" % (fulldest,nm,pt))
                    myFile.close()
                except IOError, ioe:
                    print "Error writing to error log. Quiting"
                    self.prt.end=True
                    return

                try:
                    os.remove(destpath)
                except OSError, e:
                    pass
                print "Thread [%s]: Download failed %s%s\n\n" % (tthdnum,fulldest,item.name)

            self.prt.numthreads-=1

    def folderRecurse(self, fold, path, tthdnum):

        print "Thread [%s]: %s" % (tthdnum,path)

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
                    cnti+=1
                    print "Thread [%s]: %s of %s %s%s\n" % (tthdnum,cnti,total,fulldest,nm)
                    if isinstance(item, BitcasaFile):
                        if self.numthreads >= self.maxthreads:
                            while self.numthreads > self.maxthreads and not self.end:
                                #print "Waiting for download slot"
                                time.sleep(5)
                            if not self.end:
                                self.numthreads+=1
                                thread = self.RunThreaded(item, self.numthreads, fulldest, self, fulltmp)
                                thread.start()
                                self.threads.append(thread)
                            else:
                                print "Got exit signal while sleeping"
                        elif not self.end:
                            self.numthreads+=1
                            thread = self.RunThreaded(item, self.numthreads, fulldest, self, fulltmp)
                            thread.start()
                            self.threads.append(thread)
                        else:
                            print "Got exit signal. Stopping loop"
                            break
                    elif isinstance(item, BitcasaFolder):
                            self.folderRecurse(item, "%s/%s" % (path,nm), tthdnum)
                except Exception, e:
                    myFile = file("%serrorfiles.txt" % self.tmp, 'a')
                    myFile.write("%s%s %s\r\n" % (fulldest,nm,pt))
                    myFile.close()
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
        self.maxthreads=2
        self.numthreads=0
        self.end=False
        self.cnt=0
        self.threads = []

        #Not used
        self.maxsleepcycles = 3

    def process(self):
        bc = BitcasaClient("758ab3de", "5669c999ac340185a7c80c28d12a4319", "https://rosekings.com/bitcasafilelist/", self.at)
        print "Getting base folder"
        base = bc.get_folder(self.baseFolder)

        print "Starting recursion"
        self.folderRecurse(base, "", 0)

        myFile = file("%ssuccessfiles.txt" % self.tmp, 'w+')
        myFile.write("")
        myFile.close()
        myFile = file("%serrorfiles.txt" % self.tmp, 'w+')
        myFile.write("")
        myFile.close()

print "Initializing Bitcasa"
b = BitcasaDownload()
b.process()
print "done"
