from typing import Any, List

from langgraph.checkpoint.memory import InMemorySaver


memory_checkpointer = InMemorySaver()


def clear_memory(thread_id: str = "user_session") -> None:
    """清除指定线程的记忆。"""
    try:
        memory_checkpointer.delete({"configurable": {"thread_id": thread_id}})
        print(f"🧹 已清除对话记忆 (线程: {thread_id})")
    except Exception as e:
        print(f"❌ 清除记忆失败：{str(e)}")


def show_memory_info(thread_id: str = "user_session") -> None:
    """显示记忆状态信息。"""
    try:
        checkpoint = memory_checkpointer.get({"configurable": {"thread_id": thread_id}})
        if not checkpoint:
            print(f"\n💾 记忆状态：当前线程 {thread_id} 没有记忆")
            return

        messages = checkpoint.get('channel_values', {}).get('messages', [])
        print(f"\n💾 记忆状态：")
        print(f"   当前线程: {thread_id}")
        print(f"   记忆消息数: {len(messages)}")
        if messages:
            latest = messages[-1]
            content = getattr(latest, "content", "")
            if not isinstance(content, str):
                content = str(content)
            preview = content[:50] + ("..." if len(content) > 50 else "")
            print(f"   最近消息: {preview}")
    except Exception as e:
        print(f"❌ 获取记忆状态失败：{str(e)}")


def get_messages(thread_id: str = "user_session") -> List[Any]:
    """返回指定线程的消息列表，若不存在则为空。"""
    try:
        checkpoint = memory_checkpointer.get({"configurable": {"thread_id": thread_id}})
        if not checkpoint:
            return []
        return checkpoint.get("channel_values", {}).get("messages", []) or []
    except Exception:
        return []


__all__ = ["memory_checkpointer", "clear_memory", "show_memory_info", "get_messages"]
