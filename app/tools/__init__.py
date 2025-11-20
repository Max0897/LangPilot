from .system import run_command
from .file_ops import open_file, read_file, list_dir, tail_file
from .web import open_browser, http_request, parse_webpage

TOOLS = [
    run_command,
    open_file,
    open_browser,
    read_file,
    list_dir,
    tail_file,
    http_request,
    parse_webpage,
]

__all__ = [
    "run_command",
    "open_file",
    "open_browser",
    "read_file",
    "list_dir",
    "tail_file",
    "http_request",
    "parse_webpage",
    "TOOLS",
]
