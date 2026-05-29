"""BuffCharmSearcher - 挂件搜枪自动购买类（合并 Austin 和 Budapest 两个变体）"""

import re
import time
import json
import random
from typing import List, Dict

from buff.client import BuffClient
from buff.config import CharmEvent


class BuffCharmSearcher(BuffClient):
    """BUFF挂件搜枪类

    通过 event_config 参数区分不同事件（Austin/Budapest），一个类替代原来的两个文件。
    """

    def __init__(self, game: str = "csgo", event_config: CharmEvent = None):
        super().__init__(game)
        if event_config is None:
            raise ValueError("event_config 不能为空，请传入 CharmEvent 配置")
        self.event_config = event_config

    def get_charms(self, page_num: int = 1, page_size: int = 20) -> List[Dict]:
        """获取挂件（纪念品）类饰品"""
        try:
            url = f"{self.BASE_URL}/api/market/goods"

            params = {
                "game": self.game,
                "page_num": page_num,
                "page_size": page_size,
                "category": self.event_config.category,
                "sort_by": "price.asc"
            }

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

                        is_charm = any(keyword in first_item_name for keyword in ['挂件', 'keychain', 'charm'])

                        if is_charm:
                            print(f"获取到 {len(items)} 个挂件饰品")
                            first = items[0]
                            print("第一个饰品简要信息:", json.dumps({
                                "id": first.get("id"),
                                "name": first.get("name"),
                                "price": first.get("sell_min_price")
                            }, ensure_ascii=False))
                            return items
                        else:
                            print(f"获取到的不是挂件饰品")
                    else:
                        print("未获取到饰品")
                else:
                    print(f"API响应错误: {data.get('code')}")
            else:
                print(f"请求失败，状态码: {response.status_code}")

            return []
        except Exception as e:
            print(f"获取挂件饰品异常: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_custom_charm_id(self, goods_id: str) -> str:
        """从页面中获取custom_charm ID"""
        try:
            url = f"{self.BASE_URL}/goods/{goods_id}"

            headers = {
                **self.headers,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }

            time.sleep(random.uniform(0.5, 1.5))

            max_retries = 3
            for retry in range(max_retries):
                try:
                    response = self.session.get(url, headers=headers, timeout=20)
                    break
                except requests.exceptions.Timeout:
                    print(f"请求超时，正在重试 ({retry+1}/{max_retries})...")
                    if retry == max_retries - 1:
                        raise

            print(f"请求URL: {response.url}")
            print(f"响应状态: {response.status_code}")

            if response.status_code == 200:
                html_content = response.text

                # 查找包含"挂件搜枪"的链接
                charm_link_match = re.search(r'挂件搜枪[^<]+href=["\']([^"\']+)"', html_content)
                if charm_link_match:
                    charm_link = charm_link_match.group(1)
                    print(f"找到挂件搜枪链接: {charm_link}")

                    custom_charm_match = re.search(r'custom_charm=(\d+)', charm_link)
                    if custom_charm_match:
                        custom_charm_id = custom_charm_match.group(1)
                        print(f"从链接中提取到custom_charm ID: {custom_charm_id}")
                        return custom_charm_id

                # 备选模式
                alternative_match = re.search(r'custom_charm=(\d+)', html_content)
                if alternative_match:
                    custom_charm_id = alternative_match.group(1)
                    print(f"从页面中提取到custom_charm ID (备选模式): {custom_charm_id}")
                    return custom_charm_id

                # JavaScript 对象模式
                js_charm_match = re.search(r'"charm"\s*:\s*\{[^}]*"id"\s*:\s*(\d+)', html_content)
                if js_charm_match:
                    custom_charm_id = js_charm_match.group(1)
                    print(f"从JavaScript对象中提取到custom_charm ID: {custom_charm_id}")
                    return custom_charm_id

                js_charm_match2 = re.search(r'charm_id\s*=\s*(\d+)', html_content)
                if js_charm_match2:
                    custom_charm_id = js_charm_match2.group(1)
                    print(f"从JavaScript变量中提取到custom_charm ID: {custom_charm_id}")
                    return custom_charm_id

                js_charm_match3 = re.search(r'charm\s*:\s*(\d+)', html_content)
                if js_charm_match3:
                    custom_charm_id = js_charm_match3.group(1)
                    print(f"从JavaScript对象中提取到custom_charm ID (简化模式): {custom_charm_id}")
                    return custom_charm_id

                print(f"页面HTML中包含'charm'的部分: {re.search(r'[^{]*charm[^{}]*', html_content).group(0) if re.search(r'[^{]*charm[^{}]*', html_content) else '未找到'}")

                print("未在页面中找到custom_charm ID")
            else:
                print(f"请求失败，状态码: {response.status_code}")

            return ""
        except Exception as e:
            print(f"从页面提取custom_charm ID异常: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def get_guns_with_charm(self, custom_charm_id: str, page_num: int = 1, page_size: int = 50) -> List[Dict]:
        """获取带有特定挂件的枪械饰品"""
        try:
            url = f"{self.BASE_URL}/api/market/goods"

            params = {
                "game": self.game,
                "page_num": page_num,
                "page_size": page_size,
                "charm": custom_charm_id,
                "sort_by": "price.asc",
                "tab": "selling"
            }

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

            time.sleep(random.uniform(1.5, 3.0))

            max_retries = 3
            for retry in range(max_retries):
                try:
                    response = self.session.get(url, params=params, headers=headers, timeout=20)

                    if response.status_code == 429:
                        print(f"请求过于频繁，正在等待并重试 ({retry+1}/{max_retries})...")
                        time.sleep(random.uniform(5.0, 10.0))
                        continue

                    break
                except requests.exceptions.Timeout:
                    print(f"请求超时，正在重试 ({retry+1}/{max_retries})...")
                    if retry == max_retries - 1:
                        raise

            print(f"API请求URL: {response.url}")
            print(f"响应状态: {response.status_code}")

            browser_url = f"https://buff.163.com/market/csgo#game=csgo&page_num={page_num}&custom_charm={custom_charm_id}&sort_by=price.asc&tab=selling"
            print(f"浏览器访问URL: {browser_url}")

            if response.status_code == 200:
                data = response.json()
                print(f"响应代码: {data.get('code')}")

                if data.get('code') == 'OK':
                    items = data.get('data', {}).get('items', [])
                    if items:
                        print(f"从API获取到 {len(items)} 个饰品")
                        first = items[0]
                        print("第一个饰品简要信息:", json.dumps({
                            "id": first.get("id"),
                            "name": first.get("name"),
                            "price": first.get("sell_min_price")
                        }, ensure_ascii=False))
                        return items
                    else:
                        print("未获取到饰品")
                else:
                    print(f"API响应错误: {data.get('code')}")
            else:
                print(f"请求失败，状态码: {response.status_code}")

            return []
        except Exception as e:
            print(f"获取枪械饰品异常: {e}")
            import traceback
            traceback.print_exc()
            return []

    def filter_cheap_guns(self, items: List[Dict], max_price: float = 0.3) -> List[Dict]:
        """筛选价格小于max_price的枪械饰品"""
        cheap_items = []

        for item in items:
            price_str = item.get('sell_min_price', item.get('price', '0'))
            try:
                price = float(price_str)
                if price > 0 and price < max_price:
                    item_info = {
                        'id': item.get('id'),
                        'name': item.get('name', ''),
                        'price': price,
                        'sell_num': item.get('sell_num', 0),
                        'goods_id': item.get('id'),
                        'steam_market_url': item.get('steam_market_url', '')
                    }
                    cheap_items.append(item_info)
                    print(f"找到符合条件的枪械: {item.get('name', '')} - {price}元")
                    print(f"商品ID: {item.get('id')}, Steam市场链接: {item.get('steam_market_url', 'N/A')}")
            except Exception as e:
                print(f"处理价格失败: {e}")
                print(f"价格字段: {item.get('sell_min_price')}, {item.get('price')}")
        print(f"筛选出 {len(cheap_items)} 个价格小于 {max_price} 元的枪械饰品")
        return cheap_items

    def get_sell_orders(self, goods_id: str, charm_id: str = "") -> List[Dict]:
        """获取饰品的所有卖家订单"""
        try:
            print(f"获取饰品 {goods_id} 的卖家订单列表...")
            sell_order_url = f"{self.BASE_URL}/api/market/goods/sell_order"
            sell_order_params = {
                "game": self.game,
                "goods_id": goods_id,
                "page_num": 1,
                "sort_by": "default",
                "mode": "",
                "allow_tradable_cooldown": 1
            }

            if charm_id:
                sell_order_params["charm"] = charm_id
                print(f"添加charm参数: {charm_id}")

            sell_order_response = self.session.get(sell_order_url, params=sell_order_params, timeout=15)

            if sell_order_response.status_code == 200:
                sell_order_data = sell_order_response.json()
                if sell_order_data.get('code') == 'OK':
                    sell_orders = sell_order_data.get('data', {}).get('items', [])
                    print(f"获取到 {len(sell_orders)} 个卖家订单")

                    if sell_orders:
                        print("第一个卖家订单简略:")
                        print(json.dumps({
                            'order_id': sell_orders[0].get('order_id'),
                            'price': sell_orders[0].get('price'),
                            'sell_num': sell_orders[0].get('sell_num'),
                            'user_id': sell_orders[0].get('user_id')
                        }, ensure_ascii=False, indent=2))
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

    def buy_item(self, goods_id: str, price: float, charm_id: str = "", max_price: float = 0.3, max_orders: int = 5, tried_items=None) -> List[Dict]:
        """购买带有挂件的饰品（支持购买多个报价）"""
        results = []
        if tried_items is None:
            tried_items = []

        try:
            print(f"尝试购买饰品 ID: {goods_id}, 目标价格: {price}元")

            new_session, csrf_token, goods_page_url = self._init_buy_session(goods_id)

            if not csrf_token:
                print("警告: 未能获取CSRF token")
                html_content = new_session.get(goods_page_url, timeout=15).text if goods_page_url else ""
                if html_content:
                    print("页面HTML前1000字符:")
                    print(html_content[:1000])

            # 获取卖家订单列表
            print("获取卖家订单列表...")
            sell_order_url = f"{self.BASE_URL}/api/market/goods/sell_order"
            sell_order_params = {
                "game": self.game,
                "goods_id": goods_id,
                "page_num": 1,
                "sort_by": "default",
                "mode": "",
                "allow_tradable_cooldown": 1
            }

            if charm_id:
                sell_order_params["charm"] = charm_id
                print(f"添加charm参数: {charm_id}")

            browser_headers = self._get_browser_headers()
            order_headers = {
                **browser_headers,
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
                print(f"响应内容: {sell_order_response.text[:200]}...")

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

            if not eligible_orders:
                print("未找到符合价格条件的卖家订单")
                results.append({'success': False, 'message': "未找到符合价格条件的卖家订单"})
                return results

            print(f"共找到 {len(eligible_orders)} 个符合条件的订单，将尝试购买前 {min(max_orders, len(eligible_orders))} 个")

            headers = self._build_buy_headers(csrf_token, goods_page_url)

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
                    headers["X-CSRF-Token"] = csrf_token
                    headers["Csrf-Token"] = csrf_token

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

                print("发起购买请求...")
                buy_response = new_session.post(buy_url, json=buy_data, headers=headers, timeout=15)

                print(f"购买请求状态码: {buy_response.status_code}")
                print(f"购买请求响应: {buy_response.text[:200]}...")

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

                time.sleep(4)

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

    def run(self, max_price: float = 0.3, max_pages: int = None, max_items: int = 5, tried_items=None):
        """运行主流程"""
        if max_pages is None:
            max_pages = self.event_config.default_max_pages

        print("=== BUFF挂件搜枪脚本 ===")
        print(f"游戏: {self.game}")
        print(f"事件: {self.event_config.name}")
        print(f"目标: 查找价格 < {max_price}元的带有挂件的枪械饰品")
        print(f"最大页数: {max_pages}")
        print(f"最大购买数量: {max_items}")
        print(f"已尝试商品数量: {len(tried_items) if tried_items else 0}")

        if not self.test_login():
            print("请先设置有效的cookie")
            return

        if tried_items is None:
            tried_items = []

        # 获取挂件饰品
        all_charms = []
        page = 1
        while page <= max_pages:
            print(f"\n=== 获取第 {page} 页挂件饰品 ===")
            items = self.get_charms(page_num=page, page_size=20)
            if not items:
                break
            all_charms.extend(items)
            page += 1
            time.sleep(1)

        print(f"\n=== 总计获取到 {len(all_charms)} 个挂件饰品 ===")

        print(f"\n=== 开始查找并购买符合条件的饰品 ===")
        print(f"最大购买数量: {max_items}")

        purchases = []
        purchased_count = 0
        all_cheap_guns = []

        for i, charm in enumerate(all_charms):
            if purchased_count >= max_items:
                break

            charm_id = charm.get('id')
            charm_name = charm.get('name', '')
            print(f"\n=== 处理第 {i+1} 个挂件: {charm_name} (ID: {charm_id}) ===")

            custom_charm_id = self.get_custom_charm_id(charm_id)

            if not custom_charm_id:
                custom_charm_id = charm_id
                print(f"未找到custom_charm ID，使用挂件ID作为备选: {custom_charm_id}")

            print(f"使用的custom_charm ID: {custom_charm_id}")

            time.sleep(random.uniform(0.5, 1.5))

            guns = self.get_guns_with_charm(custom_charm_id, page_num=1, page_size=50)
            if not guns:
                continue

            cheap_guns = self.filter_cheap_guns(guns, max_price)
            all_cheap_guns.extend(cheap_guns)

            for gun in cheap_guns:
                if purchased_count >= max_items:
                    break

                gun_id = gun['id']
                gun_name = gun['name']
                gun_price = gun['price']

                print(f"\n=== 购买第 {purchased_count+1} 个饰品: {gun_name} (ID: {gun_id}) ===")
                print(f"价格: {gun_price}元")

                results = self.buy_item(gun_id, gun_price, charm_id=custom_charm_id, max_price=max_price, max_orders=1, tried_items=tried_items)
                purchases.extend(results)

                for result in results:
                    if result.get('success'):
                        purchased_count += 1
                        print(f"购买成功，已购买 {purchased_count} 个饰品")
                        break

                time.sleep(2)

            time.sleep(1)

        print(f"\n=== 总计找到 {len(all_cheap_guns)} 个价格小于 {max_price} 元的带有挂件的枪械饰品 ===")
        if all_cheap_guns:
            print("\n符合条件的饰品列表：")
            for i, gun in enumerate(all_cheap_guns):
                print(f"{i+1}. {gun['name']} - {gun['price']}元")
                print(f"   商品ID: {gun['id']}")
                print(f"   Steam市场链接: {gun.get('steam_market_url', 'N/A')}")
                print("-" * 80)
        else:
            print("未找到符合条件的饰品")

        self.print_purchase_status(purchases)

        print("\n=== 脚本运行完成 ===")
