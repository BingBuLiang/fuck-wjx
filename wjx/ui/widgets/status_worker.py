"""状态查询 Worker，运行在独立 QThread 中。"""
from PySide6.QtCore import QObject, Signal


class StatusFetchWorker(QObject):
    """状态查询 Worker，运行在独立 QThread 中，确保线程安全。"""
    finished = Signal(str, str)  # text, color
    
    def __init__(self, fetcher, formatter):
        super().__init__()
        self.fetcher = fetcher
        self.formatter = formatter
        self._stopped = False
    
    def stop(self):
        """标记停止，防止后续操作"""
        self._stopped = True
    
    def fetch(self):
        """执行状态查询，完成后发送 finished 信号"""
        if self._stopped:
            return
        text = "未知：状态未知"
        color = "#666666"
        try:
            if self._stopped:
                return
            result = self.fetcher()
            if self._stopped:
                return
            if callable(self.formatter):
                fmt_result = self.formatter(result)
                if isinstance(fmt_result, tuple) and len(fmt_result) >= 2:
                    text, color = str(fmt_result[0]), str(fmt_result[1])
            else:
                if isinstance(result, dict):
                    online = result.get("online", None)
                    message = str(result.get("message") or "").strip()
                    if not message:
                        if online is True:
                            message = "系统正常运行中"
                        elif online is False:
                            message = "系统当前不在线"
                        else:
                            message = "状态未知"
                    if online is True:
                        text = f"在线：{message}"
                    elif online is False:
                        text = f"离线：{message}"
                    else:
                        text = f"未知：{message}"
                    color = "#228B22" if online is True else ("#cc0000" if online is False else "#666666")
                else:
                    text = "未知：返回数据格式异常"
                    color = "#666666"
        except Exception:
            text = "未知：状态获取失败"
            color = "#666666"
        
        if not self._stopped:
            self.finished.emit(text, color)
