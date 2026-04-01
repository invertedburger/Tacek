import os
import json
from datetime import datetime


class RunLogger:
    def __init__(self, results_dir):
        self.results_dir = results_dir
        self.logs_path = os.path.join(results_dir, 'run_log.json')
        self.logs = []
        self.start_time = datetime.now().isoformat()

    def log(self, message):
        """Add a log entry with timestamp."""
        timestamp = datetime.now().isoformat()
        self.logs.append({
            'time': timestamp,
            'message': message
        })
        print(message)

    def save(self):
        """Save logs to JSON file."""
        data = {
            'start_time': self.start_time,
            'end_time': datetime.now().isoformat(),
            'logs': self.logs
        }
        with open(self.logs_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


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
