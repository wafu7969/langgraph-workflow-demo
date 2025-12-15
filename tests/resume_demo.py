#!/usr/bin/env python3
"""
中断恢复功能演示脚本
"""

import asyncio
import sys
import os

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from main import run_travel_planning, resume_travel_planning, interactive_resume
from persistence import list_resumable_sessions

async def demo_resume_functionality():
    """演示中断恢复功能"""
    
    print("🎯 中断恢复功能演示")
    print("=" * 60)
    
    # 1. 列出可恢复的会话
    print("\n📋 步骤1: 查看可恢复的会话")
    sessions = await list_resumable_sessions()
    
    if not sessions:
        print("\n📭 没有找到可恢复的会话")
        print("💡 建议：先运行一次正常的旅游规划，然后中断它")
        print("   命令：python src/main.py")
        return
    
    # 2. 选择一个会话进行恢复
    print(f"\n🔧 步骤2: 自动选择第一个会话进行恢复")
    first_session = sessions[0]
    session_id = first_session['session_id']
    
    print(f"✅ 选择会话: {session_id}")
    print(f"📝 用户需求: {first_session['user_query']}")
    print(f"📊 当前步骤: {first_session['latest_step']}")
    print(f"🎯 最新节点: {first_session['latest_node']}")
    
    # 3. 恢复执行
    print(f"\n🚀 步骤3: 开始恢复执行")
    await resume_travel_planning(session_id, interactive=False)
    
    print(f"\n✅ 恢复演示完成！")

async def create_test_session():
    """创建一个测试会话用于演示恢复"""
    print("🔧 创建测试会话...")
    
    # 运行一个简短的旅游规划（会自动保存状态）
    user_query = "我想去北京旅游3天，预算5000元"
    
    try:
        # 运行几步后会自动保存状态
        await run_travel_planning(user_query, interactive=False, enable_persistence=True)
    except Exception as e:
        print(f"⚠️ 测试会话创建过程中出现异常（这是正常的）: {e}")
    
    print("✅ 测试会话已创建")

def main():
    """主函数"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "create":
            print("🔧 创建测试会话模式")
            asyncio.run(create_test_session())
        elif sys.argv[1] == "interactive":
            print("🎮 交互式恢复模式")
            asyncio.run(interactive_resume())
        elif sys.argv[1] == "demo":
            print("🎯 自动演示模式")
            asyncio.run(demo_resume_functionality())
        else:
            print("❌ 未知参数")
            print_usage()
    else:
        print_usage()

def print_usage():
    """打印使用说明"""
    print("🎯 中断恢复功能演示")
    print("=" * 50)
    print("使用方法:")
    print("  python resume_demo.py create      # 创建测试会话")
    print("  python resume_demo.py demo        # 自动演示恢复功能")
    print("  python resume_demo.py interactive # 交互式选择恢复")
    print("")
    print("💡 建议执行顺序:")
    print("  1. python resume_demo.py create")
    print("  2. python resume_demo.py demo")
    print("  3. python resume_demo.py interactive")

if __name__ == "__main__":
    main()