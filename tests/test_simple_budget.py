#!/usr/bin/env python3
"""
简化的预算确认测试 - 跳过复杂的并行查询
"""

import asyncio
import sys
import os

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from node import node_human_intervention
from langchain_core.messages import HumanMessage, AIMessage

async def test_simple_budget_confirmation():
    """测试简化的预算确认流程"""
    
    print("🧪 测试简化的预算确认功能")
    print("=" * 60)
    
    # 创建一个模拟的状态，直接包含预算超支的情况
    test_state = {
        "messages": [
            HumanMessage(content="我想去欧洲豪华旅游15天，预算1000元")
        ],
        "travel_info": {
            "destination": "欧洲",
            "days": 15,
            "budget": 1000,
            "travelers": "2人",
            "requirements": ["豪华", "五星级酒店"]
        },
        "cost_analysis": {
            "total_cost": 25000,  # 明显超支
            "budget": 1000,
            "flight_cost": 15000,
            "hotel_cost": 8000,
            "other_cost": 2000
        },
        "_control": {
            "needs_human_intervention": True,
            "budget_optimization_attempts": 3
        },
        "status": "waiting_confirmation"
    }
    
    print(f"📝 测试场景: 欧洲豪华旅游15天，预算1000元")
    print(f"💰 实际费用: 25000元")
    print(f"📊 超支比例: {(25000-1000)/1000*100:.1f}%")
    print("🎯 预期结果: 触发人工干预，要求用户确认")
    
    try:
        # 调用人工干预节点
        result_state = node_human_intervention(test_state)
        
        print("\n✅ 人工干预节点测试完成")
        print(f"📊 返回状态: {result_state.get('status')}")
        print(f"🎮 控制信息: {result_state.get('_control', {})}")
        
        # 检查是否正确设置了等待确认状态
        if result_state.get("status") == "waiting_confirmation":
            print("✅ 成功设置等待确认状态")
            
            control = result_state.get("_control", {})
            if control.get("waiting_confirmation"):
                print("✅ 成功设置等待确认标志")
            
            if control.get("suggestions"):
                print(f"✅ 成功生成优化建议: {len(control['suggestions'])}条")
                for i, suggestion in enumerate(control["suggestions"], 1):
                    print(f"   {i}. {suggestion}")
            
            # 检查消息是否包含用户选择提示
            messages = result_state.get("messages", [])
            if messages:
                last_message = messages[-1]
                if isinstance(last_message, AIMessage) and "请选择您的决策" in last_message.content:
                    print("✅ 成功生成用户决策提示")
                    print("✅ 预算确认功能正常工作")
                else:
                    print("❌ 未生成正确的用户决策提示")
            else:
                print("❌ 未生成任何消息")
        else:
            print(f"❌ 状态不正确: {result_state.get('status')}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_budget_confirmation())