BitcasaFileLister
=================
##NOTE. This application is now stable for use

List and download files in your Bitcasa drive 

This repo consists of two parts:
Embeded is a a php application that will allow you to login via OAuth, retreive your access token, get a listing of all the files in your Bitcasa drive with their base64 encoded path, and download individual files via the Bitcasa API.
To host this you must register and application at bitcasa and input the api secret and client id in the [config file](https://github.com/rxsegrxup/BitcasaFileLister/blob/master/bitcasa-sdk-php/config.php) and change them in [getfiles.py](https://github.com/rxsegrxup/BitcasaFileLister/blob/master/python/getfiles.py#L193).

You can access a hosted version of this at [Rose-llc.com](https://rose-llc.com/bitcasafilelist/)

This becomes useful in the second part:

#BitcasaFileFetcher


The filefetcher is a very small command line python application that will recursively fetch files from bitcasa via the API and save them to a designated path. This application is multithreaded to allow multiple downloads at the same time.
The filefetcher must be manually configured to have your access token, starting location (bitcasa base64 encoded path), target, and temp location.

This script is particularly useful for:
* Migrating from bitcasa to another provider
* Downloading large files and directories locally
* Downloading/copying large amounts of files from Bitcasa


**NOTE:** This script works best with python 2.7. It is untested with 3 and fails with 2.6.

#Install
```
git clone https://github.com/rxsegrxup/BitcasaFileLister.git
cd BitcasaFileLister/python
```
This script requires the `requests` python module which can be installed via the following command:

```
pip install requests
```
Check the [wiki](https://github.com/rxsegrxup/BitcasaFileLister/wiki/) for install guides.

To install on windows [click here](https://github.com/rxsegrxup/BitcasaFileLister/wiki/Windows-install-instructions)

#Usage
```
getfiles.py [-h] [-t TEMP] [-l LOG] [--depth DEPTH] [-m THREADS]
                   [--local] [--norecursion] [--verbose]
                   src dst token

positional arguments:
  src                   The Bitcasa base64 path for file source
  dst                   The final destination root dir or your files
  token                 The access token from Bitcasa. To get one navigate to
                        https://rose-llc.com/bitcasafilelist

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
```
##Run examples:
```
python getfiles.py /B-W80yjUQfC6umkOCahHMQ /mnt/networkdrive/c/documents/ US1_c0ed54d8aejsgrbd9c --local
```
* Simple execution
* All logging will be sent to /mnt/networkdrive/c/documents/runlog.txt by default
* Files will be downloaded directly to destination
```
python getfiles.py /B-W80yjUQfC6umkOCahHMQ /mnt/networkdrive/c/documents/ US1_c0ed54d8aejsgrbd9c -t /mnt/tmp/documents/ -m 3 >runlog.txt 2>&1 &
```
* Run in background
* Direct stdout and stderr to runlog.txt
* All logging will be sent to /mnt/tmp/documents/runlog.txt by default
```
python getfiles.py /B-W80yjUQfC6umkOCahHMQ /mnt/networkdrive/c/documents/ US1_c0ed54d8aejsgrbd9c -t /mnt/tmp/documents/ -l /var/log/bitcasafilelist/runlog.txt > /var/log/bitcasafilelist/runlog.txt 2>&1 &
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

supply the following src: ```/documents/``` NOTE: this will need to be the base64 encoded version<br>
use the following temp: ```/mnt/tmp/documents/```<br>
and the following dst: ```/mnt/networkdrives/c/documents/```<br>
<br>The result will be:

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

This script was developed in order to move files from bitcasa to network storage. Although it uses caching, it does not clog up the system with temp files.
As soon as a file is copied from temp to destination, it is deleted thus minimizing caching impact. If there is an error, the file is also deleted.

#Future Plans


* Upload directly to cloud providers (google drive, opendrive, copy)
* Copying lists of files instead of entire directories
* Python Web Application instead of command line
* Retry failed downloads
