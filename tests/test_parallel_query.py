#!/usr/bin/env python3
"""测试修复后的并行查询功能"""

import asyncio
import sys
import os

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from node import node_parallel_query
from langchain_core.messages import HumanMessage

async def test_parallel_query():
    """测试并行查询功能"""
    print("🧪 测试并行查询功能...")
    
    # 创建测试状态
    test_state = {
        "messages": [HumanMessage(content="我想去云南旅游5天，预算5000元")],
        "travel_info": {
            "destination": "云南",
            "days": 5,
            "budget": 5000,
            "travelers": "2人",
            "travel_date": "近期",
            "requirements": ["自然风光", "文化体验"]
        },
        "status": "processing"
    }
    
    try:
        # 执行并行查询
        result_state = await node_parallel_query(test_state)
        
        print("\n✅ 并行查询测试成功!")
        print(f"状态: {result_state.get('status', 'unknown')}")
        
        query_results = result_state.get("query_results", {})
        print(f"查询结果: {query_results}")
        
        # 检查结果完整性
        if "flight" in query_results and "hotel" in query_results and "attractions" in query_results:
            print("✅ 所有查询结果都已获取")
        else:
            print("⚠️ 部分查询结果缺失")
            
        return True
        
    except Exception as e:
        print(f"❌ 并行查询测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_parallel_query())
    if success:
        print("\n🎉 并行查询修复成功!")
    else:
        print("\n💥 并行查询仍有问题")