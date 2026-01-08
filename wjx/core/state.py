"""
全局状态管理模块
"""
import threading
from typing import List, Optional, Union, Dict, Any, Tuple


class EngineState:
    """引擎全局状态单例类"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 问卷配置
        self.url: str = ""
        self.single_prob: List[Union[List[float], int, float, None]] = []
        self.droplist_prob: List[Union[List[float], int, float, None]] = []
        self.multiple_prob: List[List[float]] = []
        self.matrix_prob: List[Union[List[float], int, float, None]] = []
        self.scale_prob: List[Union[List[float], int, float, None]] = []
        self.slider_targets: List[float] = []
        self.texts: List[List[str]] = []
        self.texts_prob: List[List[float]] = []
        self.text_entry_types: List[str] = []
        self.single_option_fill_texts: List[Optional[List[Optional[str]]]] = []
        self.droplist_option_fill_texts: List[Optional[List[Optional[str]]]] = []
        self.multiple_option_fill_texts: List[Optional[List[Optional[str]]]] = []
        
        # 运行参数
        self.target_num: int = 1
        self.fail_threshold: int = 1
        self.num_threads: int = 1
        self.cur_num: int = 0
        self.cur_fail: int = 0
        self.stop_on_fail_enabled: bool = True
        
        # 时间控制
        self.submit_interval_range_seconds: Tuple[int, int] = (0, 0)
        self.answer_duration_range_seconds: Tuple[int, int] = (0, 0)
        self.duration_control_enabled: bool = False
        self.duration_control_estimated_seconds: int = 0
        self.duration_control_total_duration_seconds: int = 0
        
        # 定时模式
        self.timed_mode_enabled: bool = False
        self.timed_mode_refresh_interval: float = 5.0
        
        # 代理相关
        self.random_proxy_ip_enabled: bool = False
        self.proxy_ip_pool: List[str] = []
        self.random_user_agent_enabled: bool = False
        self.user_agent_pool_keys: List[str] = []
        
        # 状态标志
        self.last_submit_had_captcha: bool = False
        self._aliyun_captcha_stop_triggered: bool = False
        self._aliyun_captcha_stop_lock = threading.Lock()
        self._aliyun_captcha_popup_shown: bool = False
        self._target_reached_stop_triggered: bool = False
        self._target_reached_stop_lock = threading.Lock()
        self._resume_after_aliyun_captcha_stop: bool = False
        self._resume_snapshot: Dict[str, Any] = {}
        
        # 线程控制
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        
        self._initialized = True
    
    def reset(self):
        """重置所有状态"""
        self.__init__()


# 全局实例
_state = EngineState()


def get_state() -> EngineState:
    """获取全局状态实例"""
    return _state
