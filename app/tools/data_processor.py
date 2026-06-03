"""数据处理工具"""
import json
import csv
from io import StringIO
from typing import Dict, Any, List, Optional
import re


def process_data(
    data: str,
    operation: str,
    params: Optional[Dict] = None,
) -> Dict[str, Any]:
    """处理数据
    
    Args:
        data: 数据内容 (JSON字符串或CSV字符串)
        operation: 操作类型
            - parse: 解析数据
            - filter: 过滤数据
            - transform: 转换数据
            - aggregate: 聚合数据
        params: 操作参数
            - filter: {"field": "字段名", "operator": "操作符", "value": "值"}
            - transform: {"mapping": {"旧字段": "新字段"}}
            - aggregate: {"group_by": "字段", "aggregation": "sum/count/avg"}
    
    Returns:
        处理结果
    """
    params = params or {}
    
    try:
        # 1. 解析数据
        parsed_data = _parse_data(data)
        if isinstance(parsed_data, dict) and "error" in parsed_data:
            return parsed_data
        
        # 2. 执行操作
        if operation == "parse":
            return {
                "success": True,
                "type": "list" if isinstance(parsed_data, list) else "dict",
                "count": len(parsed_data) if isinstance(parsed_data, list) else 1,
                "sample": parsed_data[:3] if isinstance(parsed_data, list) else parsed_data,
            }
        
        elif operation == "filter":
            return _filter_data(parsed_data, params)
        
        elif operation == "transform":
            return _transform_data(parsed_data, params)
        
        elif operation == "aggregate":
            return _aggregate_data(parsed_data, params)
        
        else:
            return {"error": f"Unknown operation: {operation}"}
    
    except Exception as e:
        return {"error": str(e)}


def _parse_data(data: str) -> Any:
    """解析数据"""
    data = data.strip()
    
    # 尝试JSON
    try:
        return json.loads(data)
    except:
        pass
    
    # 尝试CSV
    try:
        reader = csv.DictReader(StringIO(data))
        return list(reader)
    except:
        pass
    
    # 尝试行分割
    if "\n" in data:
        lines = data.split("\n")
        # 检测是否有固定分隔符
        if "|" in data:
            return [line.split("|") for line in lines if line.strip()]
        if "\t" in data:
            return [line.split("\t") for line in lines if line.strip()]
        return [line.strip() for line in lines if line.strip()]
    
    return {"error": "Unable to parse data"}


def _filter_data(data: List[Dict], params: Dict) -> Dict[str, Any]:
    """过滤数据"""
    if not isinstance(data, list):
        return {"error": "Filter requires list data"}
    
    field = params.get("field")
    operator = params.get("operator", "==")
    value = params.get("value")
    
    if not field:
        return {"error": "Missing 'field' parameter"}
    
    filtered = []
    for item in data:
        if not isinstance(item, dict):
            continue
        item_value = item.get(field)
        
        if operator == "==" and item_value == value:
            filtered.append(item)
        elif operator == "!=" and item_value != value:
            filtered.append(item)
        elif operator == ">" and item_value > value:
            filtered.append(item)
        elif operator == "<" and item_value < value:
            filtered.append(item)
        elif operator == ">=" and item_value >= value:
            filtered.append(item)
        elif operator == "<=" and item_value <= value:
            filtered.append(item)
        elif operator == "contains" and value in str(item_value):
            filtered.append(item)
    
    return {
        "success": True,
        "count": len(filtered),
        "data": filtered[:100],  # 限制返回数量
    }


def _transform_data(data: List[Dict], params: Dict) -> Dict[str, Any]:
    """转换数据"""
    mapping = params.get("mapping", {})
    if not mapping:
        return {"error": "Missing 'mapping' parameter"}
    
    if isinstance(data, list):
        transformed = []
        for item in data:
            if isinstance(item, dict):
                new_item = {}
                for old_key, new_key in mapping.items():
                    if old_key in item:
                        new_item[new_key] = item[old_key]
                transformed.append(new_item)
        return {"success": True, "count": len(transformed), "data": transformed[:100]}
    
    return {"error": "Transform requires list data"}


def _aggregate_data(data: List[Dict], params: Dict) -> Dict[str, Any]:
    """聚合数据"""
    group_by = params.get("group_by")
    aggregation = params.get("aggregation", "count")
    field = params.get("field")
    
    if not isinstance(data, list):
        return {"error": "Aggregate requires list data"}
    
    if not group_by:
        # 简单聚合
        if aggregation == "count":
            return {"success": True, "result": len(data)}
        elif aggregation == "sum" and field:
            total = sum(item.get(field, 0) for item in data if isinstance(item, dict))
            return {"success": True, "result": total}
        elif aggregation == "avg" and field:
            values = [item.get(field) for item in data if isinstance(item, dict) and item.get(field)]
            avg = sum(values) / len(values) if values else 0
            return {"success": True, "result": avg}
    
    # 分组聚合
    groups = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        key = item.get(group_by, "unknown")
        if key not in groups:
            groups[key] = []
        groups[key].append(item)
    
    result = {}
    for key, items in groups.items():
        if aggregation == "count":
            result[key] = len(items)
        elif aggregation == "sum" and field:
            result[key] = sum(item.get(field, 0) for item in items)
        elif aggregation == "avg" and field:
            values = [item.get(field) for item in items if item.get(field)]
            result[key] = sum(values) / len(values) if values else 0
    
    return {"success": True, "groups": len(groups), "result": result}
