#!/usr/bin/env python3
"""
中断恢复功能测试脚本
"""

import asyncio
import sys
import os

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from persistence import list_resumable_sessions

async def test_recovery_features():
    """测试恢复功能的各个组件"""
    
    print("🧪 中断恢复功能测试")
    print("=" * 60)
    
    # 测试1: 数据库连接和会话列表
    print("\n📋 测试1: 检查可恢复的会话")
    try:
        sessions = await list_resumable_sessions()
        if sessions:
            print(f"✅ 找到 {len(sessions)} 个可恢复的会话")
            
            # 显示第一个会话的详细信息
            first_session = sessions[0]
            print(f"\n📝 第一个会话详情:")
            print(f"   🆔 会话ID: {first_session['session_id']}")
            print(f"   📝 用户需求: {first_session['user_query'][:50]}...")
            print(f"   📊 执行步骤: {first_session['latest_step']}")
            print(f"   🎯 最新节点: {first_session['latest_node']}")
            print(f"   📅 创建时间: {first_session['created_at']}")
        else:
            print("❌ 没有找到可恢复的会话")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    # 测试2: 数据库状态恢复
    print(f"\n🔄 测试2: 检查状态恢复功能")
    try:
        from database import TravelDatabase
        
        travel_db = TravelDatabase()
        await travel_db.init_database()
        
        if sessions:
            session_id = sessions[0]['session_id']
            latest_state = await travel_db.get_latest_state(session_id)
            
            if latest_state:
                print(f"✅ 成功恢复状态数据")
                print(f"   📊 步骤编号: {latest_state['step_number']}")
                print(f"   🎯 节点名称: {latest_state['node_name']}")
                print(f"   📅 创建时间: {latest_state['created_at']}")
                
                # 检查状态数据结构
                state_data = latest_state['state_data']
                if 'messages' in state_data:
                    print(f"   💬 消息数量: {len(state_data['messages'])}")
                if 'user_query' in state_data:
                    print(f"   📝 用户查询: {state_data['user_query'][:30]}...")
                if 'status' in state_data:
                    print(f"   📊 当前状态: {state_data['status']}")
            else:
                print(f"❌ 无法恢复会话 {session_id} 的状态")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    # 测试3: 恢复接口
    print(f"\n🔧 测试3: 检查恢复接口")
    try:
        from persistence import resume_session
        
        if sessions:
            session_id = sessions[0]['session_id']
            planner, state = await resume_session(session_id)
            
            if state:
                print(f"✅ 恢复接口正常工作")
                print(f"   📊 步骤计数器: {planner.step_counter}")
                print(f"   🆔 会话ID: {planner.session_id}")
                print(f"   📝 状态键: {list(state.keys())}")
            else:
                print(f"❌ 恢复接口返回空状态")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print(f"\n✅ 测试完成！")

def main():
    """主函数"""
    asyncio.run(test_recovery_features())

if __name__ == "__main__":
    main()