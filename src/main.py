"""旅游规划助手 - 主程序入口"""

import asyncio
from typing import Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from node import TravelState
from graph import create_travel_planning_graph
from logger_utils import log_print
from persistence import create_persistent_planner, PersistentNodeWrapper, resume_session, list_resumable_sessions

# ==================== 人工干预交互函数 ====================
def handle_human_intervention_input(state: TravelState) -> TravelState:
    """处理人工干预时的用户输入 - 交互式决策"""
    print(f"\n📚 [示例-交互处理] 👤 人工干预用户输入处理")
    
    cost_analysis = state.get("cost_analysis", {})
    total_cost = cost_analysis.get("total_cost", 0)
    budget = cost_analysis.get("budget", 0)
    overspend_amount = total_cost - budget
    overspend_ratio = overspend_amount / budget if budget > 0 else 0
    
    print(f"\n💰 预算分析:")
    print(f"   📊 预算总额: {budget:,}元")
    print(f"   💸 当前花费: {total_cost:,}元")
    print(f"   ⚠️ 超支金额: {overspend_amount:,}元")
    print(f"   📈 超支比例: {overspend_ratio:.1%}")
    
    # 根据超支比例提供优化建议
    if overspend_ratio > 0.3:
        optimization_rate = 0.25
        print(f"   💡 建议优化: 降低{optimization_rate:.0%}费用")
    elif overspend_ratio > 0.2:
        optimization_rate = 0.20
        print(f"   💡 建议优化: 降低{optimization_rate:.0%}费用")
    else:
        optimization_rate = 0.15
        print(f"   💡 建议优化: 降低{optimization_rate:.0%}费用")
    
    print(f"\n🤔 请选择您的决策：")
    print(f"1. 接受优化建议（输入\"接受\"或\"1\"）")
    print(f"2. 保持原方案继续（输入\"保持\"或\"2\"）")
    print(f"3. 终止规划（输入\"终止\"或\"3\"）")
    
    while True:
        try:
            user_input = input("\n👤 请输入您的选择: ").strip().lower()
            
            if user_input in ["接受", "1", "accept"]:
                print("✅ 您选择：接受优化建议")
                return handle_accept_optimization(state, optimization_rate)
            elif user_input in ["保持", "2", "keep"]:
                print("✅ 您选择：保持原方案继续")
                return handle_keep_original(state)
            elif user_input in ["终止", "3", "reject", "quit"]:
                print("✅ 您选择：终止规划")
                return handle_terminate_planning(state)
            else:
                print("❌ 无效输入，请重新选择（1-3）")
                continue
                
        except KeyboardInterrupt:
            print("\n❌ 用户中断，终止规划")
            return handle_terminate_planning(state)
        except Exception as e:
            print(f"❌ 输入错误: {e}")
            continue

def handle_accept_optimization(state: TravelState, optimization_rate: float) -> TravelState:
    """处理用户接受优化的情况"""
    control = state.get("_control", {})
    messages = state.get("messages", [])
    
    return {
        **state,
        "status": "optimizing",
        "_control": {
            **control, 
            "human_intervention_completed": True,
            "user_choice": "accept",
            "optimization_applied": True,
            "optimization_rate": optimization_rate
        },
        "messages": messages + [
            AIMessage(content=f"""
            ✅ 已接受优化建议：
            
            🔄 优化方案：降低{optimization_rate:.0%}费用
            💡 系统将自动调整行程安排以符合预算
            ➡️ 继续生成最终行程
            """)
        ]
    }

def handle_keep_original(state: TravelState) -> TravelState:
    """处理用户保持原方案的情况"""
    control = state.get("_control", {})
    messages = state.get("messages", [])
    
    return {
        **state,
        "status": "continuing",
        "_control": {
            **control, 
            "human_intervention_completed": True,
            "user_choice": "keep",
            "optimization_applied": False
        },
        "messages": messages + [
            AIMessage(content="""
            ✅ 已保持原方案：
            
            📝 将按照当前规划继续
            💰 预算超支风险由用户承担
            ➡️ 继续生成最终行程
            """)
        ]
    }

