"""
旅游规划助手 - 节点模块
包含所有LangGraph节点函数
"""

from time import sleep
from typing import TypedDict, Annotated, Sequence, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages
import json
from common import (
    get_llm, extract_travel_info, parse_value, get_travel_info, 
    set_travel_info, get_daily_expense
)

# ==================== State 定义 ====================
class TravelState(TypedDict):
    """旅游规划状态"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    input: Optional[str]  # 用户输入查询
    travel_info: Optional[Dict[str, Any]]  # 旅行基本信息：destination, days, budget, travel_date, travelers, requirements
    query_results: Optional[Dict[str, Any]]  # 合并所有查询结果
    cost_analysis: Optional[Dict[str, Any]]  # 合并成本分析
    itinerary: Optional[str]  # 生成的行程
    status: str  # 当前状态
    _control: Optional[Dict[str, Any]]  # 流程控制字段
    # 并行查询结果键
    flight_info: Optional[Dict[str, Any]]  # 航班查询结果
    hotel_info: Optional[Dict[str, Any]]  # 酒店查询结果
    attractions_info: Optional[Dict[str, Any]]  # 景点查询结果

# ==================== 辅助函数 ====================
def check_state(state: TravelState, node_name: str) -> TravelState:
    """检查状态是否有效，如果无效则返回错误状态"""
    if state is None:
        print(f"❌ 错误：{node_name} 节点收到空状态")
        return TravelState(
            messages=[],
            input="",
            travel_info=None,
            query_results=None,
            cost_analysis=None,
            itinerary=None,
            status="error",
            _control=None
        )
    return state


def node_write_itinerary_file(state: TravelState) -> TravelState:
    """📝 写入行程文件节点 - 使用ToolNode调用写入工具"""
    print("\n" + "="*60)
    print("📚 [示例-ToolNode] 📝 写入行程文件")
    print("="*60)
    
    # 检查状态有效性
    state = check_state(state, "写入行程文件")
    if state.get("status") == "error":
        return state
    
    itinerary = state.get("itinerary", "")
    travel_info = state.get("travel_info", {})
    destination = travel_info.get("destination", "旅游")
    days = travel_info.get("days", 1)
    
    if not itinerary:
        print("❌ 没有找到行程内容，无法写入文件")
        return state
    
    print(f"📋 准备写入行程文件...")
    print(f"🌍 目的地: {destination}")
    print(f"📅 天数: {days}天")
    print(f"📄 行程长度: {len(itinerary)}字符")
    
    # 生成文件写入工具调用
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{destination}_{days}天行程_{timestamp}"
    
    # 创建带有工具调用的AIMessage
    tool_call = {
        "id": f"write_file_{timestamp}",
        "name": "write_itinerary_to_file",
        "args": {
            "itinerary_content": itinerary,
            "filename": filename
        }
    }
    
    messages = state.get("messages", [])
    ai_message_with_tool = AIMessage(
        content="📝 正在将行程保存到文件...",
        tool_calls=[tool_call]
    )
    
    print("🔧 生成工具调用指令...")
    print(f"🛠️ 工具名称: write_itinerary_to_file")
    print(f"📁 文件名: {filename}.txt")
    print("✅ 工具调用准备完成，等待ToolNode执行...")
    
    return {
        **state,
        "messages": messages + [ai_message_with_tool]
    }

# ==================== 节点函数 ====================
def node_parse_intent(state: TravelState) -> TravelState:
    """解析用户意图"""
    print("\n👉 [解析意图]")
    print("🔍 正在分析用户需求...")
    
    # 检查状态有效性
    state = check_state(state, "解析意图")
    if state.get("status") == "error":
        return state
    
    control = state.get("_control", {}) or {}
    llm = get_llm()
    
    # 首次解析
    if not control.get("parsed_attempted"):
        user_query = state.get("input", "")
        print("🤖 使用AI模型解析旅游需求...")
        parsed = extract_travel_info(user_query, llm)
        print(f"📝 解析结果: {parsed}")
        print("✅ 需求解析完成")
        
        required_fields = ["destination", "days", "budget"]
        missing = [f for f in required_fields if parsed.get(f) == "未提供"]
        
        if missing:
            prompt_map = {
                "destination": "请问您想去哪里旅游？",
                "days": "请问您计划旅游几天？",
                "budget": "请问您的预算是多少元？"
            }
            prompts = [prompt_map[f] for f in missing if f in prompt_map]
            
            return {
                **state,
                "_control": {"parsed_attempted": True, "waiting_input": True, "missing": missing, "parsed": parsed},
                "status": "collecting_info",
                "messages": state["messages"] + [AIMessage(content=f"📋 需要补充信息：\n" + "\n".join(prompts))]
            }
        
        return process_complete_info(state, parsed)
    
    # 处理补充信息
    elif control.get("waiting_input"):
        last_msg = state["messages"][-1]
        if isinstance(last_msg, HumanMessage):
            user_input = last_msg.content.strip()
            if user_input.lower() in ["跳过", "skip"]:
                return apply_defaults(state)
            
            # 更新解析结果
            parsed = control.get("parsed", {})
            missing = control.get("missing", [])
            
            if missing and user_input:
                # 填充第一个缺失的字段
                first_missing = missing[0]
                parsed[first_missing] = user_input
                print(f"✅ 已收集 {first_missing}: {user_input}")
                
                # 重新检查是否还有缺失信息
                return process_complete_info(state, parsed)
    
    return state

def process_complete_info(state: TravelState, parsed: dict) -> TravelState:
    """处理完整信息"""
    # 验证必需信息是否完整
    required_fields = ["destination", "days", "budget"]
    missing = [f for f in required_fields if not parsed.get(f) or parsed.get(f) == "未提供"]
    
    if missing:
        # 如果还有缺失信息，返回收集状态
        prompt_map = {
            "destination": "请问您想去哪里旅游？",
            "days": "请问您计划旅游几天？",
            "budget": "请问您的预算是多少元？"
        }
        prompts = [prompt_map[f] for f in missing if f in prompt_map]
        
        return {
            **state,
            "_control": {"parsed_attempted": True, "waiting_input": True, "missing": missing, "parsed": parsed},
            "status": "collecting_info",
            "messages": state["messages"] + [AIMessage(content=f"📋 还需要补充信息：\n" + "\n".join(prompts))]
        }
    
    # 所有必需信息都有了，处理数据
    destination = parsed["destination"]
    days = parse_value(parsed["days"], 5)
    budget = parse_value(parsed["budget"], 5000, is_float=True)
    
    travel_info = {
        "destination": destination,
        "days": days,
        "budget": budget,
        "travel_date": parsed.get("travel_date", "近期"),
        "travelers": parsed.get("travelers", "2人"),
        "requirements": parsed.get("requirements", [])
    }
    
    return {
        **state,
        "travel_info": travel_info,
        "_control": {"parsed_attempted": True, "waiting_input": False},
        "status": "planning",
        "messages": state["messages"] + [AIMessage(content=f"✅ 信息收集完成！目的地：{destination}，{days}天，预算{budget}元")]
    }

def apply_defaults(state: TravelState) -> TravelState:
    """应用默认值"""
    return process_complete_info(state, {"destination": "云南", "days": 5, "budget": 5000})

async def node_parallel_query(state: TravelState) -> TravelState:
    """真正的并行查询节点 - 使用asyncio.gather实现并发执行"""
    print("\n" + "="*60)
    print("🔄 [节点B] 并行查询 (真正并发)")
    print("="*60)
    
    # 检查状态有效性
    state = check_state(state, "并行查询")
    if state.get("status") == "error":
        return state
    
    # 获取旅游信息
    travel_info = state.get("travel_info", {})
    destination = travel_info.get("destination", "云南")
    days = travel_info.get("days", 5)
    travelers = travel_info.get("travelers", "2人")
    travel_date = travel_info.get("travel_date", "近期")
    requirements = travel_info.get("requirements", [])
    
    print(f"📋 查询参数: {destination}, {days}天, {travelers}")
    print("🚀 启动并行查询...")
    
    # 导入工具函数
    from tool import query_flight_prices, query_hotel_prices, query_attractions
    import asyncio
    import time
    
    # 定义异步执行函数
    async def execute_tool_async(tool_func, args, tool_name, timeout=30):
        """异步执行工具函数，带超时处理"""
        try:
            print(f"   🔍 开始查询 {tool_name}...")
            start_time = time.time()
            
            # 如果工具函数不是异步的，在线程池中执行
            import concurrent.futures
            loop = asyncio.get_event_loop()
            
            # 添加超时处理
            async def run_with_timeout():
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    return await loop.run_in_executor(executor, tool_func.invoke, args)
            
            try:
                result = await asyncio.wait_for(run_with_timeout(), timeout=timeout)
            except asyncio.TimeoutError:
                print(f"   ⏰ {tool_name} 查询超时 ({timeout}s)")
                return {"tool_name": tool_name, "error": f"查询超时 ({timeout}s)", "success": False}
            except asyncio.CancelledError:
                print(f"   🚫 {tool_name} 查询被取消")
                return {"tool_name": tool_name, "error": "查询被取消", "success": False}
            
            end_time = time.time()
            print(f"   ✅ {tool_name} 查询完成 ({end_time - start_time:.2f}s)")
            return {"tool_name": tool_name, "result": result, "success": True}
            
        except Exception as e:
            print(f"   ❌ {tool_name} 查询失败: {e}")
            return {"tool_name": tool_name, "error": str(e), "success": False}
    
    # 准备并行任务
    tasks = [
        execute_tool_async(
            query_flight_prices, 
            {"destination": destination, "travel_date": travel_date},
            "航班信息"
        ),
        execute_tool_async(
            query_hotel_prices,
            {"destination": destination, "days": days, "travelers": travelers},
            "酒店信息"
        ),
        execute_tool_async(
            query_attractions,
            {"destination": destination, "days": days, "requirements": requirements},
            "景点信息"
        )
    ]
    
    # 并行执行所有查询
    print("⚡ 并发执行3个查询任务...")
    start_time = time.time()
    
    try:
        # 使用 asyncio.gather 并设置总体超时
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=60  # 总体超时60秒
        )
    except asyncio.TimeoutError:
        print("⏰ 并行查询总体超时，使用默认数据")
        results = [
            {"tool_name": "航班信息", "error": "查询超时", "success": False},
            {"tool_name": "酒店信息", "error": "查询超时", "success": False},
            {"tool_name": "景点信息", "error": "查询超时", "success": False}
        ]
    except Exception as e:
        print(f"⚠️ 并行查询异常: {e}")
        results = [
            {"tool_name": "航班信息", "error": str(e), "success": False},
            {"tool_name": "酒店信息", "error": str(e), "success": False},
            {"tool_name": "景点信息", "error": str(e), "success": False}
        ]
    
    end_time = time.time()
    print(f"🎯 所有查询完成，总耗时: {end_time - start_time:.2f}s")
    
    # 处理结果
    flight_info = {}
    hotel_info = {}
    attraction_info = {}
    
    for result in results:
        if isinstance(result, Exception):
            print(f"⚠️ 查询异常: {result}")
            continue
            
        if result["success"]:
            tool_name = result["tool_name"]
            data = result["result"]
            
            if tool_name == "航班信息":
                flight_info = json.loads(data) if isinstance(data, str) else data
            elif tool_name == "酒店信息":
                hotel_info = json.loads(data) if isinstance(data, str) else data
            elif tool_name == "景点信息":
                attraction_info = json.loads(data) if isinstance(data, str) else data
        else:
            print(f"⚠️ {result['tool_name']} 查询失败: {result.get('error', '未知错误')}")
    
    # 如果查询失败，使用默认数据
    if not flight_info:
        flight_info = {"price": 2000, "airline": "默认航空", "flight_time": "2小时"}
        print("   📝 使用默认航班信息")
    
    if not hotel_info:
        hotel_info = {"total_price": 1500, "hotel_name": "默认酒店", "rating": "4星"}
        print("   📝 使用默认酒店信息")
    
    if not attraction_info:
        attraction_info = {"attractions": [{"name": "默认景点", "price": 100}]}
        print("   📝 使用默认景点信息")
    
    # 合并查询结果
    query_results = {
        "flight": flight_info,
        "hotel": hotel_info,
        "attractions": attraction_info
    }
    
    print("✅ 并行查询结果汇总:")
    print(f"   ✈️ 机票: {flight_info.get('price', 0)}元")
    print(f"   🏨 酒店: {hotel_info.get('total_price', 0)}元")
    print(f"   🏞️ 景点: {len(attraction_info.get('attractions', []))}个")
    
    messages = state.get("messages", [])
    
    return {
        **state,
        "query_results": query_results,
        "messages": messages + [
            AIMessage(content=f"""
            ⚡ 并行查询完成！(耗时: {end_time - start_time:.2f}s)
            
            📊 查询结果:
            • ✈️ 机票：{flight_info.get('price', 0)}元
            • 🏨 酒店：{hotel_info.get('total_price', 0)}元  
            • 🏞️ 景点：{len(attraction_info.get('attractions', []))}个推荐
            
            📋 开始预算评估...
            """)
        ]
    }

def node_prepare_parallel(state: TravelState) -> TravelState:
    """准备并行查询参数 (保留兼容性)"""
    print("\n" + "="*60)
    print("🔄 [节点B] 准备并行查询")
    print("="*60)
    
    # 检查状态有效性
    state = check_state(state, "准备并行查询")
    if state.get("status") == "error":
        return state
    
    # 获取旅游信息
    travel_info = state.get("travel_info", {})
    destination = travel_info.get("destination", "云南")
    days = travel_info.get("days", 5)
    travelers = travel_info.get("travelers", "2人")
    travel_date = travel_info.get("travel_date", "近期")
    requirements = travel_info.get("requirements", [])
    
    print(f"📋 查询参数: {destination}, {days}天, {travelers}")
    
    # 生成工具调用
    tool_calls = [
        {
            "id": "flight_call_1",
            "name": "query_flight_prices",
            "args": {
                "destination": destination,
                "travel_date": travel_date
            }
        },
        {
            "id": "hotel_call_1", 
            "name": "query_hotel_prices",
            "args": {
                "destination": destination,
                "days": days,
                "travelers": travelers
            }
        },
        {
            "id": "attraction_call_1",
            "name": "query_attractions", 
            "args": {
                "destination": destination,
                "days": days,
                "requirements": requirements
            }
        }
    ]
    
    messages = state.get("messages", [])
    
    # 创建带有工具调用的AIMessage
    ai_message = AIMessage(
        content="📡 开始并行查询机票、酒店、景点信息...",
        tool_calls=tool_calls
    )
    
    return {
        **state,
        "messages": messages + [ai_message]
    }

async def node_query_flights(state: TravelState) -> TravelState:
    """查询航班信息节点 - LangGraph原生并行 (异步版本)"""
    print("✈️ [并行节点1] 查询航班信息")
    
    # 调试：打印完整状态
    print(f"🔍 调试 - 完整状态键: {list(state.keys())}")
    
    # 从travel_info中获取解析后的参数
    travel_info = state.get("travel_info", {})
    print(f"🔍 调试 - travel_info内容: {travel_info}")
    
    destination = travel_info.get("destination", "")
    travel_date = travel_info.get("travel_date", "")
    
    print(f"📋 航班查询参数: {destination}, {travel_date}")
    
    # 检查参数是否有效
    if not destination:
        print("❌ 目的地参数为空，使用默认值")
        destination = "云南"
    if not travel_date:
        print("❌ 出行日期参数为空，使用默认值")
        travel_date = "近期"
    
    from tool import query_flight_prices
    import asyncio
    import concurrent.futures
    
    try:
        # 在线程池中异步执行同步工具函数
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, 
                lambda: query_flight_prices.invoke({
                    "destination": destination,
                    "travel_date": travel_date
                })
            )
        
        # 解析JSON结果
        import json
        if isinstance(result, str):
            result = json.loads(result)
        
        print(f"✅ 航班查询完成: {result.get('price', 0)}元")
        
        # 只返回新增的flight_info，避免更新其他键
        return {"flight_info": result}
        
    except Exception as e:
        print(f"❌ 航班查询失败: {e}")
        import traceback
        traceback.print_exc()
        return {"flight_info": {"error": str(e), "price": 0}}

async def node_query_hotels(state: TravelState) -> TravelState:
    """查询酒店信息节点 - LangGraph原生并行 (异步版本)"""
    print("🏨 [并行节点2] 查询酒店信息")
    
    # 从travel_info中获取解析后的参数
    travel_info = state.get("travel_info", {})
    print(f"🔍 调试 - travel_info内容: {travel_info}")
    
    destination = travel_info.get("destination", "")
    days = travel_info.get("days", 0)
    travelers = travel_info.get("travelers", "")
    
    print(f"📋 酒店查询参数: {destination}, {days}天, {travelers}")
    
    # 检查参数是否有效
    if not destination:
        print("❌ 目的地参数为空，使用默认值")
        destination = "云南"
    if not days or days <= 0:
        print("❌ 天数参数无效，使用默认值")
        days = 5
    if not travelers:
        print("❌ 出行人数参数为空，使用默认值")
        travelers = "2人"
    
    from tool import query_hotel_prices
    import asyncio
    import concurrent.futures
    
    try:
        # 在线程池中异步执行同步工具函数
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor,
                lambda: query_hotel_prices.invoke({
                    "destination": destination,
                    "days": days,
                    "travelers": travelers
                })
            )
        
        # 解析JSON结果
        import json
        if isinstance(result, str):
            result = json.loads(result)
        
        print(f"✅ 酒店查询完成: {result.get('total_price', 0)}元")
        
        # 只返回新增的hotel_info，避免更新其他键
        return {"hotel_info": result}
        
    except Exception as e:
        print(f"❌ 酒店查询失败: {e}")
        import traceback
        traceback.print_exc()
        return {"hotel_info": {"error": str(e), "total_price": 0}}

async def node_query_attractions(state: TravelState) -> TravelState:
    """查询景点信息节点 - LangGraph原生并行 (异步版本)"""
    print("🏞️ [并行节点3] 查询景点信息")
    
    # 从travel_info中获取解析后的参数
    travel_info = state.get("travel_info", {})
    print(f"🔍 调试 - travel_info内容: {travel_info}")
    
    destination = travel_info.get("destination", "")
    days = travel_info.get("days", 0)
    requirements = travel_info.get("requirements", [])
    
    print(f"📋 景点查询参数: {destination}, {days}天, {requirements}")
    
    # 检查参数是否有效
    if not destination:
        print("❌ 目的地参数为空，使用默认值")
        destination = "云南"
    if not days or days <= 0:
        print("❌ 天数参数无效，使用默认值")
        days = 5
    
    from tool import query_attractions
    import asyncio
    import concurrent.futures
    
    try:
        # 在线程池中异步执行同步工具函数
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor,
                lambda: query_attractions.invoke({
                    "destination": destination,
                    "days": days,
                    "requirements": requirements
                })
            )
        
        # 解析JSON结果
        import json
        if isinstance(result, str):
            result = json.loads(result)
        
        print(f"✅ 景点查询完成: {len(result.get('attractions', []))}个景点")
        
        # 只返回新增的attractions_info，避免更新其他键
        return {"attractions_info": result}
        
    except Exception as e:
        print(f"❌ 景点查询失败: {e}")
        import traceback
        traceback.print_exc()
        return {"attractions_info": {"error": str(e), "attractions": []}}

async def node_aggregate_parallel_results(state: TravelState) -> TravelState:
    """汇总并行查询结果节点 - LangGraph原生并行 (异步版本)"""
    print("\n" + "="*60)
    print("🎯 [汇总节点] 汇总并行查询结果")
    print("="*60)
    
    # 从各个并行节点获取结果
    flight_info = state.get("flight_info", {})
    hotel_info = state.get("hotel_info", {})
    attractions_info = state.get("attractions_info", {})

    # 汇总查询结果
    query_results = {
        "flight": flight_info,
        "hotel": hotel_info,
        "attractions": attractions_info
    }
    
    print("✅ 并行查询结果汇总:")
    print(f"   ✈️ 机票: {flight_info.get('price', 0)}元")
    print(f"   🏨 酒店: {hotel_info.get('total_price', 0)}元")
    print(f"   🏞️ 景点: {len(attractions_info.get('attractions', []))}个")
    import asyncio
    try:
        await asyncio.sleep(2)  # 使用异步sleep
    except asyncio.CancelledError:
        print("⚠️ 汇总节点被取消（流程正常结束）")
    messages = state.get("messages", [])
    
    return {
        **state,
        "query_results": query_results,
        "messages": messages + [
            AIMessage(content=f"""
            ✅ 并行查询完成！
            
            � 查询结果汇总：
            • ✈️ 机票：{flight_info.get('price', 0)}元
            • 🏨 酒店：{hotel_info.get('total_price', 0)}元
            • 🏞️ 景点：{len(attractions_info.get('attractions', []))}个推荐
            
            📋 开始预算评估...
            """)
        ]
    }

def node_merge_results(state: TravelState) -> TravelState:
    """合并并行查询结果"""
    print("\n" + "="*60)
    print("🔄 [节点F] 合并并行查询结果")
    print("="*60)
    print("📊 正在整理查询结果...")
    print("🔍 解析工具调用返回数据...")
    
    messages = state.get("messages", [])
    
    # 从工具调用结果中获取数据并合并到query_results
    flight_info = {}
    hotel_info = {}
    attraction_info = {}
    
    # 在LangGraph 1.0中，ToolNode会添加ToolMessage到messages列表
    # 需要通过tool_call_id匹配工具调用和结果
    tool_calls_map = {}
    tool_results_map = {}
    
    # 收集工具调用信息
    for msg in messages:
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_calls_map[tool_call['id']] = tool_call
    
    # 收集工具结果
    for msg in messages:
        if hasattr(msg, 'tool_call_id') and msg.tool_call_id:
            try:
                # ToolMessage的content是JSON字符串，需要解析
                result_data = json.loads(msg.content)
                tool_results_map[msg.tool_call_id] = result_data
            except json.JSONDecodeError:
                print(f"⚠️ 无法解析工具结果: {msg.content}")
                tool_results_map[msg.tool_call_id] = {"error": "解析失败"}
    
    # 根据工具调用名称分类结果
    for call_id, tool_call in tool_calls_map.items():
        if call_id in tool_results_map:
            result = tool_results_map[call_id]
            tool_name = tool_call['name']
            
            if tool_name == 'query_flight_prices':
                flight_info = result
            elif tool_name == 'query_hotel_prices':
                hotel_info = result
            elif tool_name == 'query_attractions':
                attraction_info = result
    
    # 合并所有查询结果
    query_results = {
        "flight": flight_info,
        "hotel": hotel_info,
        "attractions": attraction_info
    }
    
    print("✅ 数据解析完成")
    print(f"🔍 解析到的结果:")
    print(f"   机票信息: {flight_info}")
    print(f"   酒店信息: {hotel_info}")
    print(f"   景点信息: {attraction_info}")
    print("📋 正在生成结果汇总...")
    
    summary = []
    if flight_info:
        summary.append(f"✈️ 机票：{flight_info.get('price', 0)}元")
    if hotel_info:
        summary.append(f"🏨 酒店：{hotel_info.get('total_price', 0)}元")
    if attraction_info:
        summary.append(f"🏞️ 景点：{len(attraction_info.get('attractions', []))}个推荐景点")
    
    return {
        **state,
        "query_results": query_results,
        "messages": messages + [
            AIMessage(content=f"""
            ✅ 信息查询完成！
            
            📊 查询结果汇总：
            {chr(10).join(summary) if summary else '暂无查询结果'}
            
            📋 开始综合评估预算...
            """)
        ]
    }

# def node_evaluate_budget(state: TravelState) -> TravelState:
#     """评估预算是否足够 - 已移除冗余节点，功能已集成到budget_optimization中"""
#     print("\n" + "="*60)
#     print("💰 [节点C] 综合评估预算")
#     print("="*60)
#     
#     query_results = state.get("query_results", {})
#     flight_cost = query_results.get("flight", {}).get("price", 0)
#     hotel_cost = query_results.get("hotel", {}).get("total_price", 0)
#     days = get_travel_info(state, "days", 5)
#     destination = get_travel_info(state, "destination", "云南")
#     budget = get_travel_info(state, "budget", 5000)
#     
#     # 每日开销估算（餐饮、交通、门票等）
#     daily_cost = get_daily_expense(destination)
#     total_daily_cost = daily_cost * days
#     
#     # 其他费用（购物、娱乐等）
#     other_costs = 500
#     
#     total_cost = flight_cost + hotel_cost + total_daily_cost + other_costs
#     
#     is_over_budget = total_cost > budget
#     budget_remaining = budget - total_cost
#     
#     cost_breakdown = {
#         "机票": flight_cost,
#         "酒店": hotel_cost,
#         "每日开销": total_daily_cost,
#         "其他费用": other_costs
#     }
#     
#     print(f"💸 总花费: {total_cost}元")
#     print(f"💰 预算: {budget}元")
#     print(f"📊 是否超预算: {is_over_budget}")
#     
#     # 合并成本分析
#     cost_analysis = {
#         "total_cost": total_cost,
#         "budget": budget,
#         "is_over_budget": is_over_budget,
#         "budget_remaining": budget_remaining,
#         "cost_breakdown": cost_breakdown
#     }
#     
#     messages = state.get("messages", [])
#     
#     # 生成详细报告
#     breakdown_text = "\n".join([f"• {item}: {cost:,}元" for item, cost in cost_breakdown.items()])
#     
#     if is_over_budget:
#         advice = f"⚠️ 当前方案超预算 {abs(budget_remaining):,}元"
#     else:
#         advice = f"✅ 预算充足，剩余 {budget_remaining:,}元"
#     
#     return {
#         **state,
#         "cost_analysis": cost_analysis,
#         "messages": messages + [
#             AIMessage(content=f"""
#             📊 预算评估报告：
#             
#             💰 费用明细：
#             {breakdown_text}
#             
#             📈 总计：{total_cost:,}元
#             🎯 预算：{budget:,}元
#             
#             {advice}
#             
#             {"🔄 需要人工优化方案..." if is_over_budget else "✅ 预算充足，继续生成行程表..."}
#             """)
#         ]
#     }

