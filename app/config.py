import getpass
import locale
import os
from pathlib import Path

from dotenv import load_dotenv, set_key

# 定义项目根目录与 .env 路径，集中管理环境变量
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)


def ensure_deepseek_api_key() -> str:
    """若未设置 DEEPSEEK_API_KEY，则提示一次并写入 .env。"""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if api_key:
        return api_key

    prompt = "请输入 DeepSeek API 密钥："
    while True:
        user_input = getpass.getpass(prompt).strip()
        if user_input:
            break
        print("❌ 密钥不能为空，请重新输入。")

    os.environ["DEEPSEEK_API_KEY"] = user_input

    try:
        ENV_PATH.touch(exist_ok=True)
        set_key(str(ENV_PATH), "DEEPSEEK_API_KEY", user_input)
    except Exception as exc:
        print(f"⚠️ 无法写入 .env 文件：{exc}")

    return user_input


def get_system_encoding() -> str:
    """根据系统返回首选编码，用于 subprocess 输出解码。"""
    preferred = locale.getpreferredencoding(False)
    if preferred:
        return preferred
    return "utf-8"


__all__ = ["ensure_deepseek_api_key", "get_system_encoding", "BASE_DIR", "ENV_PATH"]
