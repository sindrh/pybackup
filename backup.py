#!/usr/bin/python3

import configparser
from pathlib import Path
import datetime
import subprocess
import dropbox_backup



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
    def __init__(self, config):
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
        self._encrypted_file = "{}.gpg".format(inc_name)
        self._tar_file = "{}.tar".format(inc_name)
        self._files_splitted = []

    def _delete_file(self, file):
        subprocess.run(["rm", "-f", file])

    def _delete_directory(self, directory):
        subprocess.run(["rm", "-rf", directory])

    def _delete_mirror_if_full_backup(self):
        dirs = list(self._incrementals_dir.glob("*"))
        if (len(dirs) % self._full_backup_interval == 0):
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
        enc_cmd = "gpg -o {} --encrypt -r {} {}".format(self._encrypted_file,
                self._gpg_public_key, self._tar_file)
        self._log.write("Running: {}".format(enc_cmd))
        enc_proc = subprocess.run(enc_cmd.split())

    def _split_incremental(self):
        tmp_dir = Path("splitted_files")
        self._delete_directory(tmp_dir)
        subprocess.run(["mkdir", "-p", tmp_dir])
        split_cmd = "split --bytes=100 {} {}".format(self._encrypted_file, tmp_dir / "part_")
        subprocess.run(split_cmd.split())
        self._files_splitted = list(Path(".").glob(str(tmp_dir) + "/*"))
        print(self._files_splitted)

    def _upload_to_dropbox(self):
        self._log.write("Uploading to dropbox.")
        try:
            for f in self._files_splitted:
                self._log.write("Source file: {}".format(f))
                target_file = self._dropbox_target / f
                self._log.write("Target file: {}".format(target_file))
                dropbox_backup.upload_file(file_path=str(f), dest_path=str(target_file), token=self._dropbox_token)
        except Exception as ex:
            self._log.write("Exception when uploading to dropbox: {}.".format(ex))
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
        self._split_incremental()
        self._upload_to_dropbox()


g_config = configparser.ConfigParser()
g_config.read("example.ini")
g_log = BackupLog(g_config["backup"]["log_dir"])
lock_file = LockFile(g_config)
try:
    if (lock_file.locked):
        g_log.write("Lock file is locked. Assuming process already running. Exiting.")
        exit()
    else:
        lock_file.lock()
    encrypted_backup = EncryptedBackup(g_config)
    encrypted_backup.run()
except Exception as e:
    g_log.write("Got exception: " + str(e))
    raise e
finally:
    lock_file.unlock()