def node_human_intervention(state: TravelState) -> TravelState:
    """👤 人工干预节点 - 预算超支时的用户决策点"""
    print("\n" + "="*60)
    print("📚 [条件分支] 👤 人工干预处理")
    print("="*60)
    
    messages = state.get("messages", [])
    cost_analysis = state.get("cost_analysis", {})
    total_cost = cost_analysis.get("total_cost", 0)
    budget = cost_analysis.get("budget", 0)
    control = state.get("_control", {}) or {}
    
    print(f"💰 当前总费用: {total_cost:,}元")
    print(f"🎯 用户预算: {budget:,}元")
    print(f"📊 超支金额: {total_cost - budget:,}元")
    
    # 检查是否为非交互模式
    interactive_mode = control.get("interactive_mode", True)
    if not interactive_mode:
        print("🤖 非交互模式：自动应用优化建议")
        # 在非交互模式下，自动接受优化建议
        control["user_confirmed"] = True
        control["user_choice"] = "accept"
    
    # 检查是否已经处理过用户确认
    if control.get("user_confirmed"):
        # 用户已确认，应用相应方案
        user_choice = control.get("user_choice", "accept")
        
        if user_choice == "accept":
            # 应用优化建议
            overspend = total_cost - budget
            overspend_ratio = overspend / budget
            
            # 根据超支比例确定优化幅度
            if overspend_ratio > 0.3:
                reduction_rate = 0.25  # 大幅优化
                adjustments = [
                    "调整目的地为性价比更高的城市",
                    "缩短行程天数（减少2天）",
                    "选择经济型住宿"
                ]
            elif overspend_ratio > 0.2:
                reduction_rate = 0.20  # 中等优化
                adjustments = [
                    "选择经济型酒店（节省15%）",
                    "调整航班时间（非节假日出行）",
                    "减少部分自费项目"
                ]
            else:
                reduction_rate = 0.15  # 轻度优化
                adjustments = [
                    "减少购物预算",
                    "选择部分免费景点",
                    "优化餐饮预算"
                ]
            
            adjusted_total = total_cost * (1 - reduction_rate)
            
            human_adjustment = {
                "suggestions": control.get("suggestions", []),
                "adjusted_total": adjusted_total,
                "reduction_rate": reduction_rate,
                "adjustments": adjustments,
                "advisor_note": f"已根据预算优化方案，减少{reduction_rate*100:.0f}%费用，确保核心体验不受影响"
            }
            
            updated_cost_analysis = {
                **cost_analysis,
                "total_cost": adjusted_total,
                "is_over_budget": adjusted_total > budget,
                "human_adjustment": human_adjustment
            }
            
            print("✅ 用户选择：接受优化建议")
            print(f"🛠️ 应用优化方案，费用从 {total_cost:,}元 降至 {adjusted_total:,}元")
            
            return {
                **state,
                "cost_analysis": updated_cost_analysis,
                "status": "planning",
                "_control": {**control, "optimization_applied": True, "human_intervention_completed": True},
                "messages": messages + [
                    AIMessage(content=f"""
                    ✅ 已应用优化方案：
                    
                    🛠️ 具体调整：
                    {chr(10).join([f"• {adj}" for adj in adjustments])}
                    
                    💰 调整后总花费：{adjusted_total:,}元
                    📉 节省金额：{total_cost - adjusted_total:,}元
                    📝 备注：{human_adjustment.get('advisor_note', '')}
                    
                    ✅ 优化完成，继续生成行程表...
                    """)
                ]
            }
        elif user_choice == "reject":
            # 用户拒绝优化，终止规划
            print("❌ 用户选择：拒绝继续，终止规划")
            return {
                **state,
                "status": "terminated",
                "_control": {**control, "human_intervention_completed": True, "planning_terminated": True},
                "messages": messages + [
                    AIMessage(content="""
                    ❌ 已终止旅游规划：
                    
                    📝 由于预算限制，用户选择不继续当前规划。
                    💡 建议：可以考虑调整预算或旅游需求后重新规划。
                    
                    感谢使用智能旅游规划系统！
                    """)
                ]
            }
        else:
            # 用户选择保持原方案，继续规划
            print("📝 用户选择：保持原方案，继续规划")
            return {
                **state,
                "status": "planning",
                "_control": {**control, "optimization_applied": True, "human_intervention_completed": True},
                "messages": messages + [
                    AIMessage(content=f"""
                    📝 已保持原方案，继续规划：
                    
                    💰 总花费：{total_cost:,}元
                    🎯 预算：{budget:,}元
                    ⚠️ 超支：{total_cost - budget:,}元
                    
                    📋 将按原方案继续生成详细行程表...
                    """)
                ]
            }
    
    # 首次进入，生成优化建议并等待用户确认
    overspend = total_cost - budget
    overspend_ratio = overspend / budget
    
    suggestions = [f"当前超支 {overspend:,}元"]
    
    # 根据超支比例给出建议
    if overspend_ratio > 0.3:
        suggestions.extend([
            "建议：调整目的地或缩短行程天数",
            "预计可节省：25%费用"
        ])
    elif overspend_ratio > 0.2:
        suggestions.extend([
            "建议：选择经济型酒店，节省约800-1500元",
            "建议：调整航班时间（非节假日出行）",
            "预计可节省：20%费用"
        ])
    else:
        suggestions.extend([
            "建议：减少购物预算或选择部分免费景点",
            "预计可节省：15%费用"
        ])
    
    print(f"🤖 生成优化建议: {suggestions}")
    print("⏳ 等待用户决策...")
    
    # 等待用户确认
    return {
        **state,
        "status": "waiting_confirmation",
        "_control": {
            **control, 
            "waiting_confirmation": True, 
            "suggestions": suggestions,
            "overspend": overspend,
            "overspend_ratio": overspend_ratio
        },
        "messages": messages + [
            AIMessage(content=f"""
            ⚠️ 预算超支提醒：
            
            📊 当前情况：
            • 总花费：{total_cost:,}元
            • 预算：{budget:,}元
            • 超支：{overspend:,}元 ({overspend_ratio*100:.1f}%)
            
            💡 优化建议：
            {chr(10).join([f"• {s}" for s in suggestions])}
            
            🤔 请选择您的决策：
            1. 接受优化建议（输入"接受"或"1"）
            2. 保持原方案继续（输入"保持"或"2"）  
            3. 终止规划（输入"终止"或"3"）
            
            请输入您的选择：
            """)
        ]
    }

