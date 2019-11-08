# pybackup

A rather simple backup application using rsync and Dropbox. Written in Python.

This application has been tested on Linux only. It may work on other OS too.

## What you'll need (Ubuntu)

* Python 3.
* The ```dropbox``` package (>= 9.4.0): ```pip install dropbox```
* A Dropbox account and a Dropbox access token. See http://www.dropbox.com/developers
* The ```gpg``` application, GnuPG.

## How to configure

Set up the configuration in the .ini file.

## How to run

```python backup.py```
