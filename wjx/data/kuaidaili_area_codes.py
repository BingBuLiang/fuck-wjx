"""快代理地区编码数据加载器

加载 kuaidaili_area_codes.json 文件，提供省份和城市数据访问接口。
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

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
        示例: [{"code": "11", "name": "北京", "cities": [...]}, ...]
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


def get_province_by_code(code: str) -> Optional[Dict[str, Any]]:
    """根据省份编码获取省份信息
    
    Args:
        code: 省份编码（2位），如 "11"
        
    Returns:
        省份信息字典，或 None
    """
    provinces = load_kuaidaili_provinces()
    for p in provinces:
        if p.get("code") == code:
            return p
    return None


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


def get_cities_by_province_code(province_code: str) -> List[Dict[str, str]]:
    """获取指定省份的城市列表
    
    Args:
        province_code: 省份编码（2位），如 "44"
        
    Returns:
        城市列表，每个元素包含 code, name 字段
    """
    province = get_province_by_code(province_code)
    if province:
        return province.get("cities", [])
    return []


def code_to_name(code: str) -> str:
    """将地区编码转换为名称
    
    Args:
        code: 地区编码（2位省份码或6-7位城市码）
        
    Returns:
        地区名称，找不到返回原编码
    """
    if len(code) == 2:
        # 省份编码
        province = get_province_by_code(code)
        return province["name"] if province else code
    else:
        # 城市编码，先找省份
        province_code = code[:2]
        province = get_province_by_code(province_code)
        if province:
            for city in province.get("cities", []):
                if city.get("code") == code:
                    return city["name"]
        return code


def name_to_code(name: str) -> Optional[str]:
    """将地区名称转换为编码
    
    Args:
        name: 地区名称（省份或城市）
        
    Returns:
        地区编码，找不到返回 None
    """
    provinces = load_kuaidaili_provinces()
    
    # 先查省份
    for p in provinces:
        if p.get("name") == name:
            return p["code"]
        # 再查城市
        for city in p.get("cities", []):
            if city.get("name") == name:
                return city["code"]
    
    return None


def get_province_code_name_pairs() -> List[Tuple[str, str]]:
    """获取省份编码和名称的配对列表
    
    Returns:
        [(code, name), ...] 列表，如 [("11", "北京"), ("31", "上海"), ...]
    """
    provinces = load_kuaidaili_provinces()
    return [(p["code"], p["name"]) for p in provinces if p.get("code") and p.get("name")]


def clear_cache():
    """清除缓存的数据（用于测试）"""
    global _cached_data, _cached_hierarchical
    _cached_data = None
    _cached_hierarchical = None


# 缓存三级层次结构
_cached_hierarchical: Optional[List[Dict[str, Any]]] = None


def build_hierarchical_data() -> List[Dict[str, Any]]:
    """构建三级层次结构（省→市→区）
    
    根据行政区划编码规则，将扁平的城市列表转换为三级结构：
    - 省份编码：2位（如 41 = 河南）
    - 地级市编码：6位，后两位为00（如 410300 = 洛阳市）
    - 区县编码：6位，后两位非00（如 410303 = 西工区）
    
    特殊处理：
    - 直辖市（北京、上海、天津、重庆）：省份下直接是区，无地级市层
    - 省直辖县级行政区划：7位编码如 4190000，下属县级市如 419001
    
    Returns:
        三级结构列表
    """
    global _cached_hierarchical
    if _cached_hierarchical is not None:
        return _cached_hierarchical
    
    provinces = load_kuaidaili_provinces()
    result = []
    
    # 直辖市编码（这些省份下直接是区，无地级市层）
    direct_municipalities = {"11", "12", "31", "50"}  # 北京、天津、上海、重庆
    
    for province in provinces:
        province_code = province.get("code", "")
        province_name = province.get("name", "")
        flat_cities = province.get("cities", [])
        
        if not province_code or not province_name:
            continue
        
        if province_code in direct_municipalities:
            # 直辖市：cities 就是区列表，直接作为 districts
            result.append({
                "code": province_code,
                "name": province_name,
                "is_municipality": True,
                "cities": [],
                "districts": flat_cities
            })
        else:
            # 普通省份：需要根据编码分组
            cities_map: Dict[str, Dict[str, Any]] = {}
            
            for item in flat_cities:
                code = item.get("code", "")
                name = item.get("name", "")
                if not code or not name:
                    continue
                
                # 特殊处理：7位编码的省直辖县级行政区划（如 4190000）
                if len(code) == 7 and code.endswith("0000"):
                    city_prefix = code[:3]  # 如 "419"
                    if city_prefix not in cities_map:
                        cities_map[city_prefix] = {
                            "code": code,
                            "name": name,
                            "districts": []
                        }
                    else:
                        cities_map[city_prefix]["code"] = code
                        cities_map[city_prefix]["name"] = name
                # 特殊处理：6位编码但属于省直辖（如 419001 济源市）
                elif len(code) == 6 and code[2] == "9":
                    city_prefix = code[:3]  # 如 "419"
                    if city_prefix not in cities_map:
                        cities_map[city_prefix] = {
                            "code": "",
                            "name": "",
                            "districts": []
                        }
                    cities_map[city_prefix]["districts"].append({
                        "code": code,
                        "name": name
                    })
                # 普通地级市（6位，后两位为00）
                elif len(code) == 6 and code[4:6] == "00":
                    city_prefix = code[:4]
                    if city_prefix not in cities_map:
                        cities_map[city_prefix] = {
                            "code": code,
                            "name": name,
                            "districts": []
                        }
                    else:
                        cities_map[city_prefix]["code"] = code
                        cities_map[city_prefix]["name"] = name
                # 普通区县（6位，后两位非00）
                else:
                    city_prefix = code[:4]
                    if city_prefix not in cities_map:
                        cities_map[city_prefix] = {
                            "code": "",
                            "name": "",
                            "districts": []
                        }
                    cities_map[city_prefix]["districts"].append({
                        "code": code,
                        "name": name
                    })
            
            # 整理城市列表
            cities_list = []
            orphan_districts = []
            
            for prefix, city_data in cities_map.items():
                if city_data["code"] and city_data["name"]:
                    cities_list.append(city_data)
                elif city_data["districts"]:
                    orphan_districts.extend(city_data["districts"])
            
            # 按编码排序
            cities_list.sort(key=lambda x: x["code"])
            
            result.append({
                "code": province_code,
                "name": province_name,
                "is_municipality": False,
                "cities": cities_list,
                "districts": orphan_districts
            })
    
    _cached_hierarchical = result
    return result


def get_hierarchical_province(province_code: str) -> Optional[Dict[str, Any]]:
    """获取三级结构中的省份数据"""
    data = build_hierarchical_data()
    for p in data:
        if p.get("code") == province_code:
            return p
    return None


def get_hierarchical_city(province_code: str, city_code: str) -> Optional[Dict[str, Any]]:
    """获取三级结构中的城市数据"""
    province = get_hierarchical_province(province_code)
    if not province:
        return None
    for city in province.get("cities", []):
        if city.get("code") == city_code:
            return city
    return None
