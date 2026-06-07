"""Cookie、tried_items 持久化工具函数"""

import json
import os
import time
from typing import Dict, List, Optional

from buff.log import logger

COOKIE_FILE = "cookie.txt"


def save_cookie_to_file(cookie_str: str, file_path: str = COOKIE_FILE):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(cookie_str)
    logger.info("Cookie 已保存到 %s", file_path)


def load_cookie_from_file(file_path: str = COOKIE_FILE) -> Optional[str]:
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cookie = f.read().strip()
            if cookie:
                logger.info("从 %s 加载 Cookie", file_path)
                return cookie
        except IOError:
            pass
    return None


def load_cookie(file_path=None) -> Optional[str]:
    # 文件优先：用户更新 cookie.txt 后立即生效，避免继承父进程的旧环境变量
    file_cookie = load_cookie_from_file(file_path or COOKIE_FILE)
    if file_cookie:
        return file_cookie
    return os.environ.get("BUFF_COOKIE")


def save_cookie(cookie_str: str, file_path=None):
    os.environ["BUFF_COOKIE"] = cookie_str
    save_cookie_to_file(cookie_str, file_path or COOKIE_FILE)


def prompt_cookie(client) -> str:
    logger.info("需要输入 BUFF 网站的 Cookie")
    logger.info("操作步骤:")
    logger.info("  1. 浏览器登录 buff.163.com")
    logger.info("  2. F12 -> 网络 -> 刷新页面 -> 复制任意请求的 Cookie")
    logger.info("-" * 50)
    while True:
        cookie_str = input("请输入 Cookie: ").strip()
        if client.set_cookie(cookie_str) and client.test_login():
            save_cookie(cookie_str)
            return cookie_str
        logger.warning("Cookie 无效，请重试")
        logger.info("-" * 50)


def make_tried_item(
    goods_id: str,
    order_id: str,
    price: float,
    seller_id: str = "",
    status: str = "attempted",
    error: Optional[str] = None,
    bill_order_id: Optional[str] = None,
) -> Dict:
    """创建统一格式的 tried_item 记录"""
    return {
        "goods_id": goods_id,
        "order_id": order_id,
        "price": price,
        "seller_id": seller_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "error": error,
        "bill_order_id": bill_order_id,
    }


def save_tried_items(tried_items: List[Dict], file_path: str = "purchases.json"):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(tried_items, f, ensure_ascii=False, indent=2)
    logger.info("已保存 %d 条记录到 %s", len(tried_items), file_path)


def load_tried_items(file_path: str = "purchases.json") -> List[Dict]:
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []
