import sys
import os
import dropbox

from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError


def upload_file(file_path, dest_path, token):
    dbx = dropbox.Dropbox(token)
    with open(file_path, 'rb') as f:
        file_size = os.path.getsize(file_path)
        CHUNK_SIZE = 4 * 1024 * 1024
        if file_size <= CHUNK_SIZE:
            print(dbx.files_upload(f.read(), dest_path, mode=WriteMode('overwrite')))
        else:
            upload_session_start_result = dbx.files_upload_session_start(f.read(CHUNK_SIZE))
            cursor = dropbox.files.UploadSessionCursor(
                    session_id = upload_session_start_result.session_id, offset=f.tell())
            commit = dropbox.files.CommitInfo(path = dest_path)
            while f.tell() < file_size:
                cursor.offset = f.tell()
                if ((file_size - f.tell()) <= CHUNK_SIZE):
                    dbx.files_upload_session_finish(f.read(CHUNK_SIZE), cursor, commit)
                else:
                    dbx.files_upload_session_append_v2(f.read(CHUNK_SIZE), cursor)
