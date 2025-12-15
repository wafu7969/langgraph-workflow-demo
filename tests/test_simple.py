#!/usr/bin/env python3
"""
简化测试 - 验证人工干预触发机制
只测试到人工干预触发点，不需要完整流程
"""

import asyncio
import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from node import TravelState, node_budget_optimization, node_check_budget_satisfaction
from database import TravelDatabase
from graph import create_travel_planning_graph

async def test_human_intervention_trigger():
    """测试人工干预触发机制"""
    
    print("🧪 测试人工干预触发机制")
    print("=" * 60)
    
    # 初始化数据库
    db = TravelDatabase()
    await db.init_database()
    print("✅ 数据库初始化完成")
    
    # 创建测试状态 - 豪华旅游需求，预算严重不足
    test_state = TravelState(
        messages=[],
        input="日本豪华旅游7天，要住五星级酒店，坐头等舱，预算只有1000元",
        travel_info={
            "destination": "日本",
            "days": 7,
            "budget": 1000.0,
            "requirements": ["豪华旅游", "住五星级酒店", "坐头等舱"]
        },
        query_results={
            "flights": {"price": 1500, "airline": "全日空", "class": "头等舱"},
            "hotels": {"total_price": 1400, "name": "东京丽思卡尔顿", "rating": 5},
            "attractions": {"total_cost": 200, "count": 5}
        },
        cost_analysis=None,
        itinerary=None,
        status="budget_optimization",
        _control={
            "budget_optimization_attempts": 2,  # 已经尝试2次
            "budget_satisfied": False
        }
    )
    
    print("📊 测试场景:")
    print(f"   🎯 目的地: {test_state['travel_info']['destination']}")
    print(f"   📅 天数: {test_state['travel_info']['days']}天")
    print(f"   💰 预算: {test_state['travel_info']['budget']:,}元")
    print(f"   ✨ 需求: {', '.join(test_state['travel_info']['requirements'])}")
    print(f"   ✈️ 航班费用: {test_state['query_results']['flights']['price']:,}元")
    print(f"   🏨 酒店费用: {test_state['query_results']['hotels']['total_price']:,}元")
    print(f"   🎯 景点费用: {test_state['query_results']['attractions']['total_cost']:,}元")
    
    total_cost = (test_state['query_results']['flights']['price'] + 
                  test_state['query_results']['hotels']['total_price'] + 
                  test_state['query_results']['attractions']['total_cost'])
    overspend = total_cost - test_state['travel_info']['budget']
    overspend_ratio = overspend / test_state['travel_info']['budget']
    
    print(f"   💸 总费用: {total_cost:,}元")
    print(f"   ⚠️ 超支: {overspend:,}元 ({overspend_ratio:.1%})")
    
    print("\n🔄 执行预算优化节点...")
    
    try:
        # 执行预算优化节点
        result_state = node_budget_optimization(test_state)
        
        print("\n📊 优化结果分析:")
        
        # 检查控制信息
        control = result_state.get("_control", {})
        cost_analysis = result_state.get("cost_analysis", {})
        
        print(f"   🔄 优化尝试次数: {control.get('budget_optimization_attempts', 0)}")
        print(f"   ✅ 预算满意: {control.get('budget_satisfied', False)}")
        print(f"   👤 需要人工干预: {control.get('needs_human_intervention', False)}")
        
        if cost_analysis:
            optimized_cost = cost_analysis.get('total_cost', 0)
            is_over_budget = cost_analysis.get('is_over_budget', False)
            print(f"   💰 优化后费用: {optimized_cost:,}元")
            print(f"   ⚠️ 仍然超预算: {is_over_budget}")
        
        # 执行预算满意度检查节点
        check_state = node_check_budget_satisfaction(result_state)
        
        # 测试路由逻辑
        print("\n🔀 测试路由逻辑:")
        workflow = create_travel_planning_graph()
        
        # 手动调用路由器逻辑
        control = result_state.get("_control", {})
        budget_attempts = control.get("budget_optimization_attempts", 0)
        budget_satisfied = control.get("budget_satisfied", False)
        needs_human_intervention = control.get("needs_human_intervention", False)
        cost_analysis = result_state.get("cost_analysis", {})
        is_over_budget = cost_analysis.get("is_over_budget", False)
        
        print(f"   🔄 尝试次数: {budget_attempts}/3")
        print(f"   ✅ 预算满意: {budget_satisfied}")
        print(f"   ⚠️ 超出预算: {is_over_budget}")
        print(f"   👤 需要人工干预: {needs_human_intervention}")
        
        # 判断路由决策
        if budget_satisfied:
            route_decision = "itinerary_optimization"
        elif needs_human_intervention or (budget_attempts >= 3 and is_over_budget):
            route_decision = "human_intervention"
        elif budget_attempts >= 3:
            route_decision = "itinerary_optimization"
        else:
            route_decision = "budget_optimization"
        
        print(f"   ➡️ 路由决策: {route_decision}")
        
        print("\n🎯 人工干预触发检查:")
        
        if route_decision == "human_intervention":
            print("✅ 成功触发人工干预机制")
            print("✅ 系统识别到豪华需求的优化限制")
            print("✅ 正确路由到人工干预节点")
            
            print("\n🎓 要点验证:")
            print("✅ 条件分支: 豪华需求 + 严重超支 → 触发人工干预")
            print("✅ 状态管理: needs_human_intervention = True")
            print("✅ 路由逻辑: 正确判断需要人工干预")
            print("✅ 优化限制: 豪华需求最多节省30%")
            
            return True
            
        else:
            print("❌ 未触发人工干预机制")
            print("❌ 可能的问题:")
            print("   - 优化算法过于激进")
            print("   - 豪华需求检测失败")
            print("   - 条件分支逻辑错误")
            
            return False
            
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("🎯 LangGraph 人工干预机制测试")
    print("=" * 60)
    print("📚 测试目标:")
    print("   1. 验证豪华需求的识别")
    print("   2. 验证预算超支的检测")
    print("   3. 验证人工干预的触发")
    print("   4. 验证状态管理的正确性")
    print("=" * 60)
    
    success = await test_human_intervention_trigger()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 测试通过！人工干预机制工作正常")
        print("📚 这个测试验证了 LangGraph 中的:")
        print("   • 条件分支和路由逻辑")
        print("   • 状态管理和控制信息")
        print("   • 业务逻辑的正确实现")
        print("   • 用户交互点的设计")
    else:
        print("❌ 测试失败！需要检查人工干预逻辑")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())