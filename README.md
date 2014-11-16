BitcasaFileLister
=================
Version 0.7

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

**Note:** As of version 0.6, the Bitcasa oauth command will launch the BitcasaFileLister server, open your browser to the necessary Bitcasa Login screen and, upon successful log in, store your token to the bitcasa.ini file for you.


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
* Uploading files from bitcasa to GoogleDrive
* Uploading local files to GoogleDrive

**NOTE:** Please see [Using the gdrive branch (not yet updated for version 0.6)](https://github.com/rxsegrxup/BitcasaFileLister/wiki/Using-the-gdrive-branch)


**NOTE:** This script works best with python 2.7.x and fails with others.

It is **recommended** that you run the FileFetcher and FileLister using your own client id and secret by following these directions:
[Adding custom api keys to the utils.py](https://github.com/rxsegrxup/BitcasaFileLister/wiki/Adding-custom-api-keys)

# A note on stalling
Presently it seems the requests module does not respect the timeout for streamed downloads using iter_content. because of this, the application will sometimes stall. From what I have seen, if it is stalled (and be sure it is in fact stalled for at least 10 mins), you can safely issue a **SINGLE** CTRL+C or Esc. In my experience this will unstall whatever is holding things up, and continue as usual.

# Install
 **NOTE: The wikis contains some valid info but none of them have the updated command syntax. For that please read on below.**
 **NOTE: It should no longer be necessary to install dependencies. If you run into any dependency issues please post an [issue](https://github.com/rxsegrxup/BitcasaFileLister/issues)**

Check the [wiki](https://github.com/rxsegrxup/BitcasaFileLister/wiki/) for more guides and instructions.

(**not yet updated for version 0.6**) To install on windows [click here](https://github.com/rxsegrxup/BitcasaFileLister/wiki/Windows-install-instructions)

General instructions below

```
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

Launch the FileLister for bitcasa oauth and base64 paths which will open your browser to the necessary Bitcasa Login screen and, upon succesful log in, store your token to the bitcasa.ini file for you.

```
python BitcasaFileLister
```

If you plan to upload to Google Drive you need to oauth manually using the following command which will open your browser to the necessary Google Login screen and, upon succesful log in, present a token that must be copied and entered in the console.

```
python BitcasaFileFetcher oauth --provider gdrive
```

Download your first files

```
python BitcasaFileFetcher download <base64 src directory> <destination directory>
```

# Usage

### General
```
usage: python BitcasaFileFetcher [-h] {oauth,testauth,download,upload} ...

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

```

### Download

```
usage: python BitcasaFileFetcher download [-h] [-l LOG] [-m THREADS]
                                   [-f FOLDERTHREADS]
                                   [--norecursion | --depth DEPTH]
                                   [--silentqueuer] [-s] [--noconsole]
                                   [--nofilelog] [-v] [-p] [--dryrun]
                                   [--version] [-t TEMP]
                                   src dst

positional arguments:
  src                   The Bitcasa base64 path for file source
  dst                   The final destination root dir or your files

optional arguments:
  -h, --help            show this help message and exit
  -l LOG, --log LOG     Full path to log file
  -m THREADS, --threads THREADS
                        Number of simultaneous downloads. (5)
  -f FOLDERTHREADS, --folderthreads FOLDERTHREADS
                        Number of simultaneous folder lookups. (5)
  --norecursion         Do not go below the src folder. (Same as --depth 0)
  --depth DEPTH         The depth of folder traversal
  --silentqueuer        Silence queuer output
  -s, --single          download a single file
  --noconsole           do not log to console
  --nofilelog           do not log to success, error, or skipped files
  -v, --verbose         increase output verbosity
  -p, --progress        Log download progress every 60 secs
  --dryrun              Runs through the program logging all skipped and
                        downloaded files without actually downloading anything
  --version             Displays version and exits
  -t TEMP, --temp TEMP  The dir for temp files. (A local folder)

```

### Upload

```
usage: python BitcasaFileFetcher upload [-h] [-l LOG] [-m THREADS] [-f FOLDERTHREADS]
                                 [--norecursion | --depth DEPTH]
                                 [--silentqueuer] [-s] [--noconsole]
                                 [--nofilelog] [-v] [-p] [--dryrun]
                                 [--version] [--provider {gdrive}] -t TEMP
                                 [--local]
                                 src dst

positional arguments:
  src                   The Bitcasa base64 path for file source
  dst                   The final destination root dir or your files

optional arguments:
  -h, --help            show this help message and exit
  -l LOG, --log LOG     Full path to log file
  -m THREADS, --threads THREADS
                        Number of simultaneous downloads. (5)
  -f FOLDERTHREADS, --folderthreads FOLDERTHREADS
                        Number of simultaneous folder lookups. (5)
  --norecursion         Do not go below the src folder. (Same as --depth 0)
  --depth DEPTH         The depth of folder traversal
  --silentqueuer        Silence queuer output
  -s, --single          download a single file
  --noconsole           do not log to console
  --nofilelog           do not log to success, error, or skipped files
  -v, --verbose         increase output verbosity
  -p, --progress        Log download progress every 60 secs
  --dryrun              Runs through the program logging all skipped and
                        downloaded files without actually downloading anything
  --version             Displays version and exits
  --provider {gdrive}   The remote storage provider in question (default is
                        gdrive)
  -t TEMP, --temp TEMP  The dir for temp files. (A local folder)
  --local               Upload local files

```

# Examples
### Download:

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

### Upload:

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


```
python BitcasaFileFetcher upload /cloud/data_bk 0B9LKTRBFbYN1d0VwQWJFYXBoS0k -t /mnt/tmp/documents/ --local
```
* Simple execution
* All logging will be sent to /mnt/tmp/documents/bitcasafilefetcher.log (this is the default)
* Local files in /cloud/data_bk will be uploaded to the google drive folder with specified id. (Note this folder could be at any depth)


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

# Future Plans


* Upload directly to cloud providers (~~google drive~~, opendrive, copy)
* ~~Resume partial downloads~~
* ~~Copying single file instead of entire directories~~
* ~~Uploading local files~~
* Copying lists of files instead of entire directories
* Python Web Application instead of command line
* ~~Retry failed downloads~~
