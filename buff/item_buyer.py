"""BuffItemBuyer - 指定饰品自动购买类"""

import json
import random
import re
import sys
import time
from typing import Dict, List, Optional

from buff.client import BuffClient


TRIED_ITEMS_FILE = "item_tried_items.json"


def parse_goods_id(raw: str) -> str:
    """从 URL 或纯数字中提取 goods_id

    支持的格式：
      - https://buff.163.com/goods/12345
      - https://buff.163.com/goods/12345#tab=selling
      - buff.163.com/goods/12345
      - /goods/12345
      - 12345
    """
    raw = raw.strip()
    m = re.search(r"buff\.163\.com/goods/(\d+)", raw)
    if m:
        return m.group(1)
    m = re.search(r"/goods/(\d+)", raw)
    if m:
        return m.group(1)
    if raw.isdigit():
        return raw
    print(f"错误: 无法从 '{raw}' 中解析 goods_id")
    print("支持的格式:")
    print("  - https://buff.163.com/goods/12345")
    print("  - 12345")
    sys.exit(1)


class BuffItemBuyer(BuffClient):
    """BUFF 指定饰品购买器"""

    def search_items(self, keyword: str, page_size: int = 10) -> List[Dict]:
        """按名称搜索饰品，返回匹配结果列表

        返回: [{"id": 12345, "name": "...", "sell_min_price": "1.23", "sell_num": 10}, ...]
        """
        url = f"{self.BASE_URL}/api/market/goods"
        params = {
            "game": self.game,
            "page_num": 1,
            "page_size": page_size,
            "search": keyword,
            "sort_by": "price.asc",
        }
        try:
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "OK":
                    items = data.get("data", {}).get("items", [])
                    return items
                print(f"搜索失败: {data.get('msg')}")
            else:
                print(f"搜索请求失败，状态码: {resp.status_code}")
        except Exception as e:
            print(f"搜索异常: {e}")
        return []

    def _get_sell_orders(self, new_session, goods_id, headers):
        url = f"{self.BASE_URL}/api/market/goods/sell_order"
        params = {"game": self.game, "goods_id": goods_id}
        try:
            resp = new_session.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "OK":
                    orders = data.get("data", {}).get("items", [])
                    print(f"获取到 {len(orders)} 个卖单")
                    return orders
                print(f"获取卖单失败: {data.get('msg')}")
            else:
                print(f"获取卖单请求失败，状态码: {resp.status_code}")
        except Exception as e:
            print(f"获取卖单异常: {e}")
        return []

    def run(
        self,
        goods_id: str,
        max_price: float = 1.0,
        max_items: int = 5,
        tried_items: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """单次执行：检查指定饰品并购买低于价格阈值的卖单"""
        if tried_items is None:
            tried_items = []

        print("=" * 50)
        print(f"饰品 goods_id : {goods_id}")
        print(f"价格阈值      : {max_price} 元")
        print(f"最大购买数量  : {max_items}")
        print(f"已尝试订单数  : {len(tried_items)}")
        print("=" * 50)

        if not self.test_login():
            print("请先设置有效的 cookie")
            return []

        # 初始化购买会话
        new_session, csrf_token, goods_page_url = self._init_buy_session(goods_id)
        if csrf_token:
            print(f"使用 CSRF token: {csrf_token[:20]}...")

        # 获取卖单
        order_headers = {
            **self.headers,
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/plain, */*",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Referer": goods_page_url,
        }
        if csrf_token:
            order_headers["X-CSRFToken"] = csrf_token
            order_headers["X-CSRF-Token"] = csrf_token

        sell_orders = self._get_sell_orders(new_session, goods_id, order_headers)
        if not sell_orders:
            print("未找到卖单")
            return []

        # 筛选符合条件的订单
        eligible = []
        tried_order_ids = {str(t.get("order_id")) for t in tried_items}
        for order in sell_orders:
            price = float(order.get("price", "0"))
            oid = str(order.get("id"))
            if price > max_price:
                print(f"跳过价格过高的订单: ID={oid}, 价格={price} 元")
                break
            if oid in tried_order_ids:
                print(f"跳过已尝试的订单: ID={oid}, 价格={price} 元")
                continue
            eligible.append(order)
            print(f"符合条件: ID={oid}, 价格={price} 元")

        if not eligible:
            print("没有符合条件的订单")
            return []

        buy_count = min(max_items, len(eligible))
        print(f"共 {len(eligible)} 个符合条件，将尝试购买 {buy_count} 个")

        # 构建购买 headers
        buy_headers = self._build_buy_headers(csrf_token, goods_page_url)
        if csrf_token:
            new_session.cookies.set("csrf_token", csrf_token, domain="buff.163.com", path="/")
            new_session.cookies.set("XSRF-TOKEN", csrf_token, domain="buff.163.com", path="/")

        results = []
        for i, order in enumerate(eligible[:buy_count]):
            sell_order_id = str(order.get("id"))
            order_price = float(order.get("price", "0"))
            seller_name = order.get("seller", {}).get("nickname", "")

            print(f"\n{'─'*40}")
            print(f"购买第 {i+1}/{buy_count} 个: ID={sell_order_id}, 价格={order_price} 元, 卖家={seller_name}")

            tried_items.append({
                "goods_id": goods_id,
                "price": order_price,
                "order_id": sell_order_id,
                "seller": seller_name,
                "attempt_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "attempted",
            })

            # 刷新 CSRF
            csrf_token = self._refresh_csrf_token(new_session, goods_page_url, csrf_token)
            if csrf_token:
                buy_headers["X-CSRFToken"] = csrf_token
                buy_headers["X-XSRF-TOKEN"] = csrf_token
                buy_headers["CSRF-Token"] = csrf_token

            buy_url = f"{self.BASE_URL}/api/market/goods/buy"
            buy_data = {
                "game": self.game,
                "goods_id": goods_id,
                "sell_order_id": sell_order_id,
                "price": order_price,
                "allow_tradable_cool_down": 0,
                "cdkey_id": "",
                "hide_non_epay": True,
                "pay_method": 1,
                "seller_order_id": sell_order_id,
                "steamid": None,
                "token": "",
            }

            try:
                buy_resp = new_session.post(buy_url, json=buy_data, headers=buy_headers, timeout=15)
                print(f"购买响应状态码: {buy_resp.status_code}")

                if buy_resp.status_code == 200:
                    buy_result = buy_resp.json()
                    if buy_result.get("code") == "OK":
                        print("购买成功!")
                        bill_id = self._find_bill_order_id(buy_result, new_session, buy_headers)
                        if bill_id:
                            self._ask_seller_to_send_offer(new_session, buy_headers, bill_id)
                        else:
                            print("未找到订单号，请手动在 BUFF 客户端请求卖家发送报价")

                        tried_items[-1]["status"] = "success"
                        tried_items[-1]["bill_order_id"] = bill_id
                        results.append({"success": True, "message": f"购买成功，价格={order_price} 元，订单号={bill_id}"})
                    else:
                        msg = buy_result.get("error", buy_result.get("msg", "未知错误"))
                        print(f"购买失败: {msg}")
                        tried_items[-1]["status"] = "failed"
                        tried_items[-1]["error"] = msg
                        results.append({"success": False, "message": f"购买失败: {msg}"})
                else:
                    print(f"请求失败，状态码: {buy_resp.status_code}")
                    tried_items[-1]["status"] = "failed"
                    tried_items[-1]["error"] = f"HTTP {buy_resp.status_code}"
                    results.append({"success": False, "message": f"请求失败，状态码: {buy_resp.status_code}"})
            except Exception as e:
                print(f"购买异常: {e}")
                tried_items[-1]["status"] = "failed"
                tried_items[-1]["error"] = str(e)
                results.append({"success": False, "message": str(e)})

            self.session.cookies.update(new_session.cookies)

            if i < buy_count - 1:
                wait = random.uniform(4, 6)
                print(f"等待 {wait:.1f} 秒...")
                time.sleep(wait)

        # 汇总
        print(f"\n{'='*50}")
        success = sum(1 for r in results if r["success"])
        print(f"购买完成: 成功 {success}/{len(results)}")
        for r in results:
            tag = "OK" if r["success"] else "FAIL"
            print(f"  [{tag}] {r['message']}")
        print("=" * 50)

        return results

    def run_polling(
        self,
        goods_id: str,
        max_price: float = 1.0,
        max_items: int = 5,
        interval: int = 30,
        max_rounds: int = 0,
        tried_items: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """轮询监控模式：持续检查并购买"""
        if tried_items is None:
            tried_items = []

        print(f"进入轮询模式，间隔 {interval} 秒")
        if max_rounds > 0:
            print(f"最大轮询次数: {max_rounds}")
        else:
            print("无限轮询，按 Ctrl+C 停止")
        print()

        all_results = []
        round_num = 0
        try:
            while True:
                round_num += 1
                if max_rounds > 0 and round_num > max_rounds:
                    print(f"已达到最大轮询次数 {max_rounds}，停止")
                    break

                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n{'#'*50}")
                print(f"# 第 {round_num} 轮 | {ts}")
                print(f"{'#'*50}")

                results = self.run(
                    goods_id=goods_id,
                    max_price=max_price,
                    max_items=max_items,
                    tried_items=tried_items,
                )
                all_results.extend(results)

                if max_rounds > 0 and round_num >= max_rounds:
                    break

                print(f"\n等待 {interval} 秒后进行下一轮...")
                time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n\n用户中断，共完成 {round_num} 轮")

        return all_results