def node_generate_itinerary(state: TravelState) -> TravelState:
    """生成详细行程表"""
    print("\n" + "="*60)
    print("📝 [节点E] 生成行程表")
    print("="*60)
    print("📋 正在收集行程生成所需信息...")
    print("🎨 准备生成详细行程表...")
    
    destination = get_travel_info(state, "destination", "云南")
    days = get_travel_info(state, "days", 5)
    budget = get_travel_info(state, "budget", 5000)
    travelers = get_travel_info(state, "travelers", "2人")
    requirements = get_travel_info(state, "requirements", [])
    
    # 从新的字段结构获取数据
    query_results = state.get("query_results", {})
    cost_analysis = state.get("cost_analysis", {})
    total_cost = cost_analysis.get("total_cost", 0)
    
    flight_info = query_results.get("flight", {})
    hotel_info = query_results.get("hotel", {})
    attraction_info = query_results.get("attractions", {})
    human_adjustment = cost_analysis.get("human_adjustment", {})
    
    llm = get_llm()
    
    print("🤖 调用AI模型生成行程表...")
    print("⏳ 这可能需要几秒钟时间...")
    
    # 生成行程表
    response = llm.invoke(f"""
    请为以下旅游需求生成详细、实用的行程表：
    
    【基本信息】
    • 目的地：{destination}
    • 天数：{days}天{days-1}晚
    • 预算：{budget:,}元（实际花费：{total_cost:,}元）
    • 出行人数：{travelers}
    • 出行时间：{state.get('travel_date', '近期')}
    • 特殊要求：{', '.join(requirements) if requirements else '无'}
    
    【查询结果】
    • 机票：{flight_info.get('airlines', [''])[0]}，价格{flight_info.get('price', 0)}元
    • 酒店：{hotel_info.get('recommended', '当地酒店')}，{hotel_info.get('total_price', 0)}元
    • 景点：{', '.join(attraction_info.get('attractions', ['当地景点'])[:3])}
    
    【优化调整】
    {human_adjustment.get('advisor_note', '无特殊调整')}
    
    【要求】
    请生成专业、实用的行程表，包含：
    1. 行程概览（表格形式）
    2. 每日详细安排（分上午、下午、晚上）
    3. 餐饮推荐（当地特色美食）
    4. 住宿建议
    5. 交通安排
    6. 预算分配明细
    7. 实用贴士（天气、装备、注意事项）
    
    使用中文，格式美观，结构清晰，适合打印。
    请使用markdown格式。
    """)
    
    itinerary = response.content
    
    print("✅ 行程表生成完成！")
    
    messages = state.get("messages", [])
    
    return {
        **state,
        "itinerary": itinerary,
        "status": "completed",
        "messages": messages + [
            AIMessage(content=f"""
            🎉 旅游规划完成！
            
            📋 您的{destination}{days}天行程规划已完成。
            💰 总预算：{budget:,}元，预计花费：{total_cost:,}元
            
            📄 详细行程表已生成，请查收：
            
            {itinerary[:500]}...（完整内容请查看输出）
            
            ✨ 祝您旅途愉快！
            """)
        ]
    }


