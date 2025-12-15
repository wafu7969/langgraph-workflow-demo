"""测试人工干预功能 - 预算不足场景"""

import asyncio
import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import run_travel_planning

async def test_budget_insufficient():
    """测试预算不足时的人工干预流程"""
    print("🧪 开始测试预算不足时的人工干预流程")
    print("="*80)
    
    # 使用一个明显预算不足的查询 - 豪华旅游但预算很少
    test_query = "日本豪华旅游7天，要住五星级酒店，坐头等舱，预算只有1000元"
    
    print(f"📝 测试查询: {test_query}")
    print("💡 预期结果: 预算严重不足，应该触发人工干预")
    print("="*80)
    
    try:
        # 运行旅游规划，启用交互模式和持久化
        await run_travel_planning(
            user_query=test_query,
            interactive=True,  # 启用交互模式以测试人工干预
            enable_persistence=True
        )
        
        print("\n✅ 测试完成")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_budget_insufficient())