import platform
import subprocess

from langchain.tools import tool

from app.config import get_system_encoding


@tool
def run_command(command: str) -> str:
    """执行系统命令（自动识别 OS 并设置编码）。"""
    try:
        system = platform.system()
        shell = system == "Windows"
        cmd_encoding = get_system_encoding()

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
            errors="ignore",
        )

        stdout = result.stdout.strip().replace("\r\n", "\n")
        return f"✅ 命令执行成功：\n系统：{system}\n命令：{command}\n结果：\n{stdout}"

    except subprocess.CalledProcessError as e:
        error_msg = (e.stderr or str(e)).strip().replace("\r\n", "\n")
        return f"❌ 命令执行失败：\n系统：{platform.system()}\n命令：{command}\n错误：{error_msg}"
    except Exception as e:
        return f"⚠️ 未知错误：{str(e)}"


__all__ = ["run_command"]
