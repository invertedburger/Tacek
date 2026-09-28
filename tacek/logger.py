import os
import json
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

_PRAGUE_TZ = ZoneInfo("Europe/Prague")  # DST-aware (CET/CEST)
_MAX_LOG_ENTRIES = 10000  # Prevent unbounded growth


class RunLogger:
    def __init__(self, results_dir):
        self.results_dir = results_dir
        self.logs_path = os.path.join(results_dir, 'run_log.json')
        self.logs = []
        self.start_time = datetime.now(_PRAGUE_TZ).isoformat()

    def log(self, message):
        """Add a log entry with timestamp."""
        timestamp = datetime.now(_PRAGUE_TZ).isoformat()
        self.logs.append({
            'time': timestamp,
            'message': message
        })
        print(message)

    def save(self):
        """Save logs to JSON file with atomic write and growth prevention."""
        # Ensure results directory exists
        if not os.path.exists(self.results_dir):
            try:
                os.makedirs(self.results_dir, exist_ok=True)
            except Exception as e:
                print(f"Error creating results directory {self.results_dir}: {e}")
                return

        # Trim logs if they exceed maximum entries (keep latest)
        if len(self.logs) > _MAX_LOG_ENTRIES:
            print(f"Log truncated: {len(self.logs)} entries > {_MAX_LOG_ENTRIES} max")
            self.logs = self.logs[-_MAX_LOG_ENTRIES:]

        data = {
            'start_time': self.start_time,
            'end_time': datetime.now(_PRAGUE_TZ).isoformat(),
            'logs': self.logs
        }

        # Atomic write: write to temp file first, then rename
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=self.results_dir,
                delete=False,
                suffix='.json'
            ) as tmp_f:
                tmp_path = tmp_f.name        # before the dump, so a failed dump is cleaned up
                json.dump(data, tmp_f, ensure_ascii=False, indent=2)
            # Rename is atomic on most systems
            os.replace(tmp_path, self.logs_path)
        except Exception as e:
            print(f"Error saving logs to {self.logs_path}: {e}")
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


# Global logger instance
_logger_instance = None


def init_logger(results_dir):
    """Initialize the global logger."""
    global _logger_instance
    _logger_instance = RunLogger(results_dir)
    return _logger_instance


def get_logger():
    """Get the global logger instance."""
    return _logger_instance


def log(message):
    """Log a message using the global logger."""
    if _logger_instance:
        _logger_instance.log(message)
    else:
        print(message)
