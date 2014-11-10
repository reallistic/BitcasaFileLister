BitcasaFileLister
=================
Version 0.6.0

List and download files in your Bitcasa drive

The BitcasaFileLister is a a python server that will allow you to login via OAuth, store your access token, get a listing of all the files in your Bitcasa drive with their base64 encoded path, and download individual files via the Bitcasa API.
To run it, use the following command:
```
python BitcasaFileLister
```


This will run the server on port 1115 and launch a browser at the following url:
```
http://localhost:1115/bitcasafilelister/
```

To run the server without launching a browser simply add the `-n` or `--nolaunch` param
```
python BitcasaFileLister -n
```

**Note:** As of version 0.6.0, the Bitcasa oauth command will launch the BitcasaFileFetcher server


You can access the legacy hosted php version of this at [Rose-llc.com](https://rose-llc.com/bitcasafilelist/)

The BitcasaFileLister is used to generate a Bitcasa access token and to retrieve the base64 encoded paths for use with the BitcasaFileFetcher below.

#BitcasaFileFetcher

The FileFetcher is a command line python application that will recursively fetch files from bitcasa via the API and save them to a designated path or uploaded them to a specified service. This application is multithreaded to allow multiple downloads at the same time.
The FileFetcher is automatically configured with your access token with the FileLister.
It must be invoked manually using the starting location (bitcasa base64 encoded path), target, and (optional) temp location.

This script is particularly useful for:
* Migrating from bitcasa to another provider
* Downloading large files and directories locally
* Downloading/copying large amounts of files from Bitcasa
* Uploading move/copy from bitcasa to GoogleDrive

**NOTE:** Please see [Using the gdrive branch (not yet updated for version 0.6.0)](https://github.com/rxsegrxup/BitcasaFileLister/wiki/Using-the-gdrive-branch)


**NOTE:** This script works best with python 2.7.x and fails with others.

It is **recommended** that you run the FileFetcher and FileLister using your own client id and secret by following these directions:
[Adding custom api keys to the utils.py](https://github.com/rxsegrxup/BitcasaFileLister/wiki/Adding-custom-api-keys)

#Install

Check the [wiki](https://github.com/rxsegrxup/BitcasaFileLister/wiki/) for more guides and instructions.

To install on windows (**not yet updated for version 0.6.0**) [click here](https://github.com/rxsegrxup/BitcasaFileLister/wiki/Windows-install-instructions)

General instructions below

```
pip install httplib2 uritemplate
git clone https://github.com/rxsegrxup/BitcasaFileLister.git
cd BitcasaFileLister
```

Before first run please read the help screens

```
python BitcasaFileFetcher -h
python BitcasaFileFetcher download -h
python BitcasaFileFetcher upload -h
python BitcasaFileFetcher oauth -h
python BitcasaFileFetcher testauth -h
```

Launch the FileLister for bitcasa oauth and base64 paths

```
python BitcasaFileLister
```

If you plan to upload to Google Drive you need to oauth manually using the following command

```
python BitcasaFileFetcher oauth --provider gdrive
```

Download your first files

```
python BitcasaFileFetcher download <base64 src directory> <destination directory>
```

# Usage

```
usage: BitcasaFileFetcher [-h] {oauth,testauth,download,upload} ...

Download files from bitcasa recursively

positional arguments:
  {oauth,testauth,download,upload}
    oauth               Program to retrieve the oauth url for a provider
    testauth            Program to test provider authentication
    download            Program to download files from bitcasa to
                        local/network storage
    upload              Program to download files from bitcasa and upload to
                        remote storage

optional arguments:
  -h, --help            show this help message and exit


usage: BitcasaFileFetcher download [-h] [-l LOG] [-m THREADS]
                                   [--norecursion | --depth DEPTH]
                                   [--silentqueuer] [-s] [--noconsole] [-v]
                                   [-p] [--version] [-t TEMP]
                                   src dst

positional arguments:
  src                   The Bitcasa base64 path for file source
  dst                   The final destination root dir or your files

optional arguments:
  -h, --help            show this help message and exit
  -l LOG, --log LOG     Full path to log file
  -m THREADS, --threads THREADS
                        Number of simultaneous downloads. (5)
  --norecursion         Do not go below the src folder. (Same as --depth 0)
  --depth DEPTH         The depth of folder traversal
  --silentqueuer        Silence queuer output
  -s, --single          download a single file
  --noconsole           do not log to console
  -v, --verbose         increase output verbosity
  -p, --progress        Log file download progress every 60 secs
  --version             Displays version and exits
  -t TEMP, --temp TEMP  The dir for temp files. (A local folder)

usage: BitcasaFileFetcher upload [-h] [-l LOG] [-m THREADS]
                                 [--norecursion | --depth DEPTH]
                                 [--silentqueuer] [-s] [--noconsole] [-v] [-p]
                                 [--version] -t TEMP [--provider {gdrive}]
                                 src dst

positional arguments:
  src                   The Bitcasa base64 path for file source
  dst                   The final destination root dir or your files

optional arguments:
  -h, --help            show this help message and exit
  -l LOG, --log LOG     Full path to log file
  -m THREADS, --threads THREADS
                        Number of simultaneous downloads. (5)
  --norecursion         Do not go below the src folder. (Same as --depth 0)
  --depth DEPTH         The depth of folder traversal
  --silentqueuer        Silence queuer output
  -s, --single          download a single file
  --noconsole           do not log to console
  -v, --verbose         increase output verbosity
  -p, --progress        Log file download progress every 60 secs
  --version             Displays version and exits
  -t TEMP, --temp TEMP  The dir for temp files. (A local folder)
  --provider {gdrive}   The remote storage provider in question (default is
                        gdrive)
```

## Download Run examples:

```
python BitcasaFileFetcher download /B-W80yjUQfC6umkOCahHMQ /mnt/networkdrive/c/documents/
```
* Simple execution
* All logging will be sent to /mnt/networkdrive/c/documents/bitcasafilefetcher.log (this is the default)
* Files will be downloaded directly to destination


```
python BitcasaFileFetcher download /B-W80yjUQfC6umkOCahHMQ /mnt/networkdrive/c/documents/ -t /mnt/tmp/documents/ -m 3 >bitcasafilefetcher.log 2>&1 &
```
* Run in background
* Direct stdout and stderr to bitcasafilefetcher.log
* All logging will be sent to /mnt/tmp/documents/bitcasafilefetcher.log (this is the default)


```
python BitcasaFileFetcher download /B-W80yjUQfC6umkOCahHMQ /mnt/networkdrive/c/documents/ -t /mnt/tmp/documents/ -l /var/log/bitcasafilelist/bitcasafilefetcher.log --noconsole > /var/log/bitcasafilelist/bitcasafilefetcher.log 2>&1 &
```
* Run in background
* No console logging
* Direct stdout and stderr to /var/log/bitcasafilelist/bitcasafilefetcher.log
* All logging will be sent to /var/log/bitcasafilelist/bitcasafilefetcher.log

## Upload Run examples:

```
python BitcasaFileFetcher upload /B-W80yjUQfC6umkOCahHMQ root -t /mnt/tmp/documents/
python BitcasaFileFetcher upload /B-W80yjUQfC6umkOCahHMQ root -t /mnt/tmp/documents/ --provider gdrive
```
* Simple execution
* All logging will be sent to /mnt/tmp/documents/bitcasafilefetcher.log (this is the default)
* Files will be downloaded to temp and then uploaded to the google drive root


```
python BitcasaFileFetcher upload /B-W80yjUQfC6umkOCahHMQ 0B9LKTRBFbYN1d0VwQWJFYXBoS0k -t /mnt/tmp/documents/
```
* Simple execution
* All logging will be sent to /mnt/tmp/documents/bitcasafilefetcher.log (this is the default)
* Files will be downloaded to temp and then uploaded to the google drive folder with specified id. (Note this folder could be at any depth)


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


* Upload directly to cloud providers (~~google drive~~, opendrive, copy)
* ~~Resume partial downloads~~
* ~~Copying single file instead of entire directories~~
* Copying lists of files instead of entire directories
* Python Web Application instead of command line
* ~~Retry failed downloads~~
