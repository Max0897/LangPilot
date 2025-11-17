# LangPilot

基于 LangChain/LangGraph 的多工具命令助手，支持命令执行、文件/目录查看、文件打开、HTTP 请求、网页解析以及对话记忆。

## 快速开始
- 安装依赖：`pip install -r requirements.txt`
- 配置环境变量：复制 `.env.example` 为 `.env`，填入 `DEEPSEEK_API_KEY`。
- 运行：`python main.py`

## 配置
`.env` 文件示例：
```
DEEPSEEK_API_KEY=你的API密钥
```

## 可用工具
- `run_command`：按系统自动选择命令执行方式。
- `open_file`：用系统默认程序打开文件。
- `open_browser`：打开网址或百度搜索关键词。
- `check_serial_number`：简单序列号查询。
- `read_file` / `tail_file` / `list_dir`：安全查看文件与目录。
- `http_request`：通用 HTTP 访问。
- `parse_webpage`：按 CSS 选择器提取网页内容。

## 交互提示
启动后可输入自然语言需求；支持指令：
- `记忆状态`：查看当前记忆
- `清除记忆`：清除记忆
- `切换线程 <name>`：切换对话线程
- `exit/quit/退出`：退出程序
