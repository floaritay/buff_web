"""Cookie 和 tried_items 持久化工具函数"""

import os
import json
from typing import Dict, List, Optional

COOKIE_FILE = "cookie.txt"


def save_cookie_to_file(cookie_str: str, file_path: str = COOKIE_FILE):
    """保存 Cookie 到文件"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(cookie_str)
    print(f"Cookie 已保存到 {file_path}")


def load_cookie_from_file(file_path: str = COOKIE_FILE) -> Optional[str]:
    """从文件加载 Cookie"""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cookie = f.read().strip()
            if cookie:
                print(f"从 {file_path} 加载 Cookie")
                return cookie
        except IOError:
            pass
    return None


def load_cookie(file_path=None) -> Optional[str]:
    """加载 Cookie：优先环境变量，其次文件"""
    env_cookie = os.environ.get("BUFF_COOKIE")
    if env_cookie:
        return env_cookie
    return load_cookie_from_file(file_path or COOKIE_FILE)


def save_cookie(cookie_str: str, file_path=None):
    """保存 Cookie：写入环境变量和文件"""
    os.environ["BUFF_COOKIE"] = cookie_str
    save_cookie_to_file(cookie_str, file_path or COOKIE_FILE)


def prompt_cookie(client) -> str:
    """交互式输入 Cookie 并验证"""
    print("需要输入 BUFF 网站的 Cookie")
    print("操作步骤:")
    print("  1. 浏览器登录 buff.163.com")
    print("  2. F12 -> 网络 -> 刷新页面 -> 复制任意请求的 Cookie")
    print("-" * 50)
    while True:
        cookie_str = input("请输入 Cookie: ").strip()
        if client.set_cookie(cookie_str) and client.test_login():
            save_cookie(cookie_str)
            return cookie_str
        print("Cookie 无效，请重试")
        print("-" * 50)


def save_tried_items(tried_items: List[Dict], file_path: str = "tried_items.json"):
    """保存已尝试购买的商品记录"""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(tried_items, f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(tried_items)} 条记录到 {file_path}")


def load_tried_items(file_path: str = "tried_items.json") -> List[Dict]:
    """从文件加载已尝试购买的商品记录"""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []
