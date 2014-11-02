BitcasaFileLister
=================
Version 0.5.4

List and download files in your Bitcasa drive 

The BitcasaFileLister is a a php application that will allow you to login via OAuth, retrieve your access token, get a listing of all the files in your Bitcasa drive with their base64 encoded path, and download individual files via the Bitcasa API.
To host this you must register and application at bitcasa and input the api secret and client id in the [config file](https://github.com/rxsegrxup/BitcasaFileLister/blob/master/bitcasa-sdk-php/config.php).
 and change them in [utils.py](https://github.com/rxsegrxup/BitcasaFileLister/blob/master/python/utils.py#L4-L5).

You can access a hosted version of this at [Rose-llc.com](https://rose-llc.com/bitcasafilelist/)

The BitcasaFileLister is mainly useful to retrieve the base64 encoded paths for use with the BitcasaFileFetcher below.

#BitcasaFileFetcher

The filefetcher is a very small command line python application that will recursively fetch files from bitcasa via the API and save them to a designated path. This application is multithreaded to allow multiple downloads at the same time.
The filefetcher must be manually configured to have your access token, starting location (bitcasa base64 encoded path), target, and temp location.

This script is particularly useful for:
* Migrating from bitcasa to another provider
* Downloading large files and directories locally
* Downloading/copying large amounts of files from Bitcasa


**NOTE:** This script works best with python 2.7. It is untested with 3 and fails with 2.6.

It is **recommended** that you run the FileFetcher using your own client id and secret by following these directions:
[Adding custom api keys to the utils.py](https://github.com/rxsegrxup/BitcasaFileLister/wiki/Adding-custom-api-keys)

#Install

Check the [wiki](https://github.com/rxsegrxup/BitcasaFileLister/wiki/) for more guides and instructions.

To install on windows [click here](https://github.com/rxsegrxup/BitcasaFileLister/wiki/Windows-install-instructions)

General instructions below

```
git clone https://github.com/rxsegrxup/BitcasaFileLister.git
cd BitcasaFileLister/python
```
This script requires the `requests` python module which can be installed via the following command:

```
pip install requests
```

Before first run
```
python getfiles.py --oauth
#Output will be an oauth url to retrieve the access token
```

Store access token

```
python getfiles.py --settoken <token from oauth>
```

Test authentication

```
python getfiles.py / / --testauth
```

Download your first files

```
python getfiles.py <base64 src directory> <destination directory>
```

#Usage
```
getfiles.py [-h] [--settoken TOKEN] [-t TEMP] [-l LOG] [--depth DEPTH]
                   [-m THREADS] [--norecursion] [--noconsole] [--oauth]
                   [--verbose] [--testauth] [-p] [--version]
                   src dst

positional arguments:
  src                   The Bitcasa base64 path for file source
  dst                   The final destination root dir or your files

optional arguments:
  -h, --help            show this help message and exit
  --settoken TOKEN      Set the access token from Bitcasa. You only need to do
                        this once.
  -t TEMP, --temp TEMP  The temp dir to store downloaded files. (Should be a
                        local folder)
  -l LOG, --log LOG     Full path to log file
  --depth DEPTH         Specify depth of folder traverse. 0 is same as
                        --norecursion
  -m THREADS, --threads THREADS
                        Specify the max number of threads to use for
                        downloading. Default is 5
  --norecursion         Do not go below the src folder. (Same as --depth=0)
  --noconsole           do not log to console
  --oauth               Get the url to authenticate and retrieve an access
                        token
  --verbose             increase output verbosity
  --testauth            test capability to connect to infinite drive
  -p, --progress        Log download progress every 60 secs
  --version             Displays version and exits
```
##Run examples:
```
python getfiles.py /B-W80yjUQfC6umkOCahHMQ /mnt/networkdrive/c/documents/
```
* Simple execution
* All logging will be sent to /mnt/networkdrive/c/documents/runlog.txt (this is the default)
* Files will be downloaded directly to destination
```
python getfiles.py /B-W80yjUQfC6umkOCahHMQ /mnt/networkdrive/c/documents/ -t /mnt/tmp/documents/ -m 3 >runlog.txt 2>&1 &
```
* Run in background
* Direct stdout and stderr to runlog.txt
* All logging will be sent to /mnt/tmp/documents/runlog.txt (this is the default)
```
python getfiles.py /B-W80yjUQfC6umkOCahHMQ /mnt/networkdrive/c/documents/ -t /mnt/tmp/documents/ -l /var/log/bitcasafilelist/runlog.txt --noconsole > /var/log/bitcasafilelist/runlog.txt 2>&1 &
```
* Run in background
* No console logging
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
* ~~Retry failed downloads~~
