import pytest
from unittest.mock import MagicMock, patch, call

from tacek import ftp


def test_upload_noop_when_host_empty(tmp_path):
    f = tmp_path / 'index.html'
    f.write_text('<html/>')
    with patch.object(ftp, 'FTP_HOST', ''):
        with patch('ftplib.FTP') as mock_cls:
            ftp.upload(str(f))
    mock_cls.assert_not_called()


def test_upload_connects_logs_in_and_stores(tmp_path):
    f = tmp_path / 'index.html'
    f.write_text('<html>hello</html>')

    mock_ftp = MagicMock()
    mock_cls = MagicMock()
    mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ftp)
    mock_cls.return_value.__exit__ = MagicMock(return_value=False)

    with patch.object(ftp, 'FTP_HOST', 'ftp.example.com'):
        with patch.object(ftp, 'FTP_USER', 'user'):
            with patch.object(ftp, 'FTP_PASS', 'pass'):
                with patch.object(ftp, 'FTP_DIR', '/www'):
                    with patch('ftplib.FTP', mock_cls):
                        ftp.upload(str(f), 'index.html')

    mock_ftp.login.assert_called_once_with('user', 'pass')
    mock_ftp.cwd.assert_called_once_with('/www')
    stor_cmd = mock_ftp.storbinary.call_args[0][0]
    assert stor_cmd == 'STOR index.html'


def test_upload_skips_cwd_when_ftp_dir_empty(tmp_path):
    f = tmp_path / 'file.html'
    f.write_text('data')

    mock_ftp = MagicMock()
    mock_cls = MagicMock()
    mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ftp)
    mock_cls.return_value.__exit__ = MagicMock(return_value=False)

    with patch.object(ftp, 'FTP_HOST', 'ftp.example.com'):
        with patch.object(ftp, 'FTP_USER', 'u'):
            with patch.object(ftp, 'FTP_PASS', 'p'):
                with patch.object(ftp, 'FTP_DIR', ''):
                    with patch('ftplib.FTP', mock_cls):
                        ftp.upload(str(f), 'file.html')

    mock_ftp.cwd.assert_not_called()


def test_upload_uses_basename_when_remote_name_omitted(tmp_path):
    f = tmp_path / 'mypage.html'
    f.write_text('data')

    mock_ftp = MagicMock()
    mock_cls = MagicMock()
    mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ftp)
    mock_cls.return_value.__exit__ = MagicMock(return_value=False)

    with patch.object(ftp, 'FTP_HOST', 'ftp.example.com'):
        with patch.object(ftp, 'FTP_USER', 'u'):
            with patch.object(ftp, 'FTP_PASS', 'p'):
                with patch.object(ftp, 'FTP_DIR', ''):
                    with patch('ftplib.FTP', mock_cls):
                        ftp.upload(str(f))

    stor_cmd = mock_ftp.storbinary.call_args[0][0]
    assert stor_cmd == 'STOR mypage.html'
