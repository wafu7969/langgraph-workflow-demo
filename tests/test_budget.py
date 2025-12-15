#!/usr/bin/env python3
"""
测试预算确认和人工干预功能
"""

import asyncio
import sys
import os

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from main import run_travel_planning

async def test_budget_confirmation():
    """测试预算不足的确认流程"""
    
    print("🧪 测试预算确认功能")
    print("=" * 60)
    
    # 测试一个明显预算不足的场景
    user_query = "我想去欧洲豪华旅游15天，预算1000元"
    
    print(f"📝 测试查询: {user_query}")
    print("🎯 预期结果: 系统应该检测到预算不足并要求用户确认")
    
    try:
        await run_travel_planning(user_query, interactive=False, enable_persistence=True)
    except Exception as e:
        print(f"⚠️ 测试过程中出现异常: {e}")
    
    print("✅ 预算确认测试完成")

if __name__ == "__main__":
    asyncio.run(test_budget_confirmation())