from bitcasa import BitcasaClient, BitcasaFolder, BitcasaFile
import threading, time, os, errno

class BitcasaDownload:
    class RunThreaded(threading.Thread):
        def __init__(self, item, tthdnum, fulldest, prt):
            threading.Thread.__init__(self)
            self.item = item
            self.tthdnum = tthdnum
            self.fulldest=fulldest
            self.prt = prt

        def run(self):
            fulldest=self.fulldest
            item=self.item
            tthdnum=self.tthdnum
            nm=item.name
            pt=item.path

            print "Thread [%s]: %s size %smb" % (tthdnum,item.name, item.size/1024/1024)
            

            try:
                os.makedirs(fulldest)
            except OSError as exc: # Python >2.5
                if exc.errno == errno.EEXIST and os.path.isdir(fulldest):
                    pass
                else: raise
            try:
                src = item.read()
                destpath = str("%s%s" % (fulldest,item.name))
                myFile = file(destpath, 'w+')
                #tbyts =0
                
                for byts in src:
                    #tbyts+=len(byts)
                    myFile.write(byts)
                    #print "Thread [%s]: wrote %s of %s" % (tthdnum,tbyts, item.size)
                myFile.close()
                myFile = file("%ssuccessfiles.txt" % self.prt.dest, 'a')
                myFile.write("%s\r\n" % destpath)
                myFile.close()
            except Exception, e:
                myFile = file("%serrorfiles.txt" % self.dest, 'a')
                myFile.write("%s%s %s\r\n" % (fulldest,nm,pt))
                myFile.close()

            print "Thread [%s]: Finished download %s%s\n\n" % (tthdnum,fulldest,item.name)
            self.prt.numthreads-=1

    def folderRecurse(self, fold, path, tthdnum):
        self.cnt+=1

        if self.end:
            return
        print "Thread [%s]: %s" % (tthdnum,path)
        #print "Thread [%s]: %s\n" % (tthdnum,fold.path)

        if path.startswith('/') and self.dest.endswith('/'):
            fulldest="%s%s" %(self.dest[:-1], path)
        elif not path.startswith('/') and not self.dest.endswith('/'):
            fulldest="%s/%s" %(self.dest, path)
        else:
            fulldest="%s%s" %(self.dest, path)
        if not fulldest.endswith("/"):
            fulldest+="/"

        if isinstance(fold, BitcasaFolder):
            total = len(fold.items)
            cnti=0
            for item in fold.items:
                try:
                    nm = item.name
                    pt = item.path
                    cnti+=1
                    print "Thread [%s]: %s of %s %s%s\n" % (tthdnum,cnti,total,fulldest,nm)
                    if isinstance(item, BitcasaFile):
                        if self.numthreads < self.maxthreads:
                            self.numthreads+=1
                            thread = self.RunThreaded(item, self.numthreads, fulldest, self)
                            thread.start()
                            self.threads.append(thread)
                        else:
                            while self.numthreads > self.maxthreads:
                                print "Waiting for download slot"
                                time.sleep(5)
                            self.numthreads+=1
                            thread = self.RunThreaded(item, self.numthreads, fulldest, self)
                            thread.start()
                            self.threads.append(thread)
                    elif isinstance(item, BitcasaFolder):
                            self.folderRecurse(item, "%s/%s" % (path,nm), tthdnum)
                except Exception, e:
                    myFile = file("%serrorfiles.txt" % self.dest, 'a')
                    myFile.write("%s%s %s\r\n" % (fulldest,nm,pt))
                    myFile.close()

    def __init__(self):
        self.dest="Y:/dump/files/VMs/"
        self.baseFolder="/yeYYEY5_Q_2ZtTP2gvfh2w/il17TysbQJm_kP7sG2P2GQ/QIzeWphNSi-TGUFYhmgA1g/"
        #/dump/files/Plex
        self.at=""
        self.maxthreads=5
        self.numthreads=0
        self.end=False
        self.cnt=0
        self.threads = []
        self.maxsleepcycles = 3

    def process(self):
        bc = BitcasaClient("758ab3de", "5669c999ac340185a7c80c28d12a4319", "https://rosekings.com/bitcasafilelist/", self.at)
        print "Getting base folder"
        base = bc.get_folder(self.baseFolder)
       #for item in base.items:
       #     if isinstance(item, BitcasaFolder) and item.name == "dump":
       #         base = item
       #         break
       #         
        print "Starting recursion"
        self.folderRecurse(base, "", 0)

        myFile = file("%ssuccessfiles.txt" % self.dest, 'w+')
        myFile.write("")
        myFile.close()
        myFile = file("%serrorfiles.txt" % self.dest, 'w+')
        myFile.write("")
        myFile.close()

print "Initializing Bitcasa"
b = BitcasaDownload()
b.process()
print "done"