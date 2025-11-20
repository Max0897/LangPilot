from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from app.config import ensure_deepseek_api_key
from app.prompts import SYSTEM_PROMPT
from app.tools import TOOLS

from .memory import memory_checkpointer


def get_agent():
    """延迟创建模型与 Agent，避免导入时初始化外部服务。"""
    ensure_deepseek_api_key()

    llm = init_chat_model(
        model="deepseek-chat",
        model_provider="deepseek",
        temperature=0,
    )

    return create_agent(
        model=llm,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=memory_checkpointer,
        debug=False,
    )


__all__ = ["get_agent"]
