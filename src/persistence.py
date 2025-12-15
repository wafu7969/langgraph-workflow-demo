"""
旅游规划助手 - 持久化包装器
为现有工作流提供透明的持久化功能
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from database import travel_db, generate_cache_key
from node import TravelState
from tool import query_flight_prices, query_hotel_prices, query_attractions

class PersistentTravelPlanner:
    """带持久化功能的旅游规划器"""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"travel_{uuid.uuid4().hex[:8]}"
        self.step_counter = 0
        self.cache_enabled = True
        
    async def initialize(self, user_query: str):
        """初始化会话"""
        await travel_db.init_database()
        await travel_db.create_session(self.session_id, user_query)
        print(f"🔄 会话初始化: {self.session_id}")
    
    async def save_state(self, state: TravelState, node_name: str = None):
        """保存状态到数据库"""
        try:
            self.step_counter += 1
            await travel_db.save_travel_state(self.session_id, state, self.step_counter, node_name)
            
            # 保存旅游信息
            if state.get("travel_info"):
                await travel_db.save_travel_info(self.session_id, state["travel_info"])
            
            # 保存费用分析
            if state.get("cost_analysis"):
                await travel_db.save_cost_analysis(self.session_id, state["cost_analysis"])
            
            # 保存消息
            if state.get("messages"):
                for msg in state["messages"]:
                    if isinstance(msg, (HumanMessage, AIMessage)):
                        msg_type = "human" if isinstance(msg, HumanMessage) else "ai"
                        await travel_db.save_message(self.session_id, msg_type, msg.content)
        except asyncio.CancelledError:
            print("⚠️ 数据库保存被取消（流程正常结束）")
        except Exception as e:
            print(f"❌ 保存状态失败: {e}")
    
    async def cached_query_flight_prices(self, destination: str, travel_date: str) -> Dict:
        """带缓存的航班查询"""
        params = {"destination": destination, "travel_date": travel_date}
        cache_key = generate_cache_key("flight", params)
        
        if self.cache_enabled:
            cached_result = await travel_db.get_query_cache(cache_key)
            if cached_result:
                print(f"🎯 使用缓存的航班数据: {destination}")
                return cached_result
        
        # 执行实际查询
        print(f"🔍 查询航班信息: {destination}")
        result = query_flight_prices.invoke(params)
        
        # 解析结果
        import json
        if isinstance(result, str):
            result = json.loads(result)
        
        # 保存到缓存
        if self.cache_enabled:
            await travel_db.save_query_cache(cache_key, "flight", params, result)
        
        return result
    
    async def cached_query_hotel_prices(self, destination: str, days: int, travelers: str) -> Dict:
        """带缓存的酒店查询"""
        params = {"destination": destination, "days": days, "travelers": travelers}
        cache_key = generate_cache_key("hotel", params)
        
        if self.cache_enabled:
            cached_result = await travel_db.get_query_cache(cache_key)
            if cached_result:
                print(f"🎯 使用缓存的酒店数据: {destination}")
                return cached_result
        
        # 执行实际查询
        print(f"🔍 查询酒店信息: {destination}")
        result = query_hotel_prices.invoke(params)
        
        # 解析结果
        import json
        if isinstance(result, str):
            result = json.loads(result)
        
        # 保存到缓存
        if self.cache_enabled:
            await travel_db.save_query_cache(cache_key, "hotel", params, result)
        
        return result
    
    async def cached_query_attractions(self, destination: str, days: int, requirements: list) -> Dict:
        """带缓存的景点查询"""
        params = {"destination": destination, "days": days, "requirements": requirements}
        cache_key = generate_cache_key("attractions", params)
        
        if self.cache_enabled:
            cached_result = await travel_db.get_query_cache(cache_key)
            if cached_result:
                print(f"🎯 使用缓存的景点数据: {destination}")
                return cached_result
        
        # 执行实际查询
        print(f"🔍 查询景点信息: {destination}")
        result = query_attractions.invoke(params)
        
        # 解析结果
        import json
        if isinstance(result, str):
            result = json.loads(result)
        
        # 保存到缓存
        if self.cache_enabled:
            await travel_db.save_query_cache(cache_key, "attractions", params, result)
        
        return result
    
    async def parallel_cached_query(self, travel_info: Dict[str, Any]) -> Dict[str, Any]:
        """并行执行带缓存的查询"""
        destination = travel_info.get("destination", "云南")
        days = travel_info.get("days", 5)
        travelers = travel_info.get("travelers", "2人")
        travel_date = travel_info.get("travel_date", "近期")
        requirements = travel_info.get("requirements", [])
        
        print(f"🚀 启动并行缓存查询: {destination}")
        
        # 并行执行查询
        tasks = [
            self.cached_query_flight_prices(destination, travel_date),
            self.cached_query_hotel_prices(destination, days, travelers),
            self.cached_query_attractions(destination, days, requirements)
        ]
        
        import time
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # 处理结果
        flight_info = results[0] if not isinstance(results[0], Exception) else {}
        hotel_info = results[1] if not isinstance(results[1], Exception) else {}
        attraction_info = results[2] if not isinstance(results[2], Exception) else {}
        
        print(f"⚡ 并行查询完成，耗时: {end_time - start_time:.2f}s")
        print(f"   ✈️ 机票: {flight_info.get('price', 0)}元")
        print(f"   🏨 酒店: {hotel_info.get('total_price', 0)}元")
        print(f"   🏞️ 景点: {len(attraction_info.get('attractions', []))}个")
        
        return {
            "flight": flight_info,
            "hotel": hotel_info,
            "attractions": attraction_info
        }
    
    async def finalize_session(self, final_itinerary: str, total_cost: float):
        """完成会话并保存最终结果"""
        await travel_db.update_session_completion(self.session_id, final_itinerary, total_cost)
        print(f"✅ 会话完成: {self.session_id}")
    
    async def get_session_summary(self) -> Dict:
        """获取会话摘要"""
        history = await travel_db.get_session_history(self.session_id)
        cache_stats = await travel_db.get_cache_stats()
        
        return {
            "session_id": self.session_id,
            "steps_completed": self.step_counter,
            "history": history,
            "cache_stats": cache_stats
        }
    
    async def cleanup_cache(self):
        """清理过期缓存"""
        deleted_count = await travel_db.cleanup_expired_cache()
        print(f"🧹 清理了 {deleted_count} 条过期缓存")
        return deleted_count

# 持久化节点包装器
class PersistentNodeWrapper:
    """节点持久化包装器"""
    
    def __init__(self, planner: PersistentTravelPlanner):
        self.planner = planner
    
    def wrap_node(self, node_func, node_name: str):
        """包装节点函数以添加持久化功能"""
        async def wrapped_node(state: TravelState) -> TravelState:
            print(f"💾 [持久化] 执行节点: {node_name}")
            
            # 执行原始节点函数
            if asyncio.iscoroutinefunction(node_func):
                result_state = await node_func(state)
            else:
                result_state = node_func(state)
            
            # 保存状态
            await self.planner.save_state(result_state, node_name)
            
            return result_state
        
        return wrapped_node
    
    def wrap_parallel_query_node(self, state: TravelState) -> TravelState:
        """包装并行查询节点以使用缓存"""
        async def persistent_parallel_query(state: TravelState) -> TravelState:
            print("\n" + "="*60)
            print("🔄 [持久化并行查询] 启动缓存查询")
            print("="*60)
            
            travel_info = state.get("travel_info", {})
            
            # 使用缓存查询
            query_results = await self.planner.parallel_cached_query(travel_info)
            
            # 更新状态
            messages = state.get("messages", [])
            new_state = {
                **state,
                "query_results": query_results,
                "messages": messages + [
                    AIMessage(content=f"""
                    ⚡ 持久化并行查询完成！
                    
                    📊 查询结果:
                    • ✈️ 机票：{query_results['flight'].get('price', 0)}元
                    • 🏨 酒店：{query_results['hotel'].get('total_price', 0)}元  
                    • 🏞️ 景点：{len(query_results['attractions'].get('attractions', []))}个推荐
                    
                    💾 数据已保存到数据库
                    📋 开始预算评估...
                    """)
                ]
            }
            
            # 保存状态
            await self.planner.save_state(new_state, "persistent_parallel_query")
            
            return new_state
        
        return asyncio.run(persistent_parallel_query(state))

# 工具函数
async def create_persistent_planner(user_query: str, session_id: str = None) -> PersistentTravelPlanner:
    """创建持久化旅游规划器"""
    planner = PersistentTravelPlanner(session_id)
    await planner.initialize(user_query)
    return planner

async def resume_session(session_id: str) -> tuple[PersistentTravelPlanner, Optional[Dict]]:
    """恢复中断的会话
    
    Returns:
        tuple: (planner, latest_state) - 规划器实例和最新状态
    """
    # 创建规划器实例
    planner = PersistentTravelPlanner(session_id)
    await travel_db.init_database()
    
    # 获取最新状态
    latest_state_info = await travel_db.get_latest_state(session_id)
    
    if latest_state_info:
        # 恢复步骤计数器
        planner.step_counter = latest_state_info['step_number']
        
        print(f"🔄 恢复会话: {session_id}")
        print(f"📊 最新步骤: {latest_state_info['step_number']}")
        print(f"🎯 最新节点: {latest_state_info['node_name']}")
        print(f"⏰ 最后更新: {latest_state_info['created_at']}")
        
        return planner, latest_state_info['state_data']
    else:
        print(f"❌ 未找到会话 {session_id} 的状态数据")
        return planner, None

async def list_resumable_sessions() -> List[Dict]:
    """列出可恢复的会话"""
    await travel_db.init_database()
    sessions = await travel_db.list_active_sessions()
    
    print(f"\n📋 可恢复的会话列表 ({len(sessions)}个):")
    print("=" * 80)
    
    for i, session in enumerate(sessions, 1):
        status = "✅ 已完成" if session['is_completed'] else "🔄 进行中"
        print(f"{i}. 会话ID: {session['session_id']}")
        print(f"   📝 用户需求: {session['user_query'][:50]}...")
        print(f"   📊 执行步骤: {session['latest_step']}")
        print(f"   🎯 最新节点: {session['latest_node']}")
        print(f"   📅 创建时间: {session['created_at']}")
        print(f"   🔄 更新时间: {session['updated_at']}")
        print(f"   📋 状态: {status}")
        print("-" * 80)
    
    return sessions

def enable_persistence_for_workflow(workflow, planner: PersistentTravelPlanner):
    """为工作流启用持久化功能"""
    wrapper = PersistentNodeWrapper(planner)
    
    # 这里可以添加更多的节点包装逻辑
    # 例如：替换原有的并行查询节点
    print("🔧 为工作流启用持久化功能")
    
    return wrapper

# 示例使用
async def demo_persistence():
    """演示持久化功能"""
    print("🚀 持久化功能演示")
    
    # 创建持久化规划器
    planner = await create_persistent_planner("我想去日本旅游5天，预算1万元")
    
    # 模拟查询
    travel_info = {
        "destination": "日本",
        "days": 5,
        "budget": 10000,
        "travel_date": "2024年春季",
        "travelers": "2人",
        "requirements": ["温泉", "美食"]
    }
    
    # 执行并行查询
    results = await planner.parallel_cached_query(travel_info)
    print(f"查询结果: {results}")
    
    # 获取会话摘要
    summary = await planner.get_session_summary()
    print(f"会话摘要: {summary}")
    
    # 完成会话
    await planner.finalize_session("详细行程表...", 8500.0)

if __name__ == "__main__":
    asyncio.run(demo_persistence())