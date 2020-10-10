# pybackup

A rather simple backup application using rsync and Dropbox. Written in Python.

This application has been tested on Linux only. It may work on other OS too.

## What you'll need (Ubuntu)

* Python 3.
* Rsync.
* The ```dropbox``` package (>= 9.4.0): ```pip install dropbox```
* A Dropbox account and a Dropbox access token. See http://www.dropbox.com/developers
* The ```gpg``` application, GnuPG.

## How to configure

Set up the configuration in the .ini file.

### Dropbox authentication

* Create a new Dropbox application and generate an access token.
* Paste this token to ``dropbox_token`` in the config file.
* Create a folder in Dropbox, for example ``Backup``.
* Set ``dropbox_target`` to the folder name, remember the slash at the end. Example: ``/Backup/``

### Add a new service

Add the ``.service`` files to ``$HOME/.config/systemd/user``. Then do:
```
systemctl --user enable pybackup.service
systemctl --user enable pybackup.timer
systemctl --user start pybackup.timer
```

### Set up backup folders

* ``src_dirs`` is the path to the source folder.
* ``target_dir`` is the path where a local backup should be placed.
* ``log_dir`` is the path to the log folder.

## How to run

```python backup.py```