def handle_terminate_planning(state: TravelState) -> TravelState:
    """处理用户终止规划的情况"""
    control = state.get("_control", {})
    messages = state.get("messages", [])
    
    return {
        **state,
        "status": "terminated",
        "_control": {
            **control, 
            "human_intervention_completed": True,
            "user_choice": "reject",
            "planning_terminated": True
        },
        "messages": messages + [
            AIMessage(content="""
            ❌ 已终止旅游规划：
            
            📝 由于预算限制，用户选择不继续当前规划。
            💡 建议：可以考虑调整预算或旅游需求后重新规划。
            
            感谢使用智能旅游规划系统！
            """)
        ]
    }

# ==================== 执行函数 ====================
async def run_travel_planning(user_query: str, interactive: bool = False, enable_persistence: bool = True):
    """运行旅游规划"""
    
    # 创建持久化规划器
    persistent_planner = None
    if enable_persistence:
        persistent_planner = await create_persistent_planner(user_query)
        log_print("💾 持久化功能已启用")
    
    # 创建Graph
    workflow = create_travel_planning_graph()
    
    # 创建 checkpointer 并执行整个流程
    async with AsyncSqliteSaver.from_conn_string("travel_planning.db") as checkpointer:
        app = workflow.compile(checkpointer=checkpointer)
        
        # 初始状态
        initial_state = TravelState(
            messages=[HumanMessage(content=user_query)],
            input=user_query,
            travel_info=None,
            query_results=None,
            cost_analysis=None,
            itinerary=None,
            status="collecting_info",
            _control={"interactive_mode": interactive}
        )
        
        # 执行Graph
        current_state = initial_state
        step_count = 0
        
        while True:
            final_state = None
            log_print(f"\n{'='*60}")
            log_print(f" 执行第 {step_count + 1} 轮处理")
            log_print(f"{'='*60}")
            
            # 使用values模式获取完整状态，同时显示进度
            async for event in app.astream(
                current_state,
                {"configurable": {"thread_id": f"travel_{persistent_planner.session_id if persistent_planner else 'default'}"}},
                stream_mode="values"
            ):
                final_state = event
                # 简化的进度显示
                _show_progress(event)
                
                # 持久化状态保存
                if enable_persistence and persistent_planner and final_state:
                    await persistent_planner.save_state(final_state, f"step_{step_count + 1}")
            
            step_count += 1
            
            # 检查是否需要用户输入 - 交互式状态管理
            if final_state and final_state.get("status") in ["collecting_info", "waiting_confirmation"]:
                last_message = final_state["messages"][-1]
                if isinstance(last_message, AIMessage):
                    log_print(f"\n🤖 {last_message.content}")
                    
                    if interactive:
                        # 特殊处理：人工干预状态
                        if final_state.get("status") == "waiting_confirmation":
                            print(f"\n📚 [示例-状态管理] 👤 检测到人工干预需求")
                            current_state = handle_human_intervention_input(final_state)
                            log_print(f"✅ 人工干预处理完成，状态：{current_state.get('status')}")
                            
                            if current_state.get("status") == "terminated":
                                log_print("\n🔚 用户选择终止规划，流程结束")
                                break
                            # 继续循环，使用更新的 current_state
                            continue
                        else:
                            # 普通交互模式下获取用户输入
                            user_response = input("\n💬 您的回复：")
                            
                            # 更新状态继续执行
                            current_state = dict(final_state)
                            current_state["messages"] = final_state["messages"] + [HumanMessage(content=user_response)]
                            current_state["status"] = "planning"
                            # 继续循环，使用更新的 current_state
                            continue
                    else:
                        # 非交互模式：自动处理
                        current_state = dict(final_state)
                        current_state["status"] = "planning"
                        log_print("🤖 非交互模式：自动继续处理")
                        # 继续循环，使用更新的 current_state
                        continue
                else:
                    break
            else:
                # 流程完成
                break
        
    # 显示最终结果
    if final_state:
        log_print("\n" + "="*80)
        log_print("🎉 旅游规划完成！")
        log_print("="*80)
        
        # 显示最终行程
        if final_state.get("itinerary"):
            log_print("📋 最终行程安排：")
            log_print(final_state["itinerary"])
        
        # 显示成本分析
        if final_state.get("cost_analysis"):
            cost_analysis = final_state["cost_analysis"]
            log_print("\n💰 成本分析：")
            log_print(f"   总花费：{cost_analysis.get('total_cost', 0):,.0f}元")
            log_print(f"   预算：{cost_analysis.get('budget', 0):,.0f}元")
            
            cost_breakdown = cost_analysis.get('cost_breakdown', {})
            if cost_breakdown:
                log_print("   费用明细：")
                for item, cost in cost_breakdown.items():
                    log_print(f"     • {item}：{cost:,.0f}元")
            
            if cost_analysis.get('is_over_budget', False):
                overspend = cost_analysis.get('total_cost', 0) - cost_analysis.get('budget', 0)
                log_print(f"   ⚠️ 超支：{overspend:,.0f}元")
            else:
                remaining = cost_analysis.get('budget', 0) - cost_analysis.get('total_cost', 0)
                log_print(f"   ✅ 剩余预算：{remaining:,.0f}元")
        
        # 保存最终状态
        if enable_persistence and persistent_planner:
            await persistent_planner.save_state(final_state, "final_result")
            log_print(f"\n💾 最终结果已保存到会话: {persistent_planner.session_id}")
    
    return final_state

