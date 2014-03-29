BitcasaFileLister
=================

List files in your Bitcasa drive 

This repo consists of two parts:
Embeded is a a php application that will allow you to login via OAuth, retreive your access token, and get a listing of all the files in your Bitcasa drive.
The listing also provides capability to specify what depth you want the script to go.
You can access a hosted version of this at [Rosekings.com](https://rosekings.com/bitcasafilelist/)

This becomes useful in the second part:

#BitcasaFileFetcher


The filefetcher is a very small command line python application that will recursively fetch files from bitcasa via the API and save them to a designated path. This application is multithreaded to allow multiple downloads at the same time.
The filefetcher must be manually configured to have your access token, starting location (bitcasa base64 encoded path), target, and temp location.

This script is particularly useful for:
* Migrating from bitcasa to another provider
* Downloading large files and directories locally
* Downloading/copying large amounts of files from Bitcasa


**NOTE:** This script works best with python 2.7. It is untested with 3 and fails with 2.6.
#Usage
```
getfiles.py [-h] [-t TEMP] [-l LOG] [--depth DEPTH] [-m THREADS]
                   [--local] [--norecursion] [--verbose]
                   src dst token

positional arguments:
  src                   The Bitcasa base64 path for file source
  dst                   The final destination root dir or your files
  token                 The access token from Bitcasa. To get one navigate to
                        https://rosekings.com/bitcasafilelist

optional arguments:
  -h, --help            show this help message and exit
  -t TEMP, --temp TEMP  The temp dir to store downloaded files. (Should be a
                        local folder)
  -l LOG, --log LOG     Full path to log file
  --depth DEPTH         Specify depth of folder traverse. 0 is same as
                        --norecursion
  -m THREADS, --threads THREADS
                        Specify the max number of threads to use for
                        downloading. default is 5
  --local               Only store file locally. Do not use temp dir
  --norecursion         Do not go below the src folder. (Same as --depth=0)

##Run examples:
python2.7 getfiles.py /B-W80yjUQfC6umkOCahHMQ /mnt/networkdrive/c/documents/ -t /mnt/tmp/documents/ -m 3 >runlog.txt 2>&1 &
```
* Run in background
* Direct stdout and stderr to runlog.txt
* All logging will be sent to /mnt/tmp/documents/runlog.txt by default
```
python2.7 getfiles.py /B-W80yjUQfC6umkOCahHMQ /mnt/networkdrive/c/documents/ -t /mnt/tmp/documents/ -l /var/log/bitcasafilelist/runlog.txt > /var/log/bitcasafilelist/runlog.txt 2>&1 &
```
* Run in background
* Direct stdout and stderr to /var/log/bitcasafilelist/runlog.txt
* All logging will be sent to /var/log/bitcasafilelist/runlog.txt



For example, if you have the following in Bitcasa:

```
/documents/
/documents/myfile1.ext
/documents/otherfiles/
/documents/otherfiles/otherfile.ext
/rootfile.ext
```

supply the following src: ```/documents/``` NOTE: this will need to be the base64 encoded version
use the following temp: ```/mnt/tmp/documents/```
and the following dst: ```/mnt/networkdrives/c/documents/```
The result will be:

```
/mnt/tmp/documents/
/mnt/tmp/documents/successfiles.txt
/mnt/tmp/documents/errorfiles.txt
/mnt/tmp/documents/skippedfiles.txt
/mnt/tmp/documents/otherfiles/

/mnt/networkdrives/c/documents/
/mnt/networkdrives/c/documents/myfile1.ext
/mnt/networkdrives/c/documents/otherfiles/
/mnt/networkdrives/c/documents/otherfiles/otherfile.ext
```

This script was developed in order to move files from bitcasa to network storage. Although it uses caching, it does not clof up the system with temp files.
As soon as a file is copied from temp to destination, it is deleted thus minimizing caching impact.

##Usage
Please use [this](https://github.com/rxsegrxup/BitcasaFileLister/blob/59850a21aeab8ce702998efaa3520b9df1f0a77f/python/getfiles.py) commit of the file.

Change the following lines [here](https://github.com/rxsegrxup/BitcasaFileLister/blob/59850a21aeab8ce702998efaa3520b9df1f0a77f/python/getfiles.py#L174-L181)

```
  #destination directory
  self.dest=""
  #temp directory
  self.tmp=""
  #bitcasa base64 encdoded path found by using either:
  #   the hosted tool at: https://rosekings.com/bitcasafilelist/
  #   A self-hosted cloned copy of the BitcasaFileLister php tool
  self.baseFolder=""
  #Access token
  self.at=""
  
  # for some reason of which I have not bothered to figure out,
  # this is currently downloading with 1 more thread than what is specified here.
  # For example, with the set value 6 files will download at one time
  # This does NOT include the parent thread
  self.maxthreads=5
```

#Future Plans


* Direct upload to [OpenDrive](https://www.opendrive.com) via API
* Copying lists of files instead of entire directories
* Disable recursion
* Disable temp directory if just copying locally
* Python Web Application instead of command line
