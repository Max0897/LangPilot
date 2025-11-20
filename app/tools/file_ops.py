import os
import platform
import subprocess
from collections import deque
from pathlib import Path

from langchain.tools import tool


@tool
def open_file(file_path: str) -> str:
    """使用系统默认程序打开文件。"""
    try:
        system = platform.system()
        if not os.path.exists(file_path):
            return f"❌ 文件不存在：{file_path}"

        path_obj = Path(file_path).resolve()
        if system == "Windows":
            os.startfile(path_obj)  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.run(["open", str(path_obj)], check=True)
        elif system == "Linux":
            subprocess.run(["xdg-open", str(path_obj)], check=True)
        else:
            return f"❌ 不支持的操作系统：{system}"

        return f"✅ 文件打开成功：\n系统：{system}\n文件路径：{file_path}\n已用默认程序打开"

    except subprocess.CalledProcessError as e:
        error_msg = (e.stderr or str(e)).strip().replace("\r\n", "\n")
        return f"❌ 打开文件失败：\n系统：{platform.system()}\n文件路径：{file_path}\n错误：{error_msg}"
    except Exception as e:
        return f"⚠️ 未知错误：{str(e)}"


@tool
def read_file(file_path: str, offset: int = 0, limit: int = 4000) -> str:
    """安全读取文件内容，支持偏移和长度限制。"""
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

        slice_text = text[offset: offset + limit]
        truncated = "…(已截断)" if offset + limit < len(text) else ""
        return f"✅ 文件读取成功：{path}\n---内容---\n{slice_text}{truncated}"
    except Exception as e:
        return f"⚠️ 读取文件失败：{str(e)}"


@tool
def list_dir(path: str = ".", depth: int = 1, show_hidden: bool = False) -> str:
    """列出目录结构，支持深度与隐藏文件开关。"""
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
        max_entries = 400
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
    """查看文件末尾若干行内容。"""
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


__all__ = ["open_file", "read_file", "list_dir", "tail_file"]
