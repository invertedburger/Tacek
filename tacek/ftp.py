import os
import ftplib
from tacek.config import FTP_HOST, FTP_USER, FTP_PASS, FTP_DIR
from tacek.logger import log


def upload(local_path, remote_filename=None):
    if not FTP_HOST:
        return

    if not os.path.exists(local_path):
        log(f"FTP upload skipped: file not found {local_path}")
        return

    remote_filename = remote_filename or os.path.basename(local_path)

    # Validate remote_filename is safe (no path separators or dangerous chars)
    if '/' in remote_filename or '\\' in remote_filename:
        raise ValueError(f"Invalid remote_filename (contains path separators): {remote_filename}")

    try:
        with ftplib.FTP(FTP_HOST, timeout=30) as ftp:
            ftp.login(FTP_USER, FTP_PASS)
            if FTP_DIR:
                ftp.cwd(FTP_DIR)
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_filename}', f)
        log(f"Uploaded to FTP: {remote_filename}")
    except ftplib.all_errors as e:
        log(f"FTP error uploading {remote_filename}: {e}")
        raise
    except Exception as e:
        log(f"Unexpected error uploading to FTP: {e}")
        raise
