import os
import sys
from datetime import datetime
from typing import Optional

class DualLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.log_file = None
        self._ensure_log_dir()
        self._create_log_file()
    
    def _ensure_log_dir(self):
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def _create_log_file(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"travel_planning_{timestamp}.log"
        self.log_file = os.path.join(self.log_dir, log_filename)
    
    def log_print(self, *args, **kwargs):
        message = " ".join(str(arg) for arg in args)
        
        print(*args, **kwargs)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"日志写入失败: {e}")

dual_logger = DualLogger()

def log_print(*args, **kwargs):
    dual_logger.log_print(*args, **kwargs)