async def resume_travel_planning(session_id: str, interactive: bool = False):
    """恢复中断的旅游规划"""
    
    # 恢复会话
    persistent_planner, latest_state = await resume_session(session_id)
    
    if not latest_state:
        log_print("❌ 无法恢复会话，状态数据不存在")
        return
    
    # 创建Graph
    workflow = create_travel_planning_graph()
    
    # 创建 checkpointer 并执行恢复流程
    async with AsyncSqliteSaver.from_conn_string("travel_planning.db") as checkpointer:
        app = workflow.compile(checkpointer=checkpointer)
    
        log_print("="*80)
        log_print("🔄 恢复中断的旅游规划")
        log_print("="*80)
        log_print(f"📋 会话ID：{session_id}")
        log_print(f"📊 从第{persistent_planner.step_counter}步继续执行")
        
        # 使用恢复的状态作为初始状态
        initial_state = latest_state
        
        # 执行Graph - 从中断点继续
        current_state = initial_state
        step_count = persistent_planner.step_counter  # 从恢复的步骤开始
        enable_persistence = True  # 恢复模式下启用持久化
    
        while True:
            final_state = None
            log_print(f"\n{'='*60}")
            log_print(f" 执行第 {step_count + 1} 轮处理")
            log_print(f"{'='*60}")
            
            # 使用values模式获取完整状态，同时显示进度
            async for event in app.astream(
                current_state,
                {"configurable": {"thread_id": f"travel_resume_{session_id}"}},
                stream_mode="values"
            ):
                final_state = event
                # 简化的进度显示
                _show_progress(event)
                
                # 持久化状态保存
                if enable_persistence and persistent_planner and final_state:
                    await persistent_planner.save_state(final_state, f"resume_step_{step_count + 1}")
            
            step_count += 1
        
            # 检查是否需要用户输入 - 交互式状态管理
            if final_state and final_state.get("status") in ["collecting_info", "waiting_confirmation"]:
                last_message = final_state["messages"][-1]
                if isinstance(last_message, AIMessage):
                    log_print(f"\n🤖 {last_message.content}")
                    
                    if interactive:
                        # 特殊处理：人工干预状态
                        if final_state.get("status") == "waiting_confirmation":
                            print(f"\n📚 [示例-状态管理] 👤 检测到人工干预需求")
                            # 调用专门的人工干预处理函数
                            current_state = handle_human_intervention_input(final_state)
                            log_print(f"✅ 人工干预处理完成，状态：{current_state.get('status')}")
                            
                            # 如果用户选择终止，直接结束
                            if current_state.get("status") == "terminated":
                                log_print("\n🔚 用户选择终止规划，流程结束")
                                break
                            # 继续循环，使用更新的 current_state
                            continue
                        else:
                            # 普通交互模式下获取用户输入
                            user_response = input("\n💬 您的回复：")
                            
                            # 更新状态继续执行
                            current_state = dict(final_state)
                            current_state["messages"] = final_state["messages"] + [HumanMessage(content=user_response)]
                            current_state["status"] = "processing"
                            log_print("✅ 信息收集完成，继续处理...")
                            # 继续循环，使用更新的 current_state
                            continue
                    else:
                        log_print("\n⚠️ 需要更多信息，但当前为非交互模式")
                        break
                else:
                    break
            else:
                # 流程完成
                break
    
        # 显示最终结果
        log_print(f"\n{'='*80}")
        log_print("🎉 旅游规划恢复完成！")
        log_print(f"{'='*80}")
        
        # 保存最终结果到持久化存储
        if persistent_planner and final_state:
            final_itinerary = final_state.get("itinerary", "行程规划完成")
            total_cost = 0
            if final_state.get("cost_analysis"):
                total_cost = final_state["cost_analysis"].get("total_cost", 0)
            
            await persistent_planner.finalize_session(final_itinerary, total_cost)
            
            # 显示会话摘要
            summary = await persistent_planner.get_session_summary()
            log_print(f"💾 会话ID: {summary['session_id']}")
            log_print(f"📊 执行步骤: {summary['steps_completed']}")
            log_print(f"🎯 缓存统计: {summary['cache_stats']['total_cache']}条缓存，{summary['cache_stats']['total_hits']}次命中")
        
        return final_state

