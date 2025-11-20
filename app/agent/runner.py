import threading
import time
from typing import Any, Dict

from app.utils import Spinner

from .factory import get_agent
from .memory import get_messages


_history_offsets: Dict[str, int] = {}


def _invoke_agent(agent, user_input: str, config: Dict[str, Any], container: Dict[str, Any]) -> None:
    try:
        container["result"] = agent.invoke(
            input={"messages": [{"role": "user", "content": user_input}]},
            config=config,
        )
    except Exception as exc:
        container["error"] = exc


def _emit_new_messages(thread_id: str, start_idx: int, trace_started: bool):
    messages = get_messages(thread_id)
    total = len(messages)
    if start_idx < 0:
        start_idx = 0
    if start_idx > total:
        start_idx = total
    if start_idx >= total:
        return total, trace_started, False

    if not trace_started:
        print("\n📜 === 执行过程 ===")
        trace_started = True

    for idx, msg in enumerate(messages[start_idx:], start=start_idx + 1):
        msg_type = (getattr(msg, "type", "") or "").lower()
        msg_role = (getattr(msg, "role", "") or "").lower()

        if msg_role == "system" or msg_type == "system":
            role_label = "系统提示"
        elif msg_role == "user" or msg_type in ("human", "user"):
            role_label = "用户输入"
        else:
            role_label = "模型响应"

        content = getattr(msg, "content", "")
        if not isinstance(content, str):
            content = str(content)
        content = content.strip()
        if content:
            label = role_label or (msg_role or msg_type or "消息")
            preview = content[:2000]
            suffix = "...（已截断）" if len(content) > 2000 else ""
            print(f"\n[{label}]\n{preview}{suffix}")

    return total, trace_started, True


def run_agent(user_input: str, thread_id: str = "user_session", show_trace: bool = True):
    """执行用户指令并输出带记忆的模型结果。"""
    try:
        config: Dict[str, Any] = {"configurable": {"thread_id": thread_id}}
        agent = get_agent()

        result_box: Dict[str, Any] = {}
        worker = threading.Thread(
            target=_invoke_agent,
            args=(agent, user_input, config, result_box),
            daemon=True,
        )

        spinner = Spinner()
        spinner.start()
        spinner_active = True

        start_idx = _history_offsets.get(thread_id, 0)
        trace_started = False

        worker.start()
        while worker.is_alive():
            if show_trace:
                start_idx, trace_started, printed = _emit_new_messages(thread_id, start_idx, trace_started)
                if printed and spinner_active:
                    spinner.stop()
                    spinner_active = False
            time.sleep(0.15)

        worker.join()
        if spinner_active:
            spinner.stop()

        if show_trace:
            start_idx, trace_started, _ = _emit_new_messages(thread_id, start_idx, trace_started)

        if "error" in result_box:
            raise result_box["error"]

        result = result_box.get("result", {})

        if "messages" in result and len(result["messages"]) > 0:
            final_msg = result["messages"][-1]
            final_output = getattr(final_msg, "content", str(final_msg)).strip()
            _history_offsets[thread_id] = len(result["messages"])
        else:
            final_output = result.get("output", str(result)).strip()
            _history_offsets[thread_id] = start_idx

        print("\n" + "=" * 60)
        print("✅ 最终结果：")
        print(final_output)
        print("=" * 60 + "\n")
        return final_output

    except Exception as e:
        print(f"\n❌ 交互错误：{str(e)}\n")
        return ""


__all__ = ["run_agent"]
