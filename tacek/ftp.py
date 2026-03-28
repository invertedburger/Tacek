import os
import ftplib
from tacek.config import FTP_HOST, FTP_USER, FTP_PASS, FTP_DIR


def upload(local_path, remote_filename=None):
    if not FTP_HOST:
        return
    remote_filename = remote_filename or os.path.basename(local_path)
    with ftplib.FTP(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        if FTP_DIR:
            ftp.cwd(FTP_DIR)
        with open(local_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_filename}', f)
    print(f"Uploaded to FTP: {remote_filename}")