# ========================================
# 🔄 示例：顺序执行节点 - 旅行前置验证流程
# ========================================

def node_validate_budget(state: TravelState) -> TravelState:
    """1️⃣ 预算验证节点 - 顺序执行第一步"""
    print("\n" + "="*60)
    print("📚 [顺序1/4] 💰 预算验证")
    print("="*60)
    
    travel_info = state.get("travel_info", {})
    budget = travel_info.get("budget", 0)
    destination = travel_info.get("destination", "未知")
    days = travel_info.get("days", 1)
    
    # 模拟预算验证逻辑 - 根据目的地调整最低预算
    from common import get_daily_expense
    base_daily_cost = get_daily_expense(destination)
    min_budget_per_day = base_daily_cost + 200  # 最低每日预算 = 基础开销 + 住宿交通
    recommended_budget = min_budget_per_day * days
    
    print(f"💰 用户预算: {budget}元")
    print(f"🎯 目的地: {destination}")
    print(f"📅 天数: {days}天")
    print(f"💡 建议预算: {recommended_budget}元 (每天{min_budget_per_day}元)")
    
    budget_status = "sufficient" if budget >= recommended_budget else "insufficient"
    
    if budget_status == "sufficient":
        print("✅ 预算验证通过！")
    else:
        print("⚠️ 预算可能不足，但继续流程...")
    
    # 更新状态
    control = state.get("_control", {})
    control["budget_validated"] = True
    control["budget_status"] = budget_status
    
    print("🔄 顺序执行：预算验证 → 目的地检查")
    sleep(2)
    return {**state, "_control": control}


