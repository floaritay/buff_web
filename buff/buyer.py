"""BuffBuyer - 涂鸦饰品自动购买类"""

import re
import time
import json
import random
from typing import List, Dict

from buff.client import BuffClient


class BuffBuyer(BuffClient):
    """BUFF涂鸦饰品购买类"""

    def get_graffiti(self, page_num: int = 1, page_size: int = 20) -> List[Dict]:
        """获取涂鸦类饰品"""
        try:
            url = f"{self.BASE_URL}/api/market/goods"

            params_list = [
                {
                    "game": self.game,
                    "page_num": page_num,
                    "page_size": page_size,
                    "category": "csgo_type_spray",
                    "sort_by": "price.asc"
                },
                {
                    "game": self.game,
                    "page_num": page_num,
                    "page_size": page_size,
                    "category_group": "spray",
                    "sort_by": "price.asc"
                },
                {
                    "game": self.game,
                    "page_num": page_num,
                    "page_size": page_size,
                    "category": "spray",
                    "sort_by": "price.asc"
                }
            ]

            for params in params_list:
                headers = {
                    **self.headers,
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Connection": "keep-alive",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache"
                }

                time.sleep(random.uniform(0.5, 1.5))

                max_retries = 3
                for retry in range(max_retries):
                    try:
                        response = self.session.get(url, params=params, headers=headers, timeout=20)
                        break
                    except requests.exceptions.Timeout:
                        print(f"请求超时，正在重试 ({retry+1}/{max_retries})...")
                        if retry == max_retries - 1:
                            raise

                print(f"请求URL: {response.url}")
                print(f"响应状态: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    print(f"响应代码: {data.get('code')}")

                    if data.get('code') == 'OK':
                        items = data.get('data', {}).get('items', [])
                        if items:
                            first_item_name = items[0].get('name', '')
                            print(f"第一个饰品名称: {first_item_name}")

                            is_graffiti = any(keyword in first_item_name for keyword in ['涂鸦', 'spray', 'Graffiti', '喷漆'])

                            if is_graffiti:
                                print(f"获取到 {len(items)} 个涂鸦饰品")
                                first = items[0]
                                print("第一个饰品简要信息:", json.dumps({
                                    "id": first.get("id"),
                                    "name": first.get("name"),
                                    "price": first.get("sell_min_price")
                                }, ensure_ascii=False))
                                return items
                            else:
                                print(f"获取到的不是涂鸦饰品，尝试下一种参数组合")
                    else:
                        print(f"API响应错误: {data.get('code')}")
                else:
                    print(f"请求失败，状态码: {response.status_code}")

            print("获取涂鸦饰品失败，所有参数组合都尝试过")
            return []
        except Exception as e:
            print(f"获取涂鸦饰品异常: {e}")
            import traceback
            traceback.print_exc()
            return []

    def filter_cheap_items(self, items: List[Dict], max_price: float = 0.05) -> List[Dict]:
        """筛选价格小于等于max_price的涂鸦饰品"""
        cheap_items = []
        for item in items:
            item_name = item.get('name', '')
            if '涂鸦' not in item_name and 'spray' not in item_name.lower() and 'graffiti' not in item_name.lower():
                continue

            price_str = item.get('sell_min_price', item.get('price', '0'))
            try:
                price = float(price_str)
                if price > 0 and price <= max_price:
                    item_info = {
                        'id': item.get('id'),
                        'name': item_name,
                        'price': price,
                        'sell_num': item.get('sell_num', 0),
                        'goods_id': item.get('id'),
                        'steam_market_url': item.get('steam_market_url', '')
                    }
                    cheap_items.append(item_info)
                    print(f"找到符合条件的涂鸦: {item_name} - {price}元")
            except Exception as e:
                print(f"处理价格失败: {e}")
                print(f"价格字段: {item.get('sell_min_price')}, {item.get('price')}")
        print(f"筛选出 {len(cheap_items)} 个价格小于等于 {max_price} 元的涂鸦饰品")
        return cheap_items

    def get_sell_orders(self, goods_id: str) -> List[Dict]:
        """获取饰品的所有卖家订单"""
        try:
            print(f"获取饰品 {goods_id} 的卖家订单列表...")
            sell_order_url = f"{self.BASE_URL}/api/market/goods/sell_order"
            sell_order_params = {
                "game": self.game,
                "goods_id": goods_id
            }

            sell_order_response = self.session.get(sell_order_url, params=sell_order_params, timeout=15)

            if sell_order_response.status_code == 200:
                sell_order_data = sell_order_response.json()
                if sell_order_data.get('code') == 'OK':
                    sell_orders = sell_order_data.get('data', {}).get('items', [])
                    print(f"获取到 {len(sell_orders)} 个卖家订单")

                    if sell_orders:
                        print("第一个卖家订单简略信息:", json.dumps({
                            "id": sell_orders[0].get("id"),
                            "price": sell_orders[0].get("price"),
                            "seller_name": sell_orders[0].get("seller", {}).get("nickname", "")
                        }, ensure_ascii=False))
                    return sell_orders
                else:
                    print(f"获取卖家订单失败: {sell_order_data.get('msg', '未知错误')}")
                    return []
            else:
                print(f"获取卖家订单请求失败，状态码: {sell_order_response.status_code}")
                return []
        except Exception as e:
            print(f"获取卖家订单异常: {e}")
            import traceback
            traceback.print_exc()
            return []

    def buy_item(self, goods_id: str, price: float, max_price: float = 0.05, max_orders: int = 5, tried_items=None) -> List[Dict]:
        """购买涂鸦饰品（支持购买多个报价）"""
        results = []
        if tried_items is None:
            tried_items = []

        try:
            print(f"尝试购买饰品 ID: {goods_id}, 目标价格: {price}元")

            new_session, csrf_token, goods_page_url = self._init_buy_session(goods_id)

            if csrf_token:
                print(f"使用CSRF token: {csrf_token[:20]}...")

            # 获取卖家订单列表
            print("获取卖家订单列表...")
            sell_order_url = f"{self.BASE_URL}/api/market/goods/sell_order"
            sell_order_params = {
                "game": self.game,
                "goods_id": goods_id
            }

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

            sell_order_response = new_session.get(sell_order_url, params=sell_order_params, headers=order_headers, timeout=15)
            sell_orders = []

            if sell_order_response.status_code == 200:
                sell_order_data = sell_order_response.json()
                if sell_order_data.get('code') == 'OK':
                    sell_orders = sell_order_data.get('data', {}).get('items', [])
                    print(f"获取到 {len(sell_orders)} 个卖家订单")
                else:
                    print(f"获取卖家订单失败: {sell_order_data.get('msg', '未知错误')}")
            else:
                print(f"获取卖家订单请求失败，状态码: {sell_order_response.status_code}")

            if not sell_orders:
                print("未找到卖家订单")
                results.append({'success': False, 'message': "未找到卖家订单"})
                return results

            # 筛选符合条件的订单
            eligible_orders = []
            for order in sell_orders:
                order_price = float(order.get('price', '0'))
                order_id = str(order.get('id'))

                if order_price <= max_price:
                    is_order_tried = any(
                        str(tried.get('order_id')) == order_id
                        for tried in tried_items
                    )
                    if not is_order_tried:
                        eligible_orders.append(order)
                        print(f"找到符合条件的订单: ID={order_id}, 价格={order_price}元")
                    else:
                        print(f"跳过已尝试的订单: ID={order_id}, 价格={order_price}元")
                else:
                    print(f"跳过价格过高的订单: ID={order_id}, 价格={order_price}元（最大允许价格: {max_price}元）")
                    print("订单按价格升序排列，后续订单价格更高，停止检查")
                    break

            if not eligible_orders:
                print("未找到符合价格条件的卖家订单")
                results.append({'success': False, 'message': "未找到符合价格条件的卖家订单"})
                return results

            print(f"共找到 {len(eligible_orders)} 个符合条件的订单，将尝试购买前 {min(max_orders, len(eligible_orders))} 个")

            headers = self._build_buy_headers(csrf_token, goods_page_url)
            # buyer 额外设置 cookie 中的 csrf
            if csrf_token:
                new_session.cookies.set('csrf_token', csrf_token, domain='buff.163.com', path='/')
                new_session.cookies.set('XSRF-TOKEN', csrf_token, domain='buff.163.com', path='/')

            # 尝试购买每个符合条件的订单
            for i, order in enumerate(eligible_orders[:max_orders]):
                sell_order_id = str(order.get('id'))
                order_price = float(order.get('price', '0'))

                print(f"\n尝试购买第 {i+1} 个订单: ID={sell_order_id}, 价格={order_price}元")
                print(f"订单ID类型: {type(sell_order_id)}")

                order_attempt_info = {
                    'id': str(goods_id),
                    'name': '',
                    'price': order_price,
                    'steam_market_url': '',
                    'attempt_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'attempted',
                    'order_id': sell_order_id,
                    'attempt_number': i + 1
                }
                tried_items.append(order_attempt_info)

                # 刷新 CSRF token
                csrf_token = self._refresh_csrf_token(new_session, goods_page_url, csrf_token)
                if csrf_token:
                    headers["X-CSRFToken"] = csrf_token
                    headers["X-XSRF-TOKEN"] = csrf_token
                    headers["CSRF-Token"] = csrf_token

                # 发起购买请求
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

                print("\n购买请求数据:")
                print(json.dumps(buy_data, ensure_ascii=False, indent=2))

                buy_response = new_session.post(buy_url, json=buy_data, headers=headers, timeout=15)

                print(f"购买请求状态码: {buy_response.status_code}")
                print(f"购买请求响应: {buy_response.text[:200]}...")

                bill_order_id = None

                if buy_response.status_code == 200:
                    buy_result = buy_response.json()
                    if buy_result.get('code') == 'OK':
                        print(f"购买成功")

                        print("请求卖家发送报价...")
                        bill_order_id = self._find_bill_order_id(buy_result, new_session, headers)

                        if bill_order_id:
                            self._ask_seller_to_send_offer(new_session, headers, bill_order_id)
                        else:
                            print("未找到订单号，无法请求卖家发送报价")
                            print("您可以手动在BUFF手机端上请求卖家发送报价")

                        order_id_to_display = bill_order_id if bill_order_id else buy_result.get('data', {}).get('order_id', 'N/A')
                        results.append({
                            'success': True,
                            'message': f"购买成功，饰品ID: {goods_id}，价格: {order_price}元，订单号: {order_id_to_display}"
                        })
                    else:
                        error_msg = buy_result.get('error', buy_result.get('msg', '购买失败'))
                        print(f"购买失败: {error_msg}")
                        results.append({'success': False, 'message': f"购买失败: {error_msg}"})
                else:
                    print(f"购买请求失败，状态码: {buy_response.status_code}")
                    results.append({'success': False, 'message': f"购买请求失败，状态码: {buy_response.status_code}"})

                # 更新主会话的 cookie
                self.session.cookies.update(new_session.cookies)

                time.sleep(5)

        except Exception as e:
            print(f"购买失败: {e}")
            import traceback
            traceback.print_exc()
            results.append({'success': False, 'message': str(e)})

        return results

    def print_purchase_status(self, purchases: List[Dict]):
        """打印购买情况"""
        print("\n=== 购买情况 ===")
        total_cost = 0
        success_count = 0

        for i, purchase in enumerate(purchases, 1):
            print(f"{i}. {purchase['message']}")
            if purchase['success']:
                success_count += 1
                price_match = re.search(r'价格: (\d+\.\d+)元', purchase['message'])
                if price_match:
                    total_cost += float(price_match.group(1))

        print(f"\n总计: 尝试购买 {len(purchases)} 个饰品")
        print(f"成功: {success_count} 个")
        print(f"失败: {len(purchases) - success_count} 个")
        print(f"总花费: {total_cost:.2f} 元")

    def run(self, max_price: float = 0.05, max_items: int = 10, tried_items=None):
        """运行主流程"""
        if tried_items is None:
            tried_items = []

        print("=== BUFF饰品购买脚本 ===")
        print(f"游戏: {self.game}")
        print(f"目标: 购买价格 <= {max_price}元的涂鸦饰品")
        print(f"最大购买数量: {max_items}")
        print(f"已尝试商品数量: {len(tried_items)}")

        if not self.test_login():
            print("请先设置有效的cookie")
            return

        all_items = []
        page = 1
        while len(all_items) < max_items * 2:
            items = self.get_graffiti(page_num=page, page_size=20)
            if not items:
                break
            all_items.extend(items)
            page += 1
            time.sleep(1)

        cheap_items = self.filter_cheap_items(all_items, max_price)
        if not cheap_items:
            print("没有找到符合条件的饰品")
            return

        filtered_items = cheap_items
        print(f"找到 {len(filtered_items)} 个符合条件的商品，准备尝试购买")

        if not filtered_items:
            print("没有找到符合条件的饰品")
            return

        purchases = []
        for item in filtered_items[:max_items]:
            print(f"\n准备购买: {item['name']} - {item['price']}元")

            results = self.buy_item(item['goods_id'], item['price'], max_price, tried_items=tried_items)

            for i, result in enumerate(results):
                item_info = {
                    'id': str(item.get('id', '')),
                    'name': item.get('name', ''),
                    'price': item.get('price', 0),
                    'steam_market_url': item.get('steam_market_url', ''),
                    'attempt_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'attempted'
                }

                if result.get('success'):
                    item_info['status'] = 'success'
                    order_id = result.get('message', '').split('订单号: ')[-1] if '订单号: ' in result.get('message', '') else ''
                    item_info['order_id'] = order_id
                    item_info['attempt_number'] = i + 1
                else:
                    item_info['status'] = 'failed'
                    item_info['error_message'] = result.get('message', '')
                    item_info['attempt_number'] = i + 1

                tried_items.append(item_info)
                print(f"已将商品添加到尝试记录: {item['name']} (尝试 #{i+1}, 状态: {item_info['status']})")

            purchases.extend(results)
            time.sleep(2)

        self.print_purchase_status(purchases)
        print("\n=== 脚本运行完成 ===")
