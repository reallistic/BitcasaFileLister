BitcasaFileLister
=================

List files in your bitcasa drive 

The BitcasaFileLister consistsof two parts:
Embeded is a a php application that will allow you to login via OAuth, retreive your access token, and get a listing of all the files in your Bitcasa drive.
The listing also provides capability to specify what depth you want the script to go.

This becomes useful in the second part:

##BitcasaFileFetcher
===================

The filefetcher is a very small command line python application that will recursively fetch files from bitcasa via the API and save them to a designated path.
The filefetcher must be manually configured to have your access token, starting location (bitcasa base64 encoded path), target, and temp location.
For example, if you have the following in Bitcasa:

<code>
/documents/

/documents/myfile1.ext

/documents/otherfiles/

/documents/otherfiles/otherfile.ext

/rootfile.ext
</code>

supply the following start path: <code>/documents/</code>
use the following temp dir: <code>/mnt/tmp/documents/</code>
and the following destination: <code>/mnt/networkdrives/c/documents/</code>
The result will be:

<code>
/mnt/tmp/documents/

/mnt/tmp/documents/successfiles.txt

/mnt/tmp/documents/errorfiles.txt

/mnt/tmp/documents/skippedfiles.txt

/mnt/tmp/documents/otherfiles/

/mnt/networkdrives/c/documents/

/mnt/networkdrives/c/documents/myfile1.ext

/mnt/networkdrives/c/documents/otherfiles/

/mnt/networkdrives/c/documents/otherfiles/otherfile.ext
</code>

This script was developed in order to move files from bitcasa to network storage. Although it uses caching, it does not clof up the system with temp files.
As soon as a file is copied from temp to destination, it is deleted thus minimizing caching impact.