def node_check_destination(state: TravelState) -> TravelState:
    """2️⃣ 目的地可行性检查节点 - 顺序执行第二步"""
    print("\n" + "="*60)
    print("📚 [顺序2/4] 🌍 目的地可行性检查")
    print("="*60)
    
    travel_info = state.get("travel_info", {})
    destination = travel_info.get("destination", "未知")
    
    # 模拟目的地检查逻辑
    restricted_destinations = ["朝鲜", "阿富汗", "叙利亚"]  # 示例限制地区
    popular_destinations = ["日本", "韩国", "泰国", "新加坡", "马来西亚"]
    
    print(f"🌍 检查目的地: {destination}")
    
    if destination in restricted_destinations:
        destination_status = "restricted"
        print(f"❌ 目的地 {destination} 当前有旅行限制")
    elif destination in popular_destinations:
        destination_status = "popular"
        print(f"✅ 目的地 {destination} 是热门旅游地，可行性高")
    else:
        destination_status = "normal"
        print(f"✅ 目的地 {destination} 可以正常前往")
    
    # 更新状态
    control = state.get("_control", {})
    control["destination_checked"] = True
    control["destination_status"] = destination_status
    
    print("🔄 顺序执行：目的地检查 → 时间验证")
    sleep(2)
    return {**state, "_control": control}