def _process_stream_event(event):
    """处理流式事件输出"""
    for node_name, node_data in event.items():
        if node_name == "parse_intent":
            log_print(f"🧠 [步骤1] 解析用户意图...")
            if node_data.get("travel_info"):
                info = node_data["travel_info"]
                log_print(f"   📍 目的地：{info.get('destination', '未知')}")
                log_print(f"   📅 天数：{info.get('days', '未知')}天")
                log_print(f"   💰 预算：{info.get('budget', '未知')}元")
                log_print("   ✅ 意图解析完成")
        
        elif node_name == "start_parallel":
            log_print(f"🚀 [步骤2] LangGraph原生并行查询...")
            log_print("   ⚡ 启动真正的并行执行...")
            
        elif node_name == "query_flights":
            log_print(f"   ✈️ 并行查询航班信息...")
            if node_data.get("flight_info"):
                flight_info = node_data["flight_info"]
                log_print(f"      ✅ 航班查询完成: {flight_info.get('price', 0)}元")
                
        elif node_name == "query_hotels":
            log_print(f"   🏨 并行查询酒店信息...")
            if node_data.get("hotel_info"):
                hotel_info = node_data["hotel_info"]
                log_print(f"      ✅ 酒店查询完成: {hotel_info.get('total_price', 0)}元")
                
        elif node_name == "query_attractions":
            log_print(f"   🏞️ 并行查询景点信息...")
            if node_data.get("attractions_info"):
                attractions_info = node_data["attractions_info"]
                log_print(f"      ✅ 景点查询完成: {len(attractions_info.get('attractions', []))}个")
                
        elif node_name == "aggregate_results":
            log_print(f"🎯 [步骤3] 汇总并行查询结果...")
            if node_data.get("query_results"):
                results = node_data["query_results"]
                log_print(f"   ✅ 所有并行查询完成")
                if results.get("flight"):
                    log_print(f"      ✈️ 机票: {results['flight'].get('price', 0)}元")
                if results.get("hotel"):
                    log_print(f"      🏨 酒店: {results['hotel'].get('total_price', 0)}元")
                if results.get("attractions"):
                    log_print(f"      🏞️ 景点: {len(results['attractions'].get('attractions', []))}个")
                    
        elif node_name == "parallel_query":
            log_print(f"⚡ [备用] 自定义并行查询...")
            log_print("   🚀 同时启动3个查询任务...")
            if node_data.get("query_results"):
                results = node_data["query_results"]
                log_print(f"   ✅ 并行查询完成")
                if results.get("flight"):
                    log_print(f"      ✈️ 机票: {results['flight'].get('price', 0)}元")
                if results.get("hotel"):
                    log_print(f"      🏨 酒店: {results['hotel'].get('price', 0)}元")
                if results.get("attractions"):
                    log_print(f"      🏞️ 景点: {len(results['attractions'].get('attractions', []))}个")
        
        elif node_name == "prepare_parallel":
            log_print(f"⚙️ [步骤2] 准备并行查询...")
            log_print("   🔍 正在准备航班、酒店、景点查询参数...")
            log_print("   ✅ 查询参数准备完成")
        
        elif node_name == "tools":
            log_print(f"🔧 [步骤3] 执行外部API查询...")
            log_print("   ✈️ 查询航班信息...")
            log_print("   🏨 查询酒店信息...")
            log_print("   🎯 查询景点信息...")
            log_print("   ✅ 所有查询完成")
        
        elif node_name == "merge_results":
            log_print(f"📊 [步骤4] 合并查询结果...")
            if node_data.get("query_results"):
                results = node_data["query_results"]
                if results.get("flights"):
                    flight = results["flights"]
                    log_print(f"   ✈️ 航班：{flight.get('airline', '')} - {flight.get('price', 0)}元")
                if results.get("hotels"):
                    hotel = results["hotels"]
                    log_print(f"   🏨 住宿：{hotel.get('name', '')} - {hotel.get('price', 0)}元")
                if results.get("attractions"):
                    attractions = results["attractions"]
                    log_print(f"   🎯 景点：{len(attractions.get('attractions', []))}个景点")
            log_print("   ✅ 结果合并完成")
        
        # elif node_name == "evaluate_budget":
        #     # 已移除冗余节点，预算评估已集成到budget_optimization中
        #     log_print(f"💰 [步骤5] 评估预算...")
        #     if node_data.get("cost_analysis"):
        #         cost = node_data["cost_analysis"]
        #         total = cost.get("total_cost", 0)
        #         budget = cost.get("budget", 0)
        #         over_budget = cost.get("is_over_budget", False)
        #         log_print(f"   💸 总花费：{total:,}元")
        #         log_print(f"   💰 预算：{budget:,}元")
        #         if over_budget:
        #             log_print(f"   ⚠️ 超支：{total - budget:,}元")
        #             log_print("   🔔 需要人工干预")
        #         else:
        #             log_print("   ✅ 预算充足")
        #     log_print("   ✅ 预算评估完成")
        
        elif node_name == "human_intervention":
            log_print(f"👤 [步骤6] 人工干预处理...")
            control = node_data.get("_control", {})
            status = node_data.get("status", "")
            
            # 示例：人工干预的交互处理
            print(f"📚 [示例-交互处理] 👤 人工干预状态管理")
            
            if status == "waiting_confirmation":
                log_print("   ⏳ 等待用户确认优化建议...")
                log_print("   💡 用户可以选择：接受优化/保持原方案/终止规划")
            elif status == "terminated":
                log_print("   ❌ 用户选择终止规划")
                log_print("   🔚 规划流程已结束")
            elif control.get("human_intervention_completed"):
                user_choice = control.get("user_choice", "unknown")
                if user_choice == "accept":
                    log_print("   ✅ 用户接受优化建议")
                    log_print("   🔄 已应用预算优化方案")
                elif user_choice == "keep":
                    log_print("   ✅ 用户保持原方案继续")
                    log_print("   ➡️ 继续当前规划流程")
                else:
                    log_print(f"   ✅ 用户已确认：{user_choice}")
            else:
                log_print("   🔄 正在处理人工干预逻辑...")
            
            log_print("   ✅ 人工干预处理完成")
        
        elif node_name == "generate_itinerary":
            log_print(f"📝 [步骤7] 生成最终行程...")
            log_print("   📋 正在生成详细行程表...")
            log_print("   🎨 格式化行程内容...")
            if node_data.get("itinerary"):
                log_print("   ✅ 行程生成完成")
                log_print(f"\n{'='*80}")
                log_print("🎯 最终行程规划")
                log_print(f"{'='*80}")
                log_print(node_data["itinerary"])
            else:
                log_print("   ✅ 行程生成完成")

