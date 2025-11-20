import os
import platform
import webbrowser
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from langchain.tools import tool


@tool
def open_browser(search_query: str = None, url: str = None) -> str:
    """打开默认浏览器访问指定 URL 或搜索内容。"""
    try:
        if search_query and url:
            return "❌ 参数错误：只能提供搜索内容或URL中的一个"
        if not search_query and not url:
            return "❌ 参数错误：必须提供搜索内容或URL"

        target_url = url
        if search_query:
            encoded_query = quote(search_query, encoding="utf-8")
            target_url = f"https://www.baidu.com/s?wd={encoded_query}"

        current_system = platform.system()
        if current_system == "Linux" and not os.environ.get("DISPLAY"):
            return f"⚠️ 当前为无图形环境，无法直接打开浏览器。请手动访问：{target_url}"

        success = webbrowser.open(target_url)
        if success:
            label = "搜索内容" if search_query else "网址"
            return f"✅ 浏览器已打开：\n{label}：{search_query or url}\n访问链接：{target_url}"
        return f"❌ 打开浏览器失败：无法启动默认浏览器，链接：{target_url}"

    except Exception as e:
        return f"⚠️ 打开浏览器时发生错误：{str(e)}"


@tool
def http_request(
    method: str,
    url: str,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 15,
) -> str:
    """通用 HTTP 请求工具，支持 GET/POST 等方法。"""
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
    """拉取网页并按 CSS 选择器提取内容。"""
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


__all__ = ["open_browser", "http_request", "parse_webpage"]
