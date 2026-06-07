"""BuffClient 基类 - session 管理、认证、CSRF 处理、购买流程"""

import json
import os
import random
import re
import sys
import time
from collections import namedtuple
from typing import Dict, List, Optional

import requests

from buff.log import logger, setup_logging
from buff.retry import api_request

_CSRFEntry = namedtuple("_CSRFEntry", ["token", "timestamp"])
_logging_initialized = False


class BuffClient:
    """BUFF 客户端基类

    提供：session 管理、cookie 设置、登录测试、CSRF 处理、
    统一的 get_sell_orders / buy_item 购买流程。
    """

    BASE_URL = "https://buff.163.com"

    def __init__(self, game: str = "csgo", verbose: bool = False, quiet: bool = False):
        global _logging_initialized
        if not _logging_initialized:
            setup_logging(verbose=verbose, quiet=quiet)
            _logging_initialized = True

        self.game = game
        self.dry_run = False
        self._csrf_cache: Dict[str, _CSRFEntry] = {}
        self._db_conn = None

        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
            "Referer": f"https://buff.163.com/market/{game}",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Microsoft Edge";v="122"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        self.session.headers.update(self.headers)

    # ── Cookie 管理 ──────────────────────────────────────────────

    def set_cookie(self, cookie_str: str) -> bool:
        if not cookie_str:
            logger.error("Cookie 不能为空")
            return False

        cookies = {}
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                try:
                    key, value = item.split("=", 1)
                    cookies[key] = value
                except Exception:
                    pass

        if not cookies:
            logger.error("无法解析 Cookie")
            return False

        required = ["session", "remember_me", "_ntes"]
        if not any(key in cookies for key in required):
            logger.warning("Cookie 可能缺少关键项（session / remember_me / _ntes）")

        self.session.cookies.update(cookies)
        logger.info("Cookie 设置成功，解析到 %d 项", len(cookies))
        return True

    def test_login(self) -> bool:
        try:
            url = f"{self.BASE_URL}/api/market/goods?game={self.game}&page_num=1&page_size=10"
            resp = self._api_request("GET", url, timeout=10)
            if resp.status_code == 200 and resp.json().get("code") == "OK":
                logger.info("登录状态正常")
                return True
            logger.warning("登录状态异常")
            return False
        except Exception as e:
            logger.error("测试登录失败: %s", e)
            return False

    def validate_login_or_prompt(self) -> bool:
        """检查登录状态，失效时交互式提示输入 cookie"""
        from buff.utils import load_cookie, prompt_cookie

        cookie_str = load_cookie()
        if cookie_str and self.set_cookie(cookie_str) and self.test_login():
            return True

        # 非交互环境（如仪表盘子进程）无法输入 cookie，直接退出
        if os.environ.get("BUFF_NON_INTERACTIVE") or not sys.stdin.isatty():
            logger.error("Cookie 无效或已过期，请更新 cookie.txt 后重试")
            logger.error("操作步骤: 浏览器登录 buff.163.com → F12 → 网络 → 复制任意请求的 Cookie → 粘贴到 cookie.txt")
            sys.exit(1)

        prompt_cookie(self)
        return self.test_login()

    # ── 统一请求 ─────────────────────────────────────────────────

    def _api_request(self, method: str, url: str, **kwargs) -> requests.Response:
        return api_request(self.session, method, url, **kwargs)

    # ── CSRF 处理 ────────────────────────────────────────────────

    def _extract_csrf_token(self, html_content: str, session: requests.Session) -> str:
        patterns = [
            (r'<meta name="csrf-token" content="([^"]+)"', "meta 标签"),
            (r'csrf_token\s*=\s*["\']([^"\']+)["\']', "script 变量"),
            (r'window\.csrf_token\s*=\s*["\']([^"\']+)["\']', "window.csrf_token"),
        ]
        for pattern, source in patterns:
            m = re.search(pattern, html_content)
            if m:
                token = m.group(1)
                logger.debug("从%s获取 CSRF token: %s...", source, token[:20])
                return token

        for cookie in session.cookies:
            if cookie.name == "csrf_token":
                logger.debug("从 cookie 获取 CSRF token: %s...", cookie.value[:20])
                return cookie.value

        m = re.search(r'<input[^>]+name="csrfmiddlewaretoken"[^>]+value="([^"]+)"', html_content)
        if m:
            logger.debug("从表单隐藏字段获取 CSRF token: %s...", m.group(1)[:20])
            return m.group(1)

        return ""

    def _get_browser_headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Microsoft Edge";v="122"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        }

    def _init_buy_session(self, goods_id: str):
        """初始化购买会话，返回 (new_session, csrf_token, goods_page_url)"""
        if self.dry_run:
            logger.info("[DRY RUN] 跳过会话初始化 (goods_id=%s)", goods_id)
            mock_session = requests.Session()
            return mock_session, "dry_run_token", f"{self.BASE_URL}/goods/{goods_id}"

        current_cookies = self.session.cookies.get_dict()

        new_session = requests.Session()
        new_session.headers.update(self._get_browser_headers())

        for key, value in current_cookies.items():
            new_session.cookies.set(key, value, domain="buff.163.com", path="/")

        logger.info("访问 BUFF 主页...")
        new_session.get(self.BASE_URL, timeout=15)
        time.sleep(1.5)

        market_url = f"{self.BASE_URL}/market/{self.game}"
        logger.info("访问市场页面: %s", market_url)
        new_session.get(market_url, timeout=15)
        time.sleep(1.5)

        goods_page_url = f"{self.BASE_URL}/goods/{goods_id}"
        logger.info("访问商品页面: %s", goods_page_url)
        goods_response = new_session.get(goods_page_url, timeout=15)
        time.sleep(1.5)

        csrf_token = ""
        if goods_response.status_code == 200:
            csrf_token = self._extract_csrf_token(goods_response.text, new_session)

        if not csrf_token:
            logger.warning("未能获取 CSRF token")

        self._csrf_cache[goods_id] = _CSRFEntry(csrf_token, time.time())

        return new_session, csrf_token, goods_page_url

    def _refresh_csrf_token(self, new_session: requests.Session, goods_page_url: str, current_csrf: str) -> str:
        logger.debug("刷新 CSRF token...")
        goods_response = new_session.get(goods_page_url, timeout=15)
        time.sleep(1)

        if goods_response.status_code == 200:
            fresh = self._extract_csrf_token(goods_response.text, new_session)
            if fresh:
                return fresh
        return current_csrf

    def _build_buy_headers(self, csrf_token: str, goods_page_url: str) -> dict:
        headers = {
            **self._get_browser_headers(),
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive",
            "Origin": self.BASE_URL,
            "Referer": goods_page_url,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        if csrf_token:
            headers["X-CSRFToken"] = csrf_token
            headers["X-CSRF-Token"] = csrf_token
            headers["Csrf-Token"] = csrf_token
        return headers

    # ── 订单相关 ─────────────────────────────────────────────────

    def _ask_seller_to_send_offer(self, new_session: requests.Session, headers: dict, bill_order_id) -> bool:
        url = f"{self.BASE_URL}/api/market/bill_order/ask_seller_to_send_offer"
        data = {"bill_orders": [bill_order_id], "game": self.game, "steamid": None}

        resp = new_session.post(url, json=data, headers=headers, timeout=15)
        logger.debug("请求卖家报价状态码: %d", resp.status_code)

        if resp.status_code == 200:
            result = resp.json()
            if result.get("code") == "OK":
                logger.info("请求卖家发送报价成功")
                return True
            logger.warning("请求卖家发送报价失败: %s", result.get("msg", "未知错误"))
        else:
            logger.warning("请求卖家发送报价 HTTP %d", resp.status_code)
        return False

    def _find_bill_order_id(self, buy_result: dict, new_session: requests.Session, headers: dict):
        for field in ["bill_order_id", "order_id", "id"]:
            bill_order_id = buy_result.get("data", {}).get(field)
            if bill_order_id:
                logger.debug("从 %s 获取订单号: %s", field, bill_order_id)
                return bill_order_id

        logger.info("尝试获取最新订单...")
        url = f"{self.BASE_URL}/api/market/bill_order"
        params = {"game": self.game, "page_num": 1, "status": "pending"}
        resp = new_session.get(url, params=params, headers=headers, timeout=15)

        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "OK":
                orders = data.get("data", {}).get("items", [])
                if orders:
                    oid = orders[0].get("id")
                    logger.info("获取到最新订单: %s", oid)
                    return oid

        logger.debug("购买结果: %s", json.dumps(buy_result, ensure_ascii=False, indent=2))
        logger.warning("无法获取订单号，跳过请求卖家发送报价")
        return None

    # ── 统一购买接口 ─────────────────────────────────────────────

    def get_sell_orders(self, goods_id: str, *, charm_id: str = "", session: Optional[requests.Session] = None) -> List[Dict]:
        """获取卖单列表

        Args:
            session: 使用指定的 session（购买流程中传 new_session），
                     默认使用 self.session
        """
        url = f"{self.BASE_URL}/api/market/goods/sell_order"
        params = {
            "game": self.game,
            "goods_id": goods_id,
            "page_num": 1,
            "sort_by": "default",
            "mode": "",
            "allow_tradable_cooldown": 1,
        }
        if charm_id:
            params["charm"] = charm_id

        sess = session or self.session
        try:
            resp = sess.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "OK":
                    orders = data.get("data", {}).get("items", [])
                    logger.info("获取到 %d 个卖单 (goods_id=%s)", len(orders), goods_id)
                    return orders
                logger.warning("获取卖单失败: %s", data.get("msg"))
            else:
                logger.warning("获取卖单 HTTP %d", resp.status_code)
        except Exception as e:
            logger.error("获取卖单异常: %s", e)
        return []

    def buy_single_order(
        self,
        new_session: requests.Session,
        headers: dict,
        goods_id: str,
        sell_order_id: str,
        price: float,
        csrf_token: str,
        goods_page_url: str,
    ) -> Dict:
        """购买单个卖单。返回 {"success", "message", "bill_order_id"}"""
        if self.dry_run:
            msg = f"[DRY RUN] 购买 order={sell_order_id}, 价格={price} 元, goods_id={goods_id}"
            logger.info(msg)
            return {"success": True, "message": msg, "bill_order_id": None}

        buy_url = f"{self.BASE_URL}/api/market/goods/buy"
        buy_data = {
            "game": self.game,
            "goods_id": goods_id,
            "sell_order_id": sell_order_id,
            "price": price,
            "allow_tradable_cool_down": 0,
            "cdkey_id": "",
            "hide_non_epay": True,
            "pay_method": 1,
            "seller_order_id": sell_order_id,
            "steamid": None,
            "token": "",
        }

        buy_resp = new_session.post(buy_url, json=buy_data, headers=headers, timeout=15)
        logger.debug("购买响应 HTTP %d", buy_resp.status_code)

        if buy_resp.status_code == 200:
            buy_result = buy_resp.json()
            if buy_result.get("code") == "OK":
                logger.info("购买成功! order=%s", sell_order_id)
                bill_id = self._find_bill_order_id(buy_result, new_session, headers)
                if bill_id:
                    self._ask_seller_to_send_offer(new_session, headers, bill_id)
                else:
                    logger.warning("未找到订单号，请手动请求卖家发送报价")
                return {
                    "success": True,
                    "message": f"购买成功，价格={price} 元，订单号={bill_id}",
                    "bill_order_id": bill_id,
                    "price": price,
                }
            else:
                msg = buy_result.get("error", buy_result.get("msg", "购买失败"))
                logger.warning("购买失败: %s", msg)
                return {"success": False, "message": f"购买失败: {msg}", "bill_order_id": None, "price": price}
        else:
            msg = f"HTTP {buy_resp.status_code}"
            logger.warning("购买请求失败: %s", msg)
            return {"success": False, "message": f"购买请求失败: {msg}", "bill_order_id": None, "price": price}

    def buy_item(
        self,
        goods_id: str,
        *,
        max_price: float,
        max_orders: int = 5,
        charm_id: str = "",
        tried_items: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """完整的购买流程：初始化会话 → 获取卖单 → 筛选 → 逐个购买"""
        from buff.utils import make_tried_item

        if tried_items is None:
            tried_items = []

        results = []
        tried_order_ids = {str(t.get("order_id")) for t in tried_items}

        logger.info("购买饰品 goods_id=%s, 最高价=%.2f 元, charm_id=%s", goods_id, max_price, charm_id or "无")

        new_session, csrf_token, goods_page_url = self._init_buy_session(goods_id)
        if csrf_token:
            logger.debug("CSRF token: %s...", csrf_token[:20])

        # 获取卖单（使用 new_session，保持与原代码一致）
        sell_orders = self.get_sell_orders(goods_id, charm_id=charm_id, session=new_session)
        if not sell_orders:
            logger.warning("未找到卖单")
            return [{"success": False, "message": "未找到卖单"}]

        # 筛选
        eligible = []
        for order in sell_orders:
            order_price = float(order.get("price", "0"))
            order_id = str(order.get("id"))
            if order_price > max_price:
                logger.debug("跳过高价订单: %s (%.2f > %.2f)", order_id, order_price, max_price)
                break
            if order_id in tried_order_ids:
                logger.debug("跳过已尝试订单: %s", order_id)
                continue
            eligible.append(order)
            logger.info("符合条件: ID=%s, 价格=%.2f 元", order_id, order_price)

        if not eligible:
            logger.info("无符合条件的订单")
            return [{"success": False, "message": "无符合条件的订单"}]

        buy_count = min(max_orders, len(eligible))
        logger.info("共 %d 个符合条件，购买前 %d 个", len(eligible), buy_count)

        # 构建 headers
        headers = self._build_buy_headers(csrf_token, goods_page_url)
        if csrf_token:
            new_session.cookies.set("csrf_token", csrf_token, domain="buff.163.com", path="/")
            new_session.cookies.set("XSRF-TOKEN", csrf_token, domain="buff.163.com", path="/")

        # 获取商品名称（从卖单或缓存中）
        item_name = ""
        if sell_orders:
            item_name = sell_orders[0].get("goods_info", {}).get("goods_name", "")

        for i, order in enumerate(eligible[:buy_count]):
            sell_order_id = str(order.get("id"))
            order_price = float(order.get("price", "0"))
            seller_name = order.get("seller", {}).get("nickname", "")

            logger.info("购买 %d/%d: ID=%s, 价格=%.2f 元, 卖家=%s",
                        i + 1, buy_count, sell_order_id, order_price, seller_name)

            tried_items.append(make_tried_item(
                goods_id=goods_id,
                order_id=sell_order_id,
                price=order_price,
                seller_id=seller_name,
                status="attempted",
            ))

            # 刷新 CSRF（非 dry_run 时）
            if not self.dry_run:
                csrf_token = self._refresh_csrf_token(new_session, goods_page_url, csrf_token)
                if csrf_token:
                    headers["X-CSRFToken"] = csrf_token
                    headers["X-CSRF-Token"] = csrf_token
                    headers["Csrf-Token"] = csrf_token

            result = self.buy_single_order(
                new_session, headers, goods_id, sell_order_id, order_price, csrf_token, goods_page_url,
            )
            results.append(result)

            # 更新 tried_items 状态
            if result["success"]:
                tried_items[-1]["status"] = "success"
                tried_items[-1]["bill_order_id"] = result.get("bill_order_id")
            else:
                tried_items[-1]["status"] = "failed"
                tried_items[-1]["error"] = result.get("message")

            if not self.dry_run:
                self.session.cookies.update(new_session.cookies)

            if i < buy_count - 1:
                wait = random.uniform(4, 6)
                logger.debug("等待 %.1f 秒...", wait)
                time.sleep(wait)

        # 记录到 SQLite
        self._record_to_db(goods_id, item_name, sell_orders, results)

        # 汇总
        success = sum(1 for r in results if r["success"])
        logger.info("购买完成: 成功 %d/%d", success, len(results))
        for r in results:
            tag = "OK" if r["success"] else "FAIL"
            logger.info("  [%s] %s", tag, r["message"])

        return results

    def _record_to_db(self, goods_id, name, sell_orders, results):
        """记录价格快照和购买历史到 SQLite（懒加载连接）"""
        try:
            if self._db_conn is None:
                from buff.db import init_db
                self._db_conn = init_db()
            from buff.db import record_price, record_purchase
            if sell_orders:
                lowest = min(float(o.get("price", "0")) for o in sell_orders)
                record_price(self._db_conn, goods_id, name, lowest, len(sell_orders))
            for r in results:
                record_purchase(
                    self._db_conn, goods_id, name,
                    order_id=str(r.get("bill_order_id") or ""),
                    price=r.get("price", 0.0),
                    status="success" if r["success"] else "failed",
                    error=r.get("message") if not r["success"] else None,
                    bill_order_id=r.get("bill_order_id"),
                )
        except Exception as e:
            logger.debug("记录到数据库失败: %s", e)

    # ── 工具方法 ─────────────────────────────────────────────────

    @staticmethod
    def print_purchase_status(purchases: List[Dict]):
        logger.info("=== 购买情况 ===")
        total_cost = 0.0
        success_count = 0

        for i, p in enumerate(purchases, 1):
            logger.info("%d. %s", i, p["message"])
            if p["success"]:
                success_count += 1
                m = re.search(r"(\d+\.\d+)\s*元", p["message"])
                if m:
                    total_cost += float(m.group(1))

        logger.info("总计: %d 次, 成功 %d, 失败 %d, 花费 %.2f 元",
                     len(purchases), success_count, len(purchases) - success_count, total_cost)
