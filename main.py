import subprocess
import getpass
import os
import platform
import webbrowser
import locale
from pathlib import Path
from collections import deque
from typing import Dict, Any, Optional
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

# =========================================================
# 1️⃣ 环境初始化
# =========================================================
load_dotenv()
# 延迟要求 API 密钥：仅在需要时提示，避免作为模块被导入时阻塞

# =========================================================
# 2️⃣ 修复核心：根据系统自动获取命令行编码
# =========================================================
def get_system_encoding() -> str:
    """根据操作系统自动返回命令行输出的编码（解决中文解码问题）"""
    system = platform.system()
    # 优先使用 locale 真实输出编码，回退 utf-8
    preferred = locale.getpreferredencoding(False)
    if preferred:
        return preferred
    return "utf-8"


# =========================================================
# 3️⃣ 定义工具函数
# =========================================================
@tool
def run_command(command: str) -> str:
    """
    执行系统命令（自动识别 Windows/Linux/macOS + 适配编码）。
        参数：command - 合法命令（如 Windows 用 dir，Linux/macOS 用 ls）
        """
    try:
        system = platform.system()
        shell = system == "Windows"
        cmd_encoding = get_system_encoding()

        # Windows 下允许 shell=True 以支持内建命令，其他系统用 shlex 分词确保安全
        if shell:
            run_args = command
        else:
            import shlex
            run_args = shlex.split(command)

        result = subprocess.run(
            run_args,
            shell=shell,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding=cmd_encoding,
            errors="ignore"
        )

        stdout = result.stdout.strip().replace("\r\n", "\n")
        return f"✅ 命令执行成功：\n系统：{system}\n命令：{command}\n结果：\n{stdout}"

    except subprocess.CalledProcessError as e:
        error_msg = (e.stderr or str(e)).strip().replace("\r\n", "\n")
        return f"❌ 命令执行失败：\n系统：{system}\n命令：{command}\n错误：{error_msg}"
    except Exception as e:
        return f"⚠️ 未知错误：{str(e)}"


@tool
def open_file(file_path: str) -> str:
    """
    用系统默认程序打开指定文件（自动适配不同操作系统）
        参数：file_path - 文件的路径（相对路径或绝对路径）
        """
    try:
        system = platform.system()
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return f"❌ 文件不存在：{file_path}"

        # 根据系统生成打开命令，避免 shell 注入
        path_obj = Path(file_path).resolve()
        if system == "Windows":
            os.startfile(path_obj)  # type: ignore[attr-defined]
        elif system == "Darwin":  # macOS
            subprocess.run(["open", str(path_obj)], check=True)
        elif system == "Linux":
            subprocess.run(["xdg-open", str(path_obj)], check=True)
        else:
            return f"❌ 不支持的操作系统：{system}"

        return f"✅ 文件打开成功：\n系统：{system}\n文件路径：{file_path}\n已用默认程序打开"

    except subprocess.CalledProcessError as e:
        error_msg = (e.stderr or str(e)).strip().replace("\r\n", "\n")
        return f"❌ 打开文件失败：\n系统：{system}\n文件路径：{file_path}\n错误：{error_msg}"
    except Exception as e:
        return f"⚠️ 未知错误：{str(e)}"


