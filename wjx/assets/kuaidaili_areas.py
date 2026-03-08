"""快代理地区编码数据加载器

加载 kuaidaili_area_codes.json 文件，提供省份和城市数据访问接口。
从 demo/wjx 移植并适配到当前项目。
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

_DATA_PATH = Path(__file__).with_name("kuaidaili_area_codes.json")

# 缓存加载的数据
_cached_data: Optional[Dict[str, Any]] = None


def _load_raw_data() -> Dict[str, Any]:
    """加载原始 JSON 数据（带缓存）"""
    global _cached_data
    if _cached_data is not None:
        return _cached_data
    
    try:
        with _DATA_PATH.open("r", encoding="utf-8") as f:
            _cached_data = json.load(f)
        return _cached_data
    except FileNotFoundError:
        logging.error(f"快代理地区数据文件不存在: {_DATA_PATH}")
        return {"provinces": []}
    except json.JSONDecodeError as e:
        logging.error(f"快代理地区数据文件格式错误: {e}")
        return {"provinces": []}
    except Exception as e:
        logging.error(f"加载快代理地区数据失败: {e}")
        return {"provinces": []}


def load_kuaidaili_provinces() -> List[Dict[str, Any]]:
    """加载快代理支持的省份列表
    
    Returns:
        省份列表，每个元素包含 code, name, cities 字段
    """
    data = _load_raw_data()
    return data.get("provinces", [])


def get_province_names() -> List[str]:
    """获取所有省份名称列表
    
    Returns:
        省份名称列表，如 ["北京", "上海", "广东", ...]
    """
    provinces = load_kuaidaili_provinces()
    return [p["name"] for p in provinces if p.get("name")]


def get_province_by_name(name: str) -> Optional[Dict[str, Any]]:
    """根据省份名称获取省份信息
    
    Args:
        name: 省份名称，如 "北京"
        
    Returns:
        省份信息字典，或 None
    """
    provinces = load_kuaidaili_provinces()
    for p in provinces:
        if p.get("name") == name:
            return p
    return None


def clear_cache():
    """清除缓存的数据（用于测试）"""
    global _cached_data
    _cached_data = None
