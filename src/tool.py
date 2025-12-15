"""
工具函数模块
包含所有查询工具的定义
"""

from typing import Optional, List
from langchain_core.tools import tool
import random
from datetime import datetime, timedelta
from common import DESTINATIONS, ATTRACTIONS_DB


def get_price_range(destination: str, price_type: str) -> tuple:
    """获取价格范围"""
    dest_config = DESTINATIONS.get(destination, {"flight": (800, 2000), "hotel": (300, 800), "daily": 300})
    return dest_config.get(price_type, (300, 800))


@tool
def query_flight_prices(destination: str, travel_date: Optional[str] = None, requirements: Optional[List[str]] = None) -> dict:
    """查询机票价格工具"""
    print(f"✈️ 查询 {destination} 机票价格...")
    
    min_price, max_price = get_price_range(destination, "flight")
    base_price = random.randint(min_price, max_price)
    
    # 节假日价格调整
    if travel_date and ("国庆" in travel_date or "春节" in travel_date):
        base_price = int(base_price * 1.5)
    
    # 豪华需求价格调整
    if requirements:
        for req in requirements:
            if "头等舱" in req or "商务舱" in req:
                base_price = int(base_price * 2.5)
                break
            elif "豪华" in req:
                base_price = int(base_price * 1.8)
    
    return {
        "type": "flight",
        "destination": destination,
        "price": base_price,
        "airlines": random.sample(["东方航空", "南方航空", "中国国航", "海南航空"], 2),
        "dates": {
            "departure": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
            "return": (datetime.now() + timedelta(days=12)).strftime("%Y-%m-%d")
        }
    }


@tool
def query_hotel_prices(destination: str, days: int, travelers: Optional[str] = "2人", requirements: Optional[List[str]] = None) -> dict:
    """查询酒店价格工具"""
    print(f"🏨 查询 {destination} 酒店价格...")
    
    min_price, max_price = get_price_range(destination, "hotel")
    price_per_night = random.randint(min_price, max_price)
    
    # 根据人数调整价格
    if travelers and ("3人" in travelers or "家庭" in travelers):
        price_per_night = int(price_per_night * 1.3)
    elif travelers and ("4人" in travelers or "5人" in travelers):
        price_per_night = int(price_per_night * 1.5)
    
    # 豪华需求价格调整
    if requirements:
        for req in requirements:
            if "五星级" in req or "奢华" in req:
                price_per_night = int(price_per_night * 3.0)
                break
            elif "豪华" in req or "四星级" in req:
                price_per_night = int(price_per_night * 2.0)
    
    hotel_types = {
        "云南": ["丽江古城客栈", "大理洱海民宿", "香格里拉藏式酒店"],
        "北京": ["王府井附近酒店", "四合院特色酒店", "商务型酒店"],
        "上海": ["外滩景观酒店", "迪士尼度假区酒店", "静安寺附近酒店"],
        "三亚": ["海景度假酒店", "沙滩别墅", "温泉酒店"],
        "西安": ["古城内酒店", "兵马俑附近酒店", "特色民宿"],
    }
    
    hotels = hotel_types.get(destination, ["当地特色酒店", "舒适型酒店"])
    
    return {
        "type": "hotel",
        "destination": destination,
        "price_per_night": price_per_night,
        "total_price": price_per_night * (days - 1),
        "recommended": hotels[0],
        "nights": days - 1
    }


@tool
def query_attractions(destination: str, days: int, requirements: Optional[List[str]] = None) -> dict:
    """查询景点信息工具"""
    print(f"🏞️ 查询 {destination} 景点信息...")
    
    dest_info = ATTRACTIONS_DB.get(destination, {
        "景点": ["当地著名景点", "文化遗址", "自然风光"],
        "特色": ["地方文化", "历史遗迹", "自然景观"]
    })
    
    attractions = dest_info["景点"]
    features = dest_info["特色"]
    
    # 根据要求筛选景点
    if requirements:
        filtered = []
        for req in requirements:
            if "亲子" in req:
                filtered.extend([a for a in attractions if "乐园" in a or "公园" in a])
            elif "文化" in req:
                filtered.extend([a for a in attractions if "文化" in a or "历史" in a or "博物" in a])
            elif "自然" in req:
                filtered.extend([a for a in attractions if "山" in a or "湖" in a or "海" in a])
        attractions = filtered if filtered else attractions
    
    daily_plans = [f"第{i+1}天：{attractions[i % len(attractions)]}" for i in range(days)]
    
    return {
        "type": "attractions",
        "destination": destination,
        "attractions": attractions[:days+2],
        "daily_plans": daily_plans,
        "features": features
    }


@tool
def write_itinerary_to_file(itinerary_content: str, filename: Optional[str] = None) -> dict:
    """将旅游行程写入文件工具"""
    import os
    from datetime import datetime
    
    # 如果没有指定文件名，使用时间戳生成
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"travel_itinerary_{timestamp}.txt"
    
    # 确保文件名有正确的扩展名
    if not filename.endswith('.txt'):
        filename += '.txt'
    
    # 创建输出目录
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    file_path = os.path.join(output_dir, filename)
    
    try:
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("🌟 智能旅游规划系统 - 行程方案\n")
            f.write("=" * 60 + "\n")
            f.write(f"📅 生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            f.write(itinerary_content)
            f.write("\n\n" + "=" * 60 + "\n")
            f.write("📝 本行程由LangGraph智能旅游规划系统生成\n")
            f.write("🔄 如需修改，请重新运行系统或联系客服\n")
            f.write("=" * 60 + "\n")
        
        print(f"✅ 行程已成功保存到文件: {file_path}")
        
        return {
            "success": True,
            "file_path": file_path,
            "filename": filename,
            "size": os.path.getsize(file_path),
            "message": f"行程已成功保存到 {file_path}"
        }
        
    except Exception as e:
        print(f"❌ 文件写入失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"文件写入失败: {e}"
        }