@tool
def open_browser(search_query: str = None, url: str = None) -> str:
    """
    打开默认浏览器访问指定URL或搜索指定内容（优先使用百度搜索）
    参数说明：
    - search_query: 要搜索的内容（如"天气"），会自动转为百度搜索链接
    - url: 直接访问的网址（如"https://www.baidu.com"）
    注意：search_query和url只能提供一个参数
    """
    try:
        # 验证参数合法性
        if search_query and url:
            return "❌ 参数错误：只能提供搜索内容或URL中的一个"
        if not search_query and not url:
            return "❌ 参数错误：必须提供搜索内容或URL"

        # 构建访问地址（使用urllib.parse.quote进行URL编码）
        target_url = url
        if search_query:
            # 对搜索词进行URL编码（处理中文等特殊字符）
            encoded_query = quote(search_query, encoding='utf-8')
            target_url = f"https://www.baidu.com/s?wd={encoded_query}"

        # 检查是否在无头环境
        if system == "Linux" and not os.environ.get("DISPLAY"):
            return f"⚠️ 当前为无图形环境，无法直接打开浏览器。请手动访问：{target_url}"

        success = webbrowser.open(target_url)
        if success:
            return f"✅ 浏览器已打开：\n{'搜索内容' if search_query else '网址'}：{search_query or url}\n访问链接：{target_url}"
        return f"❌ 打开浏览器失败：无法启动默认浏览器，链接：{target_url}"

    except Exception as e:
        return f"⚠️ 打开浏览器时发生错误：{str(e)}"

@tool
def read_file(file_path: str, offset: int = 0, limit: int = 4000) -> str:
    """
    安全读取文件内容，支持偏移和最大输出长度限制，避免一次性加载过大文件
    - file_path: 要读取的文件路径
    - offset: 起始字符位置，默认从开头读取
    - limit: 最大读取长度，默认4000字符
    """
    try:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return f"❌ 文件不存在：{path}"
        if not path.is_file():
            return f"❌ 不是文件：{path}"

        if offset < 0 or limit <= 0:
            return "❌ 参数错误：offset需>=0且limit需>0"

        text = path.read_text(encoding="utf-8", errors="ignore")
        if offset >= len(text):
            return f"❌ 起始位置超出文件长度（长度：{len(text)}）"

        slice_text = text[offset:offset + limit]
        truncated = "…(已截断)" if offset + limit < len(text) else ""
        return f"✅ 文件读取成功：{path}\n---内容---\n{slice_text}{truncated}"
    except Exception as e:
        return f"⚠️ 读取文件失败：{str(e)}"


