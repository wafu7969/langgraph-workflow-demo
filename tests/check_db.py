"""检查数据库中的持久化数据"""

import asyncio
import aiosqlite
import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import travel_db

async def check_database():
    """检查数据库中的数据"""
    print("🔍 检查数据库中的持久化数据...")
    
    # 初始化数据库连接
    await travel_db.init_database()
    
    async with aiosqlite.connect(travel_db.db_path) as db:
        # 检查会话数据
        print("\n📊 旅游会话数据:")
        async with db.execute("SELECT * FROM travel_sessions ORDER BY created_at DESC LIMIT 5") as cursor:
            sessions = await cursor.fetchall()
            for session in sessions:
                print(f"  会话ID: {session[1]}")
                print(f"  查询: {session[2]}")
                print(f"  状态: {session[5]}")
                print(f"  总费用: {session[7]}元")
                print(f"  创建时间: {session[8]}")
                print("  " + "-"*50)
        
        # 检查状态数据
        print("\n💾 状态保存数据:")
        async with db.execute("SELECT COUNT(*) FROM travel_states") as cursor:
            count = await cursor.fetchone()
            print(f"  总状态记录数: {count[0]}")
        
        # 检查缓存数据
        print("\n🎯 查询缓存数据:")
        async with db.execute("SELECT query_type, COUNT(*) FROM query_cache GROUP BY query_type") as cursor:
            cache_data = await cursor.fetchall()
            for cache_type, count in cache_data:
                print(f"  {cache_type}: {count}条缓存")
        
        # 检查消息数据
        print("\n💬 消息记录数据:")
        async with db.execute("SELECT COUNT(*) FROM message_history") as cursor:
            count = await cursor.fetchone()
            print(f"  总消息记录数: {count[0]}")
        
        # 获取缓存统计
        cache_stats = await travel_db.get_cache_stats()
        print(f"\n📈 缓存统计:")
        print(f"  总缓存数: {cache_stats['total_cache']}")
        print(f"  缓存命中数: {cache_stats['total_hits']}")
        print(f"  活跃缓存数: {cache_stats['active_cache']}")
        print(f"  过期缓存数: {cache_stats['expired_cache']}")

if __name__ == "__main__":
    asyncio.run(check_database())