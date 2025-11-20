import platform

from app.agent import clear_memory, run_agent, show_memory_info
from app.config import ensure_deepseek_api_key


def main() -> None:
    """命令行入口，提供交互式助手体验。"""
    ensure_deepseek_api_key()
    print("💡 LangPilot 智能命令助手已启动")
    print(f"📌 当前系统：{platform.system()}（自动适配命令与编码）")
    print("📌 支持功能：命令执行、文件/目录查看、文件打开、HTTP 请求、网页解析、对话记忆")
    print("📌 特殊命令：")
    print("   - '记忆状态'：查看当前记忆状态")
    print("   - '清除记忆'：清除当前对话记忆")
    print("   - 'exit/quit/退出'：关闭助手")
    print("   - 按 Ctrl+C 可安全退出")
    print("   - 可指定线程ID以区分会话，如输入：切换线程 demo")
    print()

    current_thread_id = "user_session"

    while True:
        try:
            user_query = input("🧠 请输入你的需求 > ").strip()

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

            run_agent(user_query, thread_id=current_thread_id)

        except KeyboardInterrupt:
            print("\n\n👋 检测到中断信号，正在安全退出...")
            break
        except EOFError:
            print("\n\n👋 输入结束，正在安全退出...")
            break
        except Exception as e:
            print(f"\n⚠️ 发生意外错误: {str(e)}")
            print("🔧 程序将继续运行，请重新输入...")
            continue


__all__ = ["main"]