@tool
def list_dir(path: str = ".", depth: int = 1, show_hidden: bool = False) -> str:
    """
    列出目录结构，支持深度限制与隐藏文件开关
    - path: 目标目录，默认为当前目录
    - depth: 深度（>=1），避免递归过深
    - show_hidden: 是否显示以.开头的文件
    """
    try:
        root = Path(path).expanduser().resolve()
        if not root.exists():
            return f"❌ 目录不存在：{root}"
        if not root.is_dir():
            return f"❌ 不是目录：{root}"
        if depth < 1:
            return "❌ 参数错误：depth 需>=1"

        output_lines = [f"📂 {root}"]
        queue = deque([(root, 0)])
        max_entries = 400  # 避免输出过长
        count = 0

        while queue:
            current, level = queue.popleft()
            if level >= depth:
                continue
            try:
                entries = sorted(current.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
            except PermissionError:
                output_lines.append("  " * (level + 1) + f"🔒 无权限访问：{current}")
                continue

            for entry in entries:
                if not show_hidden and entry.name.startswith("."):
                    continue
                prefix = "  " * (level + 1)
                marker = "📄" if entry.is_file() else "📁"
                output_lines.append(f"{prefix}{marker} {entry.name}")
                count += 1
                if count >= max_entries:
                    output_lines.append("... （输出已截断）")
                    return "\n".join(output_lines)
                if entry.is_dir():
                    queue.append((entry, level + 1))

        return "\n".join(output_lines)
    except Exception as e:
        return f"⚠️ 列目录失败：{str(e)}"


@tool
def tail_file(file_path: str, lines: int = 200) -> str:
    """
    读取文件末尾若干行，默认200行，用于快速查看日志
    - file_path: 文件路径
    - lines: 行数，最大1000
    """
    try:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return f"❌ 文件不存在：{path}"
        if not path.is_file():
            return f"❌ 不是文件：{path}"
        if lines <= 0 or lines > 1000:
            return "❌ 参数错误：lines 需在 1~1000 之间"

        buffer = deque(maxlen=lines)
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                buffer.append(line.rstrip("\n"))

        content = "\n".join(buffer)
        return f"✅ 文件尾部（{lines}行内）：{path}\n---内容---\n{content}"
    except Exception as e:
        return f"⚠️ 读取文件尾失败：{str(e)}"


@tool
def http_request(
    method: str,
    url: str,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 15,
) -> str:
    """
    通用 HTTP 请求工具，支持 GET/POST 等方法
    - method: HTTP 方法，如 GET、POST
    - url: 目标地址
    - params/data/headers: 可选参数
    - timeout: 超时时间（秒）
    """
    try:
        method_upper = method.upper()
        if method_upper not in {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}:
            return "❌ 不支持的 HTTP 方法"

        resp = requests.request(
            method=method_upper,
            url=url,
            params=params,
            data=data,
            headers=headers,
            timeout=timeout,
        )

        content_type = resp.headers.get("Content-Type", "").lower()
        body = resp.text
        if "application/json" in content_type:
            try:
                body = resp.json()
            except Exception:
                body = resp.text

        return (
            "✅ 请求成功\n"
            f"URL: {resp.url}\n"
            f"状态码: {resp.status_code}\n"
            f"Content-Type: {content_type or '未知'}\n"
            f"响应: {body if isinstance(body, str) else body}"
        )
    except requests.exceptions.Timeout:
        return f"❌ 请求超时（{timeout}s）：{url}"
    except requests.exceptions.RequestException as e:
        return f"❌ 请求失败：{str(e)}"
    except Exception as e:
        return f"⚠️ 未知错误：{str(e)}"


@tool
def parse_webpage(
    url: str,
    selector: str = "body",
    text_only: bool = True,
    timeout: int = 10,
    max_chars: int = 4000,
) -> str:
    """
    拉取网页并按 CSS 选择器提取内容
    - url: 目标页面（必须 http/https）
    - selector: CSS 选择器，默认 body
    - text_only: 是否只保留文本
    - timeout: 请求超时（秒）
    - max_chars: 最大返回长度，超出会截断
    """
    try:
        if not url.lower().startswith(("http://", "https://")):
            return "❌ URL 需以 http:// 或 https:// 开头"

        resp = requests.get(url, timeout=timeout)
        content_type = resp.headers.get("Content-Type", "")
        if resp.status_code != 200:
            return f"❌ 请求失败：{resp.status_code} {resp.reason}"

        html = resp.text
        soup = BeautifulSoup(html, "html.parser")
        nodes = soup.select(selector)
        if not nodes:
            return f"❌ 未匹配到任何节点，选择器：{selector}"

        parts = []
        for node in nodes:
            text = node.get_text(separator="\n", strip=True) if text_only else str(node)
            if text:
                parts.append(text)
            if sum(len(p) for p in parts) > max_chars:
                break

        if not parts:
            return "❌ 目标节点内容为空"

        combined = "\n\n".join(parts)
        truncated = combined[:max_chars]
        suffix = "\n…(已截断)" if len(combined) > max_chars else ""
        return (
            "✅ 网页解析成功\n"
            f"URL: {resp.url}\n"
            f"Content-Type: {content_type}\n"
            f"选择器: {selector}\n"
            f"文本模式: {text_only}\n"
            f"---内容---\n{truncated}{suffix}"
        )
    except requests.exceptions.Timeout:
        return f"❌ 请求超时（{timeout}s）：{url}"
    except requests.exceptions.RequestException as e:
        return f"❌ 请求失败：{str(e)}"
    except Exception as e:
        return f"⚠️ 解析失败：{str(e)}"

# =========================================================
# 4️⃣ 定义系统提示词（增强记忆功能说明）
# =========================================================
system = platform.system()
system_prompt = f"""
你是一个智能命令执行助手，严格适配当前操作系统，并且具有对话记忆能力。
当前操作系统：{system}
- 若为 Windows：仅生成 cmd 命令（如查看目录用 dir，查看文件用 type），禁止用 Linux 命令；
- 若为 Linux/macOS：仅生成 Bash 命令（如查看目录用 ls，查看文件用 cat），禁止用 Windows 命令。

记忆能力说明：
- 你可以记住之前的对话历史和用户偏好
- 当用户提到"之前"、"上次"、"刚才"等词语时，请参考对话历史来理解上下文
- 你可以基于之前的交互提供更个性化的服务

文件打开功能说明：
- 当用户需要打开文件时，使用 open_file 工具，无需手动生成命令
- 支持相对路径（如 "test.txt"）和绝对路径（如 "C:\\data\\file.pdf" 或 "/home/user/doc.txt"）
- 会自动调用系统默认程序打开对应类型的文件

浏览器功能说明：
- 当用户需要查询信息或访问网页时，使用open_browser工具
- 可以直接指定网址（如"https://www.baidu.com"）
- 也可以提供搜索关键词（如"今天天气"），会自动使用百度搜索
- 无需手动生成浏览器命令，工具会自动调用系统默认浏览器

网页解析功能说明：
- 需要提取网页内容时，使用 parse_webpage，支持 CSS 选择器和只文本模式
-- 默认选择器 body，可自定义，如 "article"、"div.content"

文件与目录功能说明：
- 需要查看文件时，使用 read_file（支持offset/limit）或 tail_file（查看末尾行）
- 需要浏览目录时，使用 list_dir（支持深度与隐藏文件开关）

网络请求说明：
- 通用 HTTP 访问使用 http_request，支持 GET/POST 等方法和超时时间

必须遵守的规则：
1. 用户需求优先用单条安全命令实现；
2. 生成命令后通过 run_command 工具执行，打开文件用 open_file 工具；
   查看文件/目录/日志用 read_file、list_dir、tail_file，HTTP 访问用 http_request；
   解析网页内容用 parse_webpage；
3. 绝对禁止生成高危命令（如 rm、sudo、shutdown、del、format 等）；
4. 若用户需求无法用安全命令实现，直接回复"该需求涉及高危操作，暂不支持"；
5. 利用对话记忆提供更好的服务体验；
6. 最终结果用中文整理，清晰展示命令、系统和执行结果。
"""

# =========================================================
# 5️⃣ 创建记忆检查点和 Agent 工厂
# =========================================================
memory_checkpointer = InMemorySaver()


def get_agent():
    """延迟创建模型与 Agent，避免导入时初始化外部服务。"""
    if not os.environ.get("DEEPSEEK_API_KEY"):
        os.environ["DEEPSEEK_API_KEY"] = getpass.getpass("请输入 DeepSeek API 密钥：")

    llm = init_chat_model(
        model="deepseek-chat",
        model_provider="deepseek",
        temperature=0
    )

    return create_agent(
        model=llm,
        tools=[
            run_command,
            open_file,
            open_browser,
            read_file,
            list_dir,
            tail_file,
            http_request,
            parse_webpage,
        ],
        system_prompt=system_prompt,
        checkpointer=memory_checkpointer,
        debug=False,  # 默认关闭 debug，避免泄漏敏感信息
    )


# =========================================================
# 7️⃣ 交互函数（增强记忆功能）
# =========================================================
def run_agent(user_input: str, thread_id: str = "user_session", show_trace: bool = True):
    """
    执行一条自然语言命令并展示结果，支持对话记忆
    """
    try:
        # 配置记忆线程ID
        config = {
            "configurable": {
                "thread_id": thread_id  # 使用固定线程ID保持对话记忆
            }
        }

        agent = get_agent()

        # 调用Agent，传入配置以保持记忆
        result = agent.invoke(
            input={"messages": [{"role": "user", "content": user_input}]},
            config=config
        )

        if show_trace and "messages" in result:
            print("\n📜 === 执行过程 ===")
            for idx, msg in enumerate(result["messages"], 1):
                role = getattr(msg, "type", None) or getattr(msg, "role", None)
                role_label = "系统提示" if getattr(msg, "role", "") == "system" else "用户输入" if getattr(msg, "role", "") == "user" else "模型响应"
                content = getattr(msg, "content", "")
                if not isinstance(content, str):
                    content = str(content)
                content = content.strip()
                if content:
                    print(f"\n[{role_label or role or '消息'}]\n{content[:2000]}{'...（已截断）' if len(content) > 2000 else ''}")

        if "messages" in result and len(result["messages"]) > 0:
            final_msg = result["messages"][-1]
            final_output = getattr(final_msg, "content", str(final_msg)).strip()
        else:
            final_output = result.get("output", str(result)).strip()

        print("\n" + "=" * 60)
        print("✅ 最终结果：")
        print(final_output)
        print("=" * 60 + "\n")
        return final_output

    except Exception as e:
        print(f"\n❌ 交互错误：{str(e)}\n")
        return ""


def clear_memory(thread_id: str = "user_session"):
    """
    清除指定线程的记忆
    """
    try:
        memory_checkpointer.delete({"configurable": {"thread_id": thread_id}})
        print(f"🧹 已清除对话记忆 (线程: {thread_id})")
    except Exception as e:
        print(f"❌ 清除记忆失败：{str(e)}")


def show_memory_info(thread_id: str = "user_session"):
    """
    显示记忆状态信息
    """
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


# =========================================================
# 8️⃣ 交互循环（增强记忆功能）
# =========================================================
if __name__ == "__main__":
    print("💡 DeepSeek 智能命令助手已启动")
    print(f"📌 当前系统：{platform.system()}（自动适配命令与编码）")
    print("📌 支持功能：命令执行、文件/目录查看、文件打开、HTTP 请求、网页解析、对话记忆")
    print("📌 特殊命令：")
    print("   - '记忆状态'：查看当前记忆状态")
    print("   - '清除记忆'：清除当前对话记忆")
    print("   - 'exit/quit/退出'：关闭助手")
    print("   - 按 Ctrl+C 可安全退出")
    print("   - 可指定线程ID以区分会话，如输入：切换线程 demo")
    print()

    # 初始化对话线程
    current_thread_id = "user_session"

    while True:
        try:
            user_query = input("🧠 请输入你的需求 > ").strip()

            # 特殊命令处理
            if user_query.lower() in ["exit", "quit", "退出"]:
                print("👋 再见！助手已退出。")
                break
            elif user_query.lower() in ["清除记忆", "clear memory"]:
                clear_memory(current_thread_id)
                continue
            elif user_query.lower() in ["记忆状态", "memory status"]:
                show_memory_info(current_thread_id)
                continue
            elif user_query.lower().startswith("切换线程"):
                parts = user_query.split(maxsplit=1)
                if len(parts) == 2 and parts[1]:
                    current_thread_id = parts[1]
                    print(f"🔀 已切换到线程：{current_thread_id}")
                else:
                    print("❌ 请输入线程名，如：切换线程 demo")
                continue
            elif not user_query:
                continue

            # 执行用户查询
            run_agent(user_query, thread_id=current_thread_id)

        except KeyboardInterrupt:
            # 处理 Ctrl+C 或编辑器停止按钮
            print("\n\n👋 检测到中断信号，正在安全退出...")
            break
        except EOFError:
            # 处理其他输入中断情况
            print("\n\n👋 输入结束，正在安全退出...")
            break
        except Exception as e:
            # 处理其他意外错误，但不终止程序
            print(f"\n⚠️ 发生意外错误: {str(e)}")
            print("🔧 程序将继续运行，请重新输入...")
            continue
