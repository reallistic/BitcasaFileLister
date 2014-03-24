#BitcasaFileLister
=================

List files in your Bitcasa drive 

This repo consists of two parts:
Embeded is a a php application that will allow you to login via OAuth, retreive your access token, and get a listing of all the files in your Bitcasa drive.
The listing also provides capability to specify what depth you want the script to go.
You can access a hosted version of this at [Rosekings.com](https://rosekings.com/bitcasafilelist/)

This becomes useful in the second part:

#BitcasaFileFetcher
===================

The filefetcher is a very small command line python application that will recursively fetch files from bitcasa via the API and save them to a designated path. This application is multithreaded to allow multiple downloads at the same time.
The filefetcher must be manually configured to have your access token, starting location (bitcasa base64 encoded path), target, and temp location.

This script is particularly useful for:
* Migrating from bitcasa to another provider
* Downloading large files and directories locally
* Downloading/copying large amounts of files from Bitcasa

For example, if you have the following in Bitcasa:

```
/documents/
/documents/myfile1.ext
/documents/otherfiles/
/documents/otherfiles/otherfile.ext
/rootfile.ext
```

supply the following start path: ```/documents/```
use the following temp dir: ```/mnt/tmp/documents/```
and the following destination: ```/mnt/networkdrives/c/documents/```
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

#Future Plans
================

* Direct upload to [OpenDrive](https://www.opendrive.com) via API
* Copying lists of files instead of entire directories
* Disable recursion
* Disable temp directory if just copying locally
* Python Web Application instead of command line
