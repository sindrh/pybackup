#!/usr/bin/python3

import configparser
from pathlib import Path
import datetime
import subprocess
import dropbox_backup
import smtplib



class SendMail(object):
    def __init__(self, config):
        self._config = config

    def send(self, subject, body):
        msg = "From: {}\nTo: {}\nSubject: {}\n\n{}".format(self._config["mail"]["from"],
                                                           self._config["mail"]["to"],
                                                           subject, body)
        server = smtplib.SMTP_SSL(self._config["mail"]["server_out"], int(self._config["mail"]["port_out"]))
        server.login(self._config["mail"]["username"], self._config["mail"]["password"])
        server.sendmail(self._config["mail"]["from"], self._config["mail"]["to"], msg)
        server.quit()

class LockFile(object):
    def __init__(self, config):
        self._file = Path(config["general"]["lock_file"])

    @property
    def locked(self):
        return self._file.exists()

    def lock(self):
        self._file.write_text("locked")

    def unlock(self):
        self._file.unlink()


class BackupLog(object):
    def __init__(self, logdir):
        date_today = str(datetime.date.today())
        log_filename = "Backup_{}.txt".format(date_today)
        self._logfile_path = Path(logdir) / log_filename

    def write(self, line):
        timestamp = datetime.datetime.now()
        with open(self._logfile_path, "a") as f:
            f.write("{}: {}\n".format(timestamp, line))


class EncryptedBackup(object):
    def __init__(self, config, mailer):
        self._mailer = mailer
        date_today = str(datetime.date.today())
        inc_name = "Backup_{}".format(date_today)
        self._incrementals_dir = Path(config["backup"]["target_dir"]) / "Incremental"
        self._incremental_dir = Path(config["backup"]["target_dir"]) / "Incremental" / inc_name
        self._mirror_dir = Path(config["backup"]["target_dir"]) / "Mirror"
        self._src_dirs = Path(config["backup"]["src_dirs"])
        self._log = BackupLog(config["backup"]["log_dir"])
        self._rsync = config["general"]["rsync_path"]
        self._rsync_extra = config["backup"]["rsync_extra"]
        self._gpg_public_key = config["general"]["gpg_public_key"]
        self._dropbox_token = config["general"]["dropbox_token"]
        self._dropbox_target = Path(config["general"]["dropbox_target"]) / Path(inc_name)
        self._full_backup_interval = int(config["general"]["full_backup_interval"])
        self._encrypted_file = Path(config["backup"]["target_dir"]) / "{}.gpg".format(inc_name)
        self._tar_file = Path(config["backup"]["target_dir"]) / "{}.tar".format(inc_name)
        self._files_splitted = []

    def _delete_file(self, file):
        subprocess.run(["rm", "-f", file])

    def _delete_directory(self, directory):
        subprocess.run(["rm", "-rf", directory])

    def _delete_mirror_if_full_backup(self):
        dirs = list(self._incrementals_dir.glob("*"))
        if (len(dirs) % self._full_backup_interval == 0):
            try:
                mailer.send("Starting full backup", "Starting full backup.")
            except:
                pass
            self._log.write("Number of incremental backups is a multiple of " +
                " {}.".format(self._full_backup_interval))
            self._log.write("Time for a full backup.")
            self._log.write("Removing directory of mirror backup.")
            self._delete_directory(self._mirror_dir)

    def _create_dirs(self):
        self._log.write("Creating directory structure.")
        self._incremental_dir.mkdir(parents=True)
        self._mirror_dir.mkdir(exist_ok=True)

    def _create_incremental(self):
        self._log.write("Creating incremental backup in '{}'.".format(self._incremental_dir))
        rsync_cmd = "{} -ac {} --progress {} --compare-dest={} {}".format(self._rsync,
                self._src_dirs, self._incremental_dir, self._mirror_dir.absolute(),
                self._rsync_extra)
        self._log.write("Running: {}".format(rsync_cmd))
        rsync_proc = subprocess.run(rsync_cmd.split())
        self._log.write("Removing write access to '{}'".format(self._incremental_dir))
        ch_proc = subprocess.run(["chmod", "-R", "ugo-w", self._incremental_dir])

    def _create_mirror(self):
        self._log.write("Creating mirror in '{}'.".format(self._mirror_dir))
        rsync_cmd = "rsync -ac --delete {} {} {}".format(
                self._src_dirs, self._mirror_dir, self._rsync_extra)
        self._log.write("Running: {}".format(rsync_cmd))
        rsync_proc = subprocess.run(rsync_cmd.split())

    def _compress_incremental(self):
        self._delete_file(self._tar_file)
        self._log.write("Creating tar file of incremental backup.")
        tar_cmd = "tar cf {} {}".format(self._tar_file, self._incremental_dir)
        self._log.write("Running: {}".format(tar_cmd))
        tar_proc = subprocess.run(tar_cmd.split())

    def _encrypt_incremental(self):
        self._delete_file(self._encrypted_file)
        self._log.write("Encrypting incremental backup.")
        enc_cmd = "gpg -o {} --encrypt -r {} {}".format(self._encrypted_file, self._gpg_public_key, self._tar_file)
        self._log.write("Running: {}".format(enc_cmd))
        enc_proc = subprocess.run(enc_cmd.split())

    def _upload_to_dropbox(self):
        self._log.write("Uploading to dropbox.")
        try:
            f = self._encrypted_file
            self._log.write("Source file: {}".format(f))
            target_file = self._dropbox_target / f.name
            self._log.write("Target file: {}".format(target_file))
            dropbox_backup.upload_file(file_path=str(f), dest_path=str(target_file), token=self._dropbox_token)
        except Exception as ex:
            self._log.write("Exception when uploading to dropbox: {}.".format(ex))
            raise
        else:
            self._log.write("File uploaded successfully to dropbox.")

    def run(self):
        self._log.write("Starting incremental backup.")
        self._log.write("Source directories is '{}'.".format(self._src_dirs))
        self._delete_mirror_if_full_backup()
        self._create_dirs()
        self._create_incremental()
        self._create_mirror()
        self._compress_incremental()
        self._encrypt_incremental()
        self._upload_to_dropbox()
        self._delete_file(self._encrypted_file)
        self._delete_file(self._tar_file)

g_config = configparser.ConfigParser()
g_config.read("/home/sindre/bin/pybackup/example.ini")
g_log = BackupLog(g_config["backup"]["log_dir"])
lock_file = LockFile(g_config)
mailer = SendMail(g_config)
was_locked = False
try:
    if (lock_file.locked):
        print("Lock file is locked. Assuming process already running. Exiting.")
        mailer.send("Backup not started", "Backup did not start. Lock file is locked.")
        was_locked = True
        exit()
    else:
        lock_file.lock()
    encrypted_backup = EncryptedBackup(g_config, mailer)
    encrypted_backup.run()
    mailer.send("Backup success", "Everything is backed up.")
except Exception as e:
    g_log.write("Got exception: " + str(e))
    mailer.send("Backup failed", "Something failed when backing up. Exception was: {}".format(str(e)))
    raise e
finally:
    if not was_locked:
        lock_file.unlock()
