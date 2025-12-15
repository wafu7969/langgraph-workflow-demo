#!/usr/bin/env python3
"""
测试预算修复 - 验证预算计算的合理性
"""

import asyncio
import sys
import os

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from node import node_budget_optimization
from common import get_daily_expense, get_price_range
import random

def test_budget_calculation():
    """测试预算计算的合理性"""
    
    print("🧪 测试预算计算修复")
    print("=" * 60)
    
    # 测试场景1：欧洲豪华旅游15天，预算1000元（明显不足）
    print("\n📝 测试场景1: 欧洲豪华旅游15天，预算1000元")
    
    # 模拟查询结果
    # 模拟欧洲豪华机票价格
    min_flight, max_flight = get_price_range("欧洲", "flight")
    flight_price = random.randint(min_flight, max_flight) * 2.5  # 头等舱价格
    
    # 模拟欧洲豪华酒店价格
    min_hotel, max_hotel = get_price_range("欧洲", "hotel")
    hotel_price_per_night = random.randint(min_hotel, max_hotel) * 3.0  # 五星级价格
    
    flight_result = {"price": int(flight_price)}
    hotel_result = {
        "price_per_night": int(hotel_price_per_night),
        "total_price": int(hotel_price_per_night * 14)  # 14晚
    }
    daily_cost = get_daily_expense("欧洲")
    
    print(f"✈️ 机票价格: {flight_result['price']:,}元")
    print(f"🏨 酒店价格: {hotel_result['total_price']:,}元 ({hotel_result['price_per_night']}元/晚)")
    print(f"🍽️ 每日开销: {daily_cost}元")
    
    total_daily_cost = daily_cost * 15
    other_costs = 500
    total_cost = flight_result['price'] + hotel_result['total_price'] + total_daily_cost + other_costs
    
    print(f"💸 总费用: {total_cost:,}元")
    print(f"💰 用户预算: 1,000元")
    print(f"📊 超支比例: {(total_cost-1000)/1000*100:.1f}%")
    
    # 测试预算优化节点
    test_state = {
        "travel_info": {
            "destination": "欧洲",
            "days": 15,
            "budget": 1000,
            "travelers": "2人",
            "requirements": ["豪华", "五星级酒店", "头等舱"]
        },
        "query_results": {
            "flight": flight_result,
            "hotel": hotel_result
        },
        "_control": {}
    }
    
    print("\n🔄 执行预算优化节点...")
    result_state = node_budget_optimization(test_state)
    
    control = result_state.get("_control", {})
    cost_analysis = result_state.get("cost_analysis", {})
    
    print(f"\n📊 优化结果:")
    print(f"   🔄 优化尝试次数: {control.get('budget_optimization_attempts', 0)}")
    print(f"   ✅ 预算满意: {control.get('budget_satisfied', False)}")
    print(f"   🚨 需要人工干预: {control.get('needs_human_intervention', False)}")
    print(f"   💰 优化后费用: {cost_analysis.get('total_cost', 0):,}元")
    
    # 测试场景2：日本旅游7天，预算30000元（合理预算）
    print("\n" + "=" * 60)
    print("📝 测试场景2: 日本旅游7天，预算30000元")
    
    # 模拟日本普通旅游价格
    min_flight2, max_flight2 = get_price_range("日本", "flight")
    flight_price2 = random.randint(min_flight2, max_flight2)
    
    min_hotel2, max_hotel2 = get_price_range("日本", "hotel")
    hotel_price_per_night2 = random.randint(min_hotel2, max_hotel2)
    
    flight_result2 = {"price": flight_price2}
    hotel_result2 = {
        "price_per_night": hotel_price_per_night2,
        "total_price": hotel_price_per_night2 * 6  # 6晚
    }
    daily_cost2 = get_daily_expense("日本")
    
    print(f"✈️ 机票价格: {flight_result2['price']:,}元")
    print(f"🏨 酒店价格: {hotel_result2['total_price']:,}元")
    print(f"🍽️ 每日开销: {daily_cost2}元")
    
    total_daily_cost2 = daily_cost2 * 7
    total_cost2 = flight_result2['price'] + hotel_result2['total_price'] + total_daily_cost2 + 500
    
    print(f"💸 总费用: {total_cost2:,}元")
    print(f"💰 用户预算: 30,000元")
    
    if total_cost2 <= 30000:
        print("✅ 预算充足，无需优化")
    else:
        print(f"📊 超支: {total_cost2-30000:,}元")
    
    test_state2 = {
        "travel_info": {
            "destination": "日本",
            "days": 7,
            "budget": 30000,
            "travelers": "2人",
            "requirements": []
        },
        "query_results": {
            "flight": flight_result2,
            "hotel": hotel_result2
        },
        "_control": {}
    }
    
    print("\n🔄 执行预算优化节点...")
    result_state2 = node_budget_optimization(test_state2)
    
    control2 = result_state2.get("_control", {})
    cost_analysis2 = result_state2.get("cost_analysis", {})
    
    print(f"\n📊 优化结果:")
    print(f"   🔄 优化尝试次数: {control2.get('budget_optimization_attempts', 0)}")
    print(f"   ✅ 预算满意: {control2.get('budget_satisfied', False)}")
    print(f"   🚨 需要人工干预: {control2.get('needs_human_intervention', False)}")
    print(f"   💰 优化后费用: {cost_analysis2.get('total_cost', 0):,}元")
    
    print("\n✅ 预算计算修复测试完成")

if __name__ == "__main__":
    test_budget_calculation()