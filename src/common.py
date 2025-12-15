"""
旅游规划助手 - 公共模块
包含常量定义和辅助函数
"""

import json
import os
from typing import Dict, Any, Optional
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# ==================== 常量定义 ====================
DESTINATIONS = {
    "云南": {"flight": (1200, 2500), "hotel": (400, 1000), "daily": 300},
    "北京": {"flight": (800, 1800), "hotel": (500, 1200), "daily": 350},
    "上海": {"flight": (600, 1500), "hotel": (600, 1500), "daily": 400},
    "三亚": {"flight": (1500, 3000), "hotel": (800, 2000), "daily": 450},
    "西安": {"flight": (1000, 2000), "hotel": (300, 800), "daily": 250},
    "欧洲": {"flight": (8000, 15000), "hotel": (1200, 3000), "daily": 800},
    "日本": {"flight": (3000, 6000), "hotel": (800, 2000), "daily": 600},
    "韩国": {"flight": (2000, 4000), "hotel": (600, 1500), "daily": 500},
    "新加坡": {"flight": (3500, 6500), "hotel": (1000, 2500), "daily": 700},
}

ATTRACTIONS_DB = {
    "云南": {"景点": ["丽江古城", "玉龙雪山", "大理洱海", "香格里拉", "西双版纳热带雨林"], "特色": ["纳西文化", "雪山风光", "白族风情", "藏族文化", "热带风情"]},
    "北京": {"景点": ["故宫", "长城", "天安门", "颐和园", "天坛"], "特色": ["皇家建筑", "历史遗迹", "政治中心", "皇家园林", "祭天建筑"]},
    "上海": {"景点": ["外滩", "迪士尼乐园", "东方明珠", "南京路", "豫园"], "特色": ["万国建筑", "主题乐园", "城市地标", "购物天堂", "古典园林"]},
    "三亚": {"景点": ["亚龙湾", "天涯海角", "南山寺", "蜈支洲岛", "大小洞天"], "特色": ["沙滩度假", "浪漫地标", "佛教文化", "潜水天堂", "道教文化"]},
    "西安": {"景点": ["兵马俑", "大雁塔", "古城墙", "华清池", "钟鼓楼"], "特色": ["考古奇迹", "佛教圣地", "古代防御", "温泉历史", "古代报时"]},
}

# ==================== LLM 初始化 ====================
def get_llm():
    """获取LLM实例"""
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("MODEL")
    if not api_key:
        raise ValueError("请设置OPENAI_API_KEY环境变量")
    return ChatOpenAI(model=model, temperature=0.3, api_key=api_key)

# ==================== 辅助函数 ====================
def parse_llm_json(content: str) -> dict:
    """解析LLM返回的JSON"""
    try:
        if '```json' in content:
            json_str = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            json_str = content.split('```')[1].strip()
        else:
            json_str = content.strip()
        return json.loads(json_str)
    except Exception as e:
        print(f"❌ JSON解析失败: {e}")
        return {}

def extract_travel_info(user_query: str, llm) -> dict:
    """提取旅游信息"""
    response = llm.invoke(f"""
    从用户查询中提取旅游信息：{user_query}
    
    返回JSON格式：
    {{
        "destination": "目的地或'未提供'",
        "days": "天数或'未提供'",
        "budget": "预算或'未提供'",
        "travel_date": "时间或'未提供'",
        "travelers": "人数或'未提供'",
        "requirements": ["要求列表"]
    }}
    """)
    
    parsed = parse_llm_json(response.content)
    if not parsed:
        return {"destination": "未提供", "days": "未提供", "budget": "未提供", 
                "travel_date": "未提供", "travelers": "未提供", "requirements": []}
    return parsed

def parse_value(value, default, is_float=False):
    """解析数值"""
    if value == "未提供" or not value:
        return default
    try:
        if is_float:
            if isinstance(value, str):
                if "千" in value:
                    return float(value.replace("千", "")) * 1000
                elif "万" in value:
                    return float(value.replace("万", "")) * 10000
                elif "元" in value:
                    return float(value.replace("元", ""))
            return float(value)
        else:
            # 处理整数值，支持带单位的数字（如"10天"、"5人"等）
            if isinstance(value, str):
                # 提取字符串中的数字
                import re
                numbers = re.findall(r'\d+', value)
                if numbers:
                    return int(numbers[0])  # 取第一个数字
                else:
                    return default
            elif str(value).isdigit():
                return int(value)
            else:
                return default
    except:
        return default

def add_message(state: Dict[str, Any], content: str) -> Dict[str, Any]:
    """添加消息到状态"""
    messages = state.get("messages", [])
    return {**state, "messages": messages + [AIMessage(content=content)]}

def get_travel_info(state: Dict[str, Any], key: str, default=None):
    """获取旅行信息"""
    travel_info = state.get("travel_info", {})
    return travel_info.get(key, default)

def set_travel_info(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """设置旅行信息"""
    travel_info = state.get("travel_info", {})
    travel_info.update(kwargs)
    return {**state, "travel_info": travel_info}

def get_price_range(destination: str, price_type: str) -> tuple:
    """获取价格范围"""
    dest_config = DESTINATIONS.get(destination, {"flight": (800, 2000), "hotel": (300, 800), "daily": 300})
    return dest_config.get(price_type, (300, 800))

def get_daily_expense(destination: str) -> int:
    """获取每日开销估算"""
    daily_expense_map = {
        "云南": 300,
        "北京": 350,
        "上海": 400,
        "三亚": 450,
        "西安": 250,
        "欧洲": 800,
        "日本": 600,
        "韩国": 500,
        "新加坡": 700
    }
    return daily_expense_map.get(destination, 300)