def _process_event(event):
    """处理事件输出（保留兼容性）"""
    if "itinerary" in event:
        log_print("\n" + "="*80)
        log_print("🎯 最终行程规划")
        log_print("="*80)
        log_print(event["itinerary"])
        log_print("\n✨ 规划完成！")
    
    elif "cost_analysis" in event:
        cost_analysis = event["cost_analysis"]
        log_print(f"\n💰 预算评估完成：")
        log_print(f"   总计花费：{cost_analysis.get('total_cost', 0):,}元")
        log_print(f"   是否超预算：{'是' if cost_analysis.get('is_over_budget', False) else '否'}")
    
    elif "messages" in event and event["messages"]:
        last_msg = event["messages"][-1]
        if isinstance(last_msg, AIMessage) and not event.get("_waiting_for_input"):
            # 过滤掉长行程内容，避免重复输出
            content = last_msg.content
            if "详细行程表已生成" in content or "行程表已生成" in content:
                log_print("\n📄 行程表生成中...")
            elif len(content) < 500:  # 只输出短消息
                log_print(f"\n💬 {content}")

def _show_progress(event):
    """简化的进度显示函数"""
    if not event:
        return
    
    # 调试信息：显示事件中的所有键
    # print(f"🔍 调试：事件键 = {list(event.keys())}")
    # if "itinerary" in event:
    #     print(f"🔍 调试：发现itinerary字段，长度 = {len(str(event['itinerary']))}")
    
    # 检查当前状态并显示相应的进度信息
    current_status = event.get("status", "")
    
    # 根据状态显示进度 - 优先检查最终结果
    if "itinerary" in event and event.get("itinerary") and len(str(event["itinerary"])) > 100:
        log_print("📝 行程生成完成")
        log_print(f"\n{'='*80}")
        log_print("🎯 最终行程规划")
        log_print(f"{'='*80}")
        log_print(event["itinerary"])
        log_print(f"\n{'='*80}")
        log_print("✨ 规划完成！")
        log_print(f"{'='*80}")
    
    elif "cost_analysis" in event and event.get("cost_analysis"):
        cost = event["cost_analysis"]
        total = cost.get("total_cost", 0)
        over_budget = cost.get("is_over_budget", False)
        status_text = "超预算" if over_budget else "预算充足"
        log_print(f"💰 预算评估完成 - 总花费：{total:,}元 ({status_text})")
    
    elif "query_results" in event and event.get("query_results"):
        log_print("🔍 外部查询完成 - 航班、酒店、景点信息已获取")
    
    elif "travel_info" in event and event.get("travel_info"):
        info = event["travel_info"]
        log_print(f"🧠 解析意图完成 - 目的地：{info.get('destination', '未知')}, 天数：{info.get('days', '未知')}天")
    
    elif current_status == "waiting_confirmation":
        log_print("👤 等待用户确认优化建议...")
    
    elif current_status == "collecting_info":
        log_print("📝 等待用户补充信息...")


