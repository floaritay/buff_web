"""BuffClient 基类 - 提取三个脚本中相同的 session 管理、认证、CSRF 处理逻辑"""

import re
import time
import json
import requests


class BuffClient:
    """BUFF 客户端基类，提供 session 管理、cookie 设置、登录测试、CSRF 处理等公共功能"""

    BASE_URL = "https://buff.163.com"

    def __init__(self, game: str = "csgo"):
        self.game = game
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

    def set_cookie(self, cookie_str: str) -> bool:
        """手动设置cookie"""
        if not cookie_str:
            print("错误: Cookie不能为空")
            return False

        cookies = {}
        cookie_items = cookie_str.split(';')

        for item in cookie_items:
            item = item.strip()
            if '=' in item:
                try:
                    key, value = item.split('=', 1)
                    cookies[key] = value
                except Exception:
                    pass

        if not cookies:
            print("错误: 无法解析Cookie")
            return False

        required_cookies = ['session', 'remember_me', '_ntes']
        has_required = any(key in cookies for key in required_cookies)

        if not has_required:
            print("警告: Cookie可能缺少关键项（'session', 'remember_me', '_ntes'），可能无法正常登录")

        self.session.cookies.update(cookies)
        print(f"Cookie设置成功，解析到 {len(cookies)} 个Cookie项")
        return True

    def test_login(self) -> bool:
        """测试登录状态"""
        try:
            url = f"{self.BASE_URL}/api/market/goods?game={self.game}&page_num=1&page_size=10"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 'OK':
                    print("登录状态正常")
                    return True

            print("登录状态异常")
            return False
        except Exception as e:
            print(f"测试登录失败: {e}")
            return False

    def _extract_csrf_token(self, html_content: str, session: requests.Session) -> str:
        """从 HTML 内容和 cookie 中提取 CSRF token（5 种模式的超集）"""
        csrf_token = ""

        # 模式1: meta 标签
        meta_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html_content)
        if meta_match:
            csrf_token = meta_match.group(1)
            print(f"从meta标签获取到CSRF token: {csrf_token[:20]}...")
            return csrf_token

        # 模式2: csrf_token = '...'
        script_match = re.search(r'csrf_token\s*=\s*["\']([^"\']+)["\']', html_content)
        if script_match:
            csrf_token = script_match.group(1)
            print(f"从script标签获取到CSRF token: {csrf_token[:20]}...")
            return csrf_token

        # 模式3: window.csrf_token = '...'
        window_match = re.search(r'window\.csrf_token\s*=\s*["\']([^"\']+)["\']', html_content)
        if window_match:
            csrf_token = window_match.group(1)
            print(f"从window.csrf_token获取到CSRF token: {csrf_token[:20]}...")
            return csrf_token

        # 模式4: cookie
        for cookie in session.cookies:
            if cookie.name == 'csrf_token':
                csrf_token = cookie.value
                print(f"从cookie获取到CSRF token: {csrf_token[:20]}...")
                return csrf_token

        # 模式5: 表单隐藏字段
        form_match = re.search(r'<input[^>]+name="csrfmiddlewaretoken"[^>]+value="([^"]+)"', html_content)
        if form_match:
            csrf_token = form_match.group(1)
            print(f"从表单隐藏字段获取到CSRF token: {csrf_token[:20]}...")
            return csrf_token

        return ""

    def _get_browser_headers(self) -> dict:
        """返回完整的浏览器级请求头（用于购买流程）"""
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
        """购买前重新初始化会话，模拟浏览器全新访问

        返回:
            tuple: (new_session, csrf_token, goods_page_url)
        """
        current_cookies = self.session.cookies.get_dict()

        new_session = requests.Session()
        browser_headers = self._get_browser_headers()
        new_session.headers.update(browser_headers)

        for key, value in current_cookies.items():
            new_session.cookies.set(key, value, domain='buff.163.com', path='/')

        # 访问主页
        print("访问BUFF主页...")
        new_session.get(f"{self.BASE_URL}", timeout=15)
        time.sleep(1.5)

        # 访问市场页面
        market_url = f"{self.BASE_URL}/market/{self.game}"
        print(f"访问市场页面: {market_url}")
        new_session.get(market_url, timeout=15)
        time.sleep(1.5)

        # 访问商品页面
        goods_page_url = f"{self.BASE_URL}/goods/{goods_id}"
        print(f"访问商品页面: {goods_page_url}")
        goods_response = new_session.get(goods_page_url, timeout=15)
        time.sleep(1.5)

        # 提取 CSRF token
        csrf_token = ""
        if goods_response.status_code == 200:
            csrf_token = self._extract_csrf_token(goods_response.text, new_session)

        if not csrf_token:
            print("警告: 未能获取CSRF token")

        return new_session, csrf_token, goods_page_url

    def _refresh_csrf_token(self, new_session: requests.Session, goods_page_url: str, current_csrf: str) -> str:
        """重新访问商品页面获取新鲜的 CSRF token"""
        print("再次访问商品页面以确保token新鲜...")
        goods_response = new_session.get(goods_page_url, timeout=15)
        time.sleep(1)

        if goods_response.status_code == 200:
            fresh_token = self._extract_csrf_token(goods_response.text, new_session)
            if fresh_token:
                return fresh_token
        return current_csrf

    def _build_buy_headers(self, csrf_token: str, goods_page_url: str) -> dict:
        """构建购买请求的 headers"""
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

    def _ask_seller_to_send_offer(self, new_session: requests.Session, headers: dict, bill_order_id) -> bool:
        """请求卖家发送 Steam 交易报价"""
        ask_seller_url = f"{self.BASE_URL}/api/market/bill_order/ask_seller_to_send_offer"
        ask_seller_data = {
            "bill_orders": [bill_order_id],
            "game": self.game,
            "steamid": None
        }

        ask_seller_response = new_session.post(ask_seller_url, json=ask_seller_data, headers=headers, timeout=15)

        print(f"请求卖家发送报价状态码: {ask_seller_response.status_code}")
        print(f"请求卖家发送报价响应: {ask_seller_response.text[:300]}...")

        if ask_seller_response.status_code == 200:
            ask_seller_result = ask_seller_response.json()
            if ask_seller_result.get('code') == 'OK':
                print("请求卖家发送报价成功")
                return True
            else:
                print(f"请求卖家发送报价失败: {ask_seller_result.get('msg', '未知错误')}")
        else:
            print(f"请求卖家发送报价请求失败，状态码: {ask_seller_response.status_code}")
        return False

    def _find_bill_order_id(self, buy_result: dict, new_session: requests.Session, headers: dict):
        """从购买结果或最新订单中获取 bill_order_id"""
        # 1. 从购买结果中获取
        for field in ['bill_order_id', 'order_id', 'id']:
            bill_order_id = buy_result.get('data', {}).get(field)
            if bill_order_id:
                print(f"从{field}字段获取到订单号: {bill_order_id}")
                return bill_order_id

        # 2. 获取最新订单
        print("尝试获取最新的订单...")
        orders_url = f"{self.BASE_URL}/api/market/bill_order"
        orders_params = {
            "game": self.game,
            "page_num": 1,
            "status": "pending"
        }
        orders_response = new_session.get(orders_url, params=orders_params, headers=headers, timeout=15)

        if orders_response.status_code == 200:
            orders_data = orders_response.json()
            if orders_data.get('code') == 'OK':
                orders = orders_data.get('data', {}).get('items', [])
                if orders:
                    latest_order = orders[0]
                    bill_order_id = latest_order.get('id')
                    print(f"获取到最新订单: {bill_order_id}")
                    return bill_order_id

        # 3. 打印购买结果便于分析
        print("购买结果数据:")
        print(json.dumps(buy_result, ensure_ascii=False, indent=2))
        print("无法获取订单号，跳过请求卖家发送报价")
        return None