def node_verify_travel_time(state: TravelState) -> TravelState:
    """3️⃣ 时间可行性检查节点 - 顺序执行第三步"""
    print("\n" + "="*60)
    print("📚 [顺序3/4] 📅 时间可行性检查")
    print("="*60)
    
    travel_info = state.get("travel_info", {})
    departure_date = travel_info.get("departure_date", "未指定")
    destination = travel_info.get("destination", "未知")
    
    print(f"📅 出发时间: {departure_date}")
    print(f"🌍 目的地: {destination}")
    
    # 模拟时间检查逻辑
    import datetime
    try:
        # 简单的时间检查
        if "春节" in str(departure_date) or "国庆" in str(departure_date):
            time_status = "peak_season"
            print("🎊 检测到节假日出行，属于旺季")
            print("💡 建议：提前预订，价格可能较高")
        else:
            time_status = "normal_season"
            print("✅ 出行时间合适，非高峰期")
    except:
        time_status = "unknown"
        print("⚠️ 无法解析出行时间，建议确认具体日期")
    
    # 更新状态
    control = state.get("_control", {})
    control["time_verified"] = True
    control["time_status"] = time_status
    
    print("🔄 顺序执行：时间验证 → 文件检查")
    sleep(2)
    return {**state, "_control": control}


