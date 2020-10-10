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

Create a new Dropbox application and generate an access token. Paste this token to ``dropbox_token`` in the config file.

### Add a new service

Add the ``.service`` files to ``$HOME/.config/systemd/user``. Then do:
```
systemctl --user enable pybackup.service
systemctl --user start pybackup.service
```

## How to run

```python backup.py```