# ==================== 主程序 ====================
def main():
    """主程序入口函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="智能旅游规划助手")
    parser.add_argument("--query", type=str, help="旅游需求查询")
    parser.add_argument("--interactive", action="store_true", help="交互模式")
    parser.add_argument("--no-persistence", action="store_true", help="禁用持久化功能")
    
    args = parser.parse_args()
    
    enable_persistence = not args.no_persistence
    
    if args.query:
        asyncio.run(run_travel_planning(args.query, args.interactive, enable_persistence))
    else:
        # 交互式输入模式
        log_print("🌟 智能旅游规划助手")
        log_print("=" * 50)
        log_print("请输入您的旅游需求")
        log_print("例如：我想去云南旅游5天，预算8000元")
        log_print("=" * 50)
        
        user_query = input("\n💬 请输入您的旅游需求: ").strip()
        if user_query:
            asyncio.run(run_travel_planning(user_query, True, enable_persistence))
        else:
            log_print("❌ 未输入有效需求，程序退出")

async def interactive_resume():
    """交互式恢复会话选择"""
    sessions = await list_resumable_sessions()
    
    if not sessions:
        print("📭 没有找到可恢复的会话")
        return
    
    while True:
        try:
            choice = input(f"\n🔢 请选择要恢复的会话 (1-{len(sessions)}) 或输入 'q' 退出: ").strip()
            
            if choice.lower() == 'q':
                print("👋 退出恢复功能")
                return
            
            session_index = int(choice) - 1
            if 0 <= session_index < len(sessions):
                selected_session = sessions[session_index]
                session_id = selected_session['session_id']
                
                print(f"\n✅ 选择恢复会话: {session_id}")
                print(f"📝 用户需求: {selected_session['user_query']}")
                
                # 确认恢复
                confirm = input("🤔 确认恢复此会话吗？(y/n): ").strip().lower()
                if confirm in ['y', 'yes', '是', '确认']:
                    await resume_travel_planning(session_id, interactive=True)
                    break
                else:
                    print("❌ 取消恢复")
                    continue
            else:
                print(f"❌ 无效选择，请输入 1-{len(sessions)} 之间的数字")
        except ValueError:
            print("❌ 请输入有效的数字")
        except KeyboardInterrupt:
            print("\n👋 用户取消操作")
            break

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "resume":
        # 恢复模式
        asyncio.run(interactive_resume())
    else:
        # 正常模式
        main()