def node_check_documents(state: TravelState) -> TravelState:
    """4️⃣ 个人信息验证节点 - 顺序执行第四步"""
    print("\n" + "="*60)
    print("📚 [顺序4/4] 📋 个人信息验证")
    print("="*60)
    
    travel_info = state.get("travel_info", {})
    destination = travel_info.get("destination", "未知")
    
    # 模拟文件检查逻辑
    international_destinations = ["日本", "韩国", "泰国", "新加坡", "美国", "欧洲"]
    domestic_destinations = ["北京", "上海", "广州", "深圳", "杭州", "成都"]
    
    print(f"📋 检查前往 {destination} 所需文件")
    
    if any(dest in destination for dest in international_destinations):
        document_status = "international"
        print("🛂 国际旅行所需文件:")
        print("  ✓ 护照 (有效期6个月以上)")
        print("  ✓ 签证 (根据目的地要求)")
        print("  ✓ 机票预订单")
        print("  ✓ 酒店预订单")
    elif any(dest in destination for dest in domestic_destinations):
        document_status = "domestic"
        print("🆔 国内旅行所需文件:")
        print("  ✓ 身份证")
        print("  ✓ 健康码 (如需要)")
    else:
        document_status = "unknown"
        print("❓ 无法确定具体文件要求，请确认目的地类型")
    
    # 更新状态
    control = state.get("_control", {})
    control["documents_checked"] = True
    control["document_status"] = document_status
    
    print("\n🎯 ✅ 顺序验证流程完成！")
    print("📋 验证摘要:")
    print(f"  💰 预算状态: {control.get('budget_status', '未知')}")
    print(f"  🌍 目的地状态: {control.get('destination_status', '未知')}")
    print(f"  📅 时间状态: {control.get('time_status', '未知')}")
    print(f"  📋 文件状态: {document_status}")
    print("🔄 顺序执行完成 → 开始并行查询")
    
    # 重要：更新状态，避免无限循环
    control["validation_completed"] = True
    sleep(5)
    return {**state, "_control": control, "status": "processing"}


# ========================================
# 🔄 示例：循环执行节点 - 预算优化循环
# ========================================

def node_budget_optimization(state: TravelState) -> TravelState:
    """预算优化处理节点 - 循环执行"""
    print("\n" + "="*60)
    print("📚 [循环] 💰 预算优化处理")
    print("="*60)
    
    control = state.get("_control", {})
    attempts = control.get("budget_optimization_attempts", 0) + 1
    
    # 如果是第一次进入，先进行预算评估
    cost_analysis = state.get("cost_analysis", {})
    if not cost_analysis:
        print("🔍 首次进入，执行预算评估...")
        # 执行预算评估逻辑
        query_results = state.get("query_results", {})
        flight_cost = query_results.get("flight", {}).get("price", 0)
        hotel_cost = query_results.get("hotel", {}).get("total_price", 0)
        days = state.get("travel_info", {}).get("days", 5)
        destination = state.get("travel_info", {}).get("destination", "云南")
        budget = state.get("travel_info", {}).get("budget", 5000)
        
        # 每日开销估算（餐饮、交通、门票等）
        from common import get_daily_expense
        daily_cost = get_daily_expense(destination)
        total_daily_cost = daily_cost * days
        
        # 其他费用（购物、娱乐等）
        other_costs = 500
        
        total_cost = flight_cost + hotel_cost + total_daily_cost + other_costs
        is_over_budget = total_cost > budget
        budget_remaining = budget - total_cost
        
        cost_analysis = {
            "total_cost": total_cost,
            "budget": budget,
            "is_over_budget": is_over_budget,
            "budget_remaining": budget_remaining,
            "cost_breakdown": {
                "机票": flight_cost,
                "酒店": hotel_cost,
                "每日开销": total_daily_cost,
                "其他费用": other_costs
            }
        }
        
        print(f"💸 总花费: {total_cost}元")
        print(f"💰 预算: {budget}元")
        print(f"📊 是否超预算: {is_over_budget}")
        
        # 如果预算充足，直接标记为满意
        if not is_over_budget:
            control["budget_satisfied"] = True
            control["budget_optimization_attempts"] = attempts
            return {
                **state,
                "cost_analysis": cost_analysis,
                "_control": control
            }
    
    total_cost = cost_analysis.get("total_cost", 0)
    budget = state.get("travel_info", {}).get("budget", 0)
    over_amount = total_cost - budget
    
    print(f"🔄 第{attempts}次预算优化")
    print(f"💰 当前总费用: {total_cost}元")
    print(f"🎯 用户预算: {budget}元")
    print(f"📊 超支金额: {over_amount}元")
    
    # 模拟优化策略 - 示例：有限的优化能力
    # 检查用户需求是否包含豪华要求
    travel_info = state.get("travel_info", {})
    requirements = travel_info.get("requirements", [])
    has_luxury_requirements = any(req in str(requirements) for req in ["豪华", "五星级", "头等舱", "奢华"])
    
    if has_luxury_requirements and over_amount > budget * 0.5:
        # 豪华需求且超支严重时，优化能力有限
        max_savings_rate = 0.3  # 最多只能节省30%
        print(f"⚠️ 检测到豪华旅游需求，优化能力有限（最多节省{max_savings_rate*100:.0f}%）")
        
        optimization_strategies = [
            {"name": "部分降低酒店档次", "savings": over_amount * 0.15},
            {"name": "调整部分航班时间", "savings": over_amount * 0.10},
            {"name": "减少部分自费项目", "savings": over_amount * 0.05}
        ]
    else:
        # 普通需求，可以大幅优化
        optimization_strategies = [
            {"name": "降低酒店档次", "savings": over_amount * 0.4},
            {"name": "选择经济航班", "savings": over_amount * 0.3},
            {"name": "减少景点数量", "savings": over_amount * 0.3}
        ]
    
    total_savings = 0
    print("\n🛠️ 应用优化策略:")
    for strategy in optimization_strategies:
        total_savings += strategy["savings"]
        print(f"  ✓ {strategy['name']}: 节省 {strategy['savings']:.0f}元")
    
    # 更新费用
    optimized_cost = total_cost - total_savings
    print(f"\n📊 优化后总费用: {optimized_cost:.0f}元")
    
    # 检查预算是否严重不足（实际费用远超预算）
    if total_cost > budget * 5:  # 如果实际费用超过预算5倍，认为预算严重不足
        print(f"⚠️ 预算严重不足！")
        print(f"   实际需要: {total_cost}元")
        print(f"   您的预算: {budget}元") 
        print(f"   建议预算至少: {total_cost * 0.7:.0f}元")
        control["needs_human_intervention"] = True
        budget_satisfied = False
        # 不进行不现实的费用缩减，保持原始费用分析
        return {
            **state,
            "_control": control,
            "cost_analysis": cost_analysis
        }
    
    # 检查是否满足预算
    if optimized_cost <= budget:
        budget_satisfied = True
        print("✅ 预算优化成功！费用已控制在预算范围内")
    else:
        budget_satisfied = False
        remaining_over = optimized_cost - budget
        print(f"⚠️ 仍超支 {remaining_over:.0f}元，需要进一步优化")
        
        # 如果是豪华需求且已达到最大优化次数，标记为无法进一步优化
        if has_luxury_requirements and attempts >= 2:
            print("💡 豪华需求限制了进一步优化空间，建议人工干预")
            # 强制标记为需要人工干预（当达到3次尝试时）
            if attempts >= 3:
                control["needs_human_intervention"] = True
    
    # 更新状态
    control["budget_optimization_attempts"] = attempts
    control["budget_satisfied"] = budget_satisfied
    control["optimized_cost"] = optimized_cost
    
    # 更新费用分析
    updated_cost_analysis = cost_analysis.copy()
    updated_cost_analysis["total_cost"] = optimized_cost
    updated_cost_analysis["is_over_budget"] = not budget_satisfied
    updated_cost_analysis["budget_remaining"] = budget - optimized_cost
    
    # 更新费用明细 - 按比例减少各项费用，但设置合理下限
    if total_cost > 0:  # 避免除零错误
        reduction_rate = total_savings / total_cost
        original_breakdown = cost_analysis.get("cost_breakdown", {})
        updated_breakdown = {}
        
        # 设置各项费用的合理最低值
        min_costs = {
            "机票": 300,      # 最便宜的国内机票
            "酒店": 100,      # 每晚最低住宿费用  
            "每日开销": 80,   # 每天最低餐饮交通费
            "其他费用": 50    # 最低其他费用
        }
        
        for item, original_cost in original_breakdown.items():
            reduced_cost = int(original_cost * (1 - reduction_rate))
            min_cost = min_costs.get(item, original_cost * 0.3)  # 默认最低为原价30%
            final_cost = max(reduced_cost, min_cost)
            updated_breakdown[item] = final_cost
        
        # 重新计算总费用以确保一致性
        actual_optimized_cost = sum(updated_breakdown.values())
        updated_cost_analysis["total_cost"] = actual_optimized_cost
        updated_cost_analysis["cost_breakdown"] = updated_breakdown
        updated_cost_analysis["budget_remaining"] = budget - actual_optimized_cost
        
        print(f"📊 费用明细优化:")
        for item, cost in updated_breakdown.items():
            original_cost = original_breakdown.get(item, 0)
            savings = original_cost - cost
            print(f"  • {item}: {original_cost}元 → {cost}元 (节省{savings}元)")
        
        # 如果优化后仍然超支太多，触发人工干预
        if actual_optimized_cost > budget * 2:
            print("⚠️ 即使优化后仍严重超支，建议调整行程或增加预算")
            control["needs_human_intervention"] = True

    sleep(2)
    
    return {
        **state,  # 保持原有状态
        "_control": control,
        "cost_analysis": updated_cost_analysis
    }


def node_check_budget_satisfaction(state: TravelState) -> TravelState:
    """检查预算满意度节点 - 循环条件判断"""
    print("\n" + "="*60)
    print("📚 [示例-循环] 🔍 预算满意度检查")
    print("="*60)
    
    control = state.get("_control", {})
    attempts = control.get("budget_optimization_attempts", 0)
    budget_satisfied = control.get("budget_satisfied", False)
    optimized_cost = control.get("optimized_cost", 0)
    budget = state.get("travel_info", {}).get("budget", 0)
    
    print(f"🔍 预算循环状态检查:")
    print(f"  🔄 优化次数: {attempts}/3")
    print(f"  💰 当前费用: {optimized_cost:.0f}元")
    print(f"  🎯 预算限额: {budget}元")
    print(f"  ✅ 是否满意: {budget_satisfied}")
    
    if budget_satisfied:
        print("🎉 预算优化成功！进入行程优化阶段")
    elif attempts >= 3:
        print("⚠️ 已达最大优化次数，转入人工干预")
    else:
        print("🔄 继续预算优化...")
    
    return state


# ========================================
# 🔄 示例：循环执行节点 - 行程优化循环
# ========================================

def node_itinerary_optimization(state: TravelState) -> TravelState:
    """行程优化处理节点 - 循环执行"""
    print("\n" + "="*60)
    print("📚 [示例-循环] 🗺️ 行程优化处理")
    print("="*60)
    
    control = state.get("_control", {})
    attempts = control.get("itinerary_optimization_attempts", 0) + 1
    
    travel_info = state.get("travel_info", {})
    destination = travel_info.get("destination", "未知")
    days = travel_info.get("days", 1)
    
    print(f"🔄 第{attempts}次行程优化")
    print(f"🌍 目的地: {destination}")
    print(f"📅 天数: {days}天")
    
    # 模拟行程优化策略
    optimization_aspects = [
        {"aspect": "景点路线优化", "improvement": "减少往返时间30%"},
        {"aspect": "用餐安排优化", "improvement": "增加当地特色餐厅"},
        {"aspect": "交通方式优化", "improvement": "选择更便捷的交通"},
        {"aspect": "时间分配优化", "improvement": "平衡游览和休息时间"}
    ]
    
    print("\n🛠️ 应用优化策略:")
    for opt in optimization_aspects:
        print(f"  ✓ {opt['aspect']}: {opt['improvement']}")
    
    # 模拟满意度评分
    base_score = 0.6
    improvement_per_attempt = 0.15
    current_score = min(0.95, base_score + (attempts * improvement_per_attempt))
    
    print(f"\n📊 行程满意度评分: {current_score:.2f}/1.0")
    
    # 检查是否满足要求
    if current_score >= 0.85:
        itinerary_satisfied = True
        print("✅ 行程优化成功！满意度达标")
    else:
        itinerary_satisfied = False
        print(f"⚠️ 满意度未达标(目标0.85)，需要进一步优化")
    
    # 更新状态
    control["itinerary_optimization_attempts"] = attempts
    control["itinerary_satisfied"] = itinerary_satisfied
    control["itinerary_score"] = current_score
    
    return {**state, "_control": control}


def node_check_itinerary_satisfaction(state: TravelState) -> TravelState:
    """检查行程满意度节点 - 循环条件判断"""
    print("\n" + "="*60)
    print("📚 [循环] 🔍 行程满意度检查")
    print("="*60)
    
    control = state.get("_control", {})
    attempts = control.get("itinerary_optimization_attempts", 0)
    itinerary_satisfied = control.get("itinerary_satisfied", False)
    itinerary_score = control.get("itinerary_score", 0)
    
    print(f"🔍 行程循环状态检查:")
    print(f"  🔄 优化次数: {attempts}/3")
    print(f"  📊 满意度评分: {itinerary_score:.2f}/1.0")
    print(f"  🎯 目标评分: 0.85")
    print(f"  ✅ 是否满意: {itinerary_satisfied}")
    
    if itinerary_satisfied:
        print("🎉 行程优化成功！准备生成最终行程")
    elif attempts >= 3:
        print("⚠️ 已达最大优化次数，使用当前最佳方案")
    else:
        print("🔄 继续行程优化...")
    
    sleep(2)
    
    return state