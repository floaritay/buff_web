"""
BUFF饰品购买脚本

功能：
- 自动登录BUFF网站（使用Cookie）
- 筛选涂鸦类饰品
- 查找价格≤5分钱的饰品
- 使用BUFF可用资金购买
- 购买后请求卖家发送报价
- 自动保存和加载Cookie

使用方法：
1. 首次运行时输入BUFF网站的Cookie
2. 后续运行无需手动输入Cookie
3. Cookie失效时会自动提示重新输入
"""

import requests
import time
import json
from typing import List, Dict

class BuffBuyer:
    """BUFF饰品购买类
    
    实现从BUFF网站筛选、购买涂鸦饰品的完整流程
    """
    
    def __init__(self, game: str = "csgo"):
        """初始化BUFF购买器

        输入：
        game: 游戏名称，默认csgo
        """
        self.game = game
        self.session = requests.Session() # 会话对象，用于保持登录状态
        # 设置请求头，模拟浏览器行为
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
        self.session.headers.update(self.headers) # 更新会话的请求头
    
    def set_cookie(self, cookie_str: str) -> bool:
        """手动设置cookie

        输入：
        cookie_str: BUFF网站的Cookie字符串

        返回：
        bool: Cookie设置是否成功
        """
        if not cookie_str:
            print("错误: Cookie不能为空")
            return False
        
        # 解析Cookie字符串
        cookies = {}
        cookie_items = cookie_str.split(';')
        
        for item in cookie_items:
            item = item.strip()
            if '=' in item: # 过滤空项
                try:
                    key, value = item.split('=', 1)
                    cookies[key] = value
                except:
                    pass
        
        if not cookies:
            print("错误: 无法解析Cookie")
            return False
        
        # 检查关键Cookie项
        required_cookies = ['session', 'remember_me', '_ntes']
        has_required = any(key in cookies for key in required_cookies)
        
        if not has_required:
            print("警告: Cookie可能缺少关键项（'session', 'remember_me', '_ntes'），可能无法正常登录")
        
        self.session.cookies.update(cookies)
        print(f"Cookie设置成功，解析到 {len(cookies)} 个Cookie项")
        return True
    
    def test_login(self) -> bool:
        """测试登录状态
        
        返回：
        bool: 登录状态是否正常
        """
        try:
            # 发送测试请求，检查登录状态
            url = f"https://buff.163.com/api/market/goods?game={self.game}&page_num=1&page_size=10"
            response = self.session.get(url, timeout=10)
            
            # 检查响应状态和返回数据
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
    
    def get_graffiti(self, page_num: int = 1, page_size: int = 20) -> List[Dict]:
        """获取涂鸦类饰品
        
        输入：
        page_num: 页码，默认为1
        page_size: 每页数量，默认为20
        
        返回：
        List[Dict]: 涂鸦饰品列表
        """
        # 尝试不同的分类参数组合
        try:
            url = f"https://buff.163.com/api/market/goods"
            
            # 尝试不同的分类参数组合（第一项就可以）
            params_list = [
                {
                    "game": self.game,
                    "page_num": page_num,
                    "page_size": page_size,
                    "category": "csgo_type_spray",  # 涂鸦分类参数
                    "sort_by": "price.asc"
                },
                {
                    "game": self.game,
                    "page_num": page_num,
                    "page_size": page_size,
                    "category_group": "spray",  # 备选参数
                    "sort_by": "price.asc"
                },
                {
                    "game": self.game,
                    "page_num": page_num,
                    "page_size": page_size,
                    "category": "spray",  # 备选参数
                    "sort_by": "price.asc"
                }
            ]
            
            for params in params_list:
                # 添加更多反爬措施
                headers = {
                    **self.headers, # 合并基础请求头
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Connection": "keep-alive",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache"
                }
                
                # 随机延迟
                import random
                time.sleep(random.uniform(0.5, 1.5))
                
                # 增加超时重试
                max_retries = 3 # 最大重试次数
                for retry in range(max_retries):
                    try:
                        response = self.session.get(url, params=params, headers=headers, timeout=20)
                        break
                    except requests.exceptions.Timeout: # 超时异常处理
                        print(f"请求超时，正在重试 ({retry+1}/{max_retries})...")
                        if retry == max_retries - 1:
                            raise
                
                # 详细日志
                print(f"请求URL: {response.url}")
                print(f"响应状态: {response.status_code}")
                
                if response.status_code == 200: # 成功响应处理
                    data = response.json()
                    print(f"响应代码: {data.get('code')}") # 打印响应代码
                    
                    if data.get('code') == 'OK':
                        items = data.get('data', {}).get('items', []) # 获取物品列表
                        if items:
                            # 检查是否为涂鸦类饰品
                            first_item_name = items[0].get('name', '')
                            print(f"第一个饰品名称: {first_item_name}")
                            
                            # 更宽松的识别逻辑
                            is_graffiti = any(keyword in first_item_name for keyword in ['涂鸦', 'spray', 'Graffiti', '喷漆'])
                            
                            if is_graffiti:
                                print(f"获取到 {len(items)} 个涂鸦饰品")
                                # 简化版：仅打印关键字段，减少日志冗余
                                first = items[0]
                                print("第一个饰品简要信息:", json.dumps({
                                    "id": first.get("id"),
                                    "name": first.get("name"),
                                    "price": first.get("sell_min_price")
                                }, ensure_ascii=False))
                                # 详细版：打印第一个饰品的完整 JSON 信息，包含所有字段，便于调试和查看数据结构
                                # print("第一个饰品完整信息（调试版）:", json.dumps(items[0], ensure_ascii=False, indent=2))
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
            traceback.print_exc() # 打印异常栈跟踪
            return []
    
    def filter_cheap_items(self, items: List[Dict], max_price: float = 0.05) -> List[Dict]:
        """筛选价格小于等于max_price的饰品
        
        输入:
            items: 饰品列表
            max_price: 最大价格，默认为0.05元
            
        返回:
            List[Dict]: 符合条件的饰品列表
        """
        cheap_items = []
        for item in items:
            # 确保是涂鸦类饰品
            item_name = item.get('name', '')
            # item_name.lower() 转换为小写进行匹配
            if '涂鸦' not in item_name and 'spray' not in item_name.lower() and 'graffiti' not in item_name.lower():
                continue # 不是涂鸦类饰品，跳过
            
            # 处理价格
            # 尝试获取不同的价格字段
            price_str = item.get('sell_min_price', item.get('price', '0')) # 获取最小销售价格，默认0
            try:
                price = float(price_str)
                # 过滤异常价格（如0元）
                if price > 0 and price <= max_price:
                    item_info = {
                        'id': item.get('id'),
                        'name': item_name,
                        'price': price,
                        'sell_num': item.get('sell_num', 0),
                        'goods_id': item.get('id'),  # 使用id作为goods_id
                        'steam_market_url': item.get('steam_market_url', '')  # 添加steam市场链接
                    }
                    cheap_items.append(item_info)
                    print(f"找到符合条件的涂鸦: {item_name} - {price}元")
                    # print(f"商品ID: {item.get('id')}, Steam市场链接: {item.get('steam_market_url', 'N/A')}")
            except Exception as e:
                print(f"处理价格失败: {e}")
                print(f"价格字段: {item.get('sell_min_price')}, {item.get('price')}")
                pass
        print(f"筛选出 {len(cheap_items)} 个价格小于等于 {max_price} 元的涂鸦饰品")
        return cheap_items
    
    def get_sell_orders(self, goods_id: str) -> List[Dict]:
        """获取饰品的所有卖家订单
        
        输入:
            goods_id: 商品ID
            
        返回:
            List[Dict]: 卖家订单列表
        """
        try:
            print(f"获取饰品 {goods_id} 的卖家订单列表...")
            sell_order_url = "https://buff.163.com/api/market/goods/sell_order"
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
                        
                        # 打印第一个订单的信息
                        if sell_orders:
                            # print("第一个卖家订单详情:")
                            # print(json.dumps(sell_orders[0], ensure_ascii=False, indent=2))
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
        """购买饰品（支持购买多个报价）
        
        输入:
            goods_id: 商品ID
            price: 购买价格
            max_price: 最大价格，默认为0.04元
            max_orders: 最大尝试购买的订单数量，默认为5
            tried_items: 已尝试购买的商品记录列表
            
        返回:
            List[Dict]: 购买结果列表
        """
        results = []
        if tried_items is None:
            tried_items = []
        
        try:
            print(f"尝试购买饰品 ID: {goods_id}, 目标价格: {price}元")
            
            # 清除旧的 csrf_token cookie，防止多个同名 cookie 导致服务端校验失败
            old_csrf = [c for c in self.session.cookies if c.name == 'csrf_token']
            for c in old_csrf:
                self.session.cookies.clear(c.domain, c.path, c.name)
            
            # 访问商品页面以获取新的 CSRF token（模拟浏览器行为）
            print("访问商品页面以刷新CSRF token...")
            goods_page_url = f"https://buff.163.com/goods/{goods_id}"
            self.session.get(goods_page_url, timeout=10)
            
            # 从 session cookies 中提取 CSRF token
            csrf_token = ""
            for cookie in self.session.cookies:
                if cookie.name == 'csrf_token':
                    csrf_token = cookie.value
            if csrf_token:
                print(f"获取到CSRF token: {csrf_token[:20]}...")
            else:
                print("警告: 未能从cookies中获取CSRF token")
            
            # 获取卖家订单列表
            sell_orders = self.get_sell_orders(goods_id)
            
            if not sell_orders:
                print("未找到卖家订单")
                results.append({
                    'success': False,
                    'message': "未找到卖家订单"
                })
                return results
            
            # 筛选符合价格条件的订单，并检查是否已经尝试过
            eligible_orders = []
            for order in sell_orders:
                order_price = float(order.get('price', '0'))
                order_id = str(order.get('id'))  # 确保是字符串
                
                # 检查价格是否符合条件（价格≤max_price）
                if order_price <= max_price:
                    # 检查订单是否已经尝试过（即之前购买失败，多半是因为卖家原因，而无法请求卖家发送报价）
                    is_order_tried = any(
                        str(tried.get('order_id')) == order_id # 根据 订单ID 检查是否已经尝试过
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
                    break  # 按价格升序排列，遇到价格过高的就停止
            
            if not eligible_orders:
                print("未找到符合价格条件的卖家订单")
                results.append({
                    'success': False,
                    'message': "未找到符合价格条件的卖家订单"
                })
                return results
            
            print(f"共找到 {len(eligible_orders)} 个符合条件的订单，将尝试购买前 {min(max_orders, len(eligible_orders))} 个")
            
            # 添加必要的头信息
            headers = {
                **self.headers,
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
                "Origin": "https://buff.163.com",
                "Referer": f"https://buff.163.com/goods/{goods_id}",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Microsoft Edge";v="122"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
            }
            
            # 如果获取到了CSRF token，添加到请求头
            if csrf_token:
                headers["X-CSRFToken"] = csrf_token
            
            # 尝试购买每个符合条件的订单
            for i, order in enumerate(eligible_orders[:max_orders]):
                sell_order_id = str(order.get('id'))  # 确保是字符串
                order_price = float(order.get('price', '0'))
                
                print(f"\n尝试购买第 {i+1} 个订单: ID={sell_order_id}, 价格={order_price}元")
                print(f"订单ID类型: {type(sell_order_id)}")
                
                # 创建订单尝试记录
                order_attempt_info = {
                    'id': str(goods_id),
                    'name': '',  # 稍后从结果中获取
                    'price': order_price,
                    'steam_market_url': '',  # 稍后从结果中获取
                    'attempt_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'attempted',
                    'order_id': sell_order_id,
                    'attempt_number': i + 1
                }
                
                # 添加到已尝试列表，避免重复尝试
                tried_items.append(order_attempt_info)
                
                # 发起购买请求
                buy_url = "https://buff.163.com/api/market/goods/buy"
                buy_data = {
                    "game": self.game,
                    "goods_id": goods_id,
                    "sell_order_id": sell_order_id,
                    "price": order_price,
                    "allow_tradable_cool_down": 0,
                    "hide_non_epay": True,
                    "pay_method": 1,
                    "seller_order_id": sell_order_id,
                }
                
                # 打印购买请求数据（调试用）
                print("\n购买请求数据:")
                print(json.dumps(buy_data, ensure_ascii=False, indent=2))
                
                # 发起购买请求
                buy_response = self.session.post(buy_url, json=buy_data, headers=headers, timeout=15)
                
                print(f"购买请求状态码: {buy_response.status_code}")
                print(f"购买请求响应: {buy_response.text[:100]}...") # 只显示前100字符
                
                if buy_response.status_code == 200:
                    buy_result = buy_response.json()
                    if buy_result.get('code') == 'OK':
                        print(f"购买成功")
                        
                        # 请求卖家发送报价
                        print("请求卖家发送报价...")
                        
                        # 1. 尝试从购买结果中获取订单号
                        bill_order_id = None
                        
                        # 尝试不同的字段名
                        possible_fields = ['bill_order_id', 'order_id', 'id'] # ‘id’就可以
                        for field in possible_fields:
                            bill_order_id = buy_result.get('data', {}).get(field)
                            if bill_order_id:
                                print(f"从{field}字段获取到订单号: {bill_order_id}")
                                break
                        
                        # 2. 如果找不到，尝试获取最新的订单
                        if not bill_order_id:
                            print("尝试获取最新的订单...")
                            orders_url = "https://buff.163.com/api/market/bill_order"
                            orders_params = {
                                "game": self.game,
                                "page_num": 1,
                                "status": "pending"
                            }
                            orders_response = self.session.get(orders_url, params=orders_params, timeout=15)
                            
                            if orders_response.status_code == 200:
                                orders_data = orders_response.json()
                                if orders_data.get('code') == 'OK':
                                    orders = orders_data.get('data', {}).get('items', [])
                                    if orders:
                                        # 获取第一个订单
                                        latest_order = orders[0]
                                        bill_order_id = latest_order.get('id')
                                        print(f"获取到最新订单: {bill_order_id}")
                        
                        # 3. 打印购买结果，便于分析
                        if not bill_order_id:
                            print("购买结果数据:")
                            print(json.dumps(buy_result, ensure_ascii=False, indent=2))
                            print("无法获取订单号，跳过请求卖家发送报价")
                        
                        if bill_order_id:
                            ask_seller_url = "https://buff.163.com/api/market/bill_order/ask_seller_to_send_offer"
                            ask_seller_data = {
                                "bill_orders": [bill_order_id],
                                "game": self.game,
                                "steamid": None
                            }
                            
                            ask_seller_response = self.session.post(ask_seller_url, json=ask_seller_data, headers=headers, timeout=15)
                            
                            print(f"请求卖家发送报价状态码: {ask_seller_response.status_code}")
                            print(f"请求卖家发送报价响应: {ask_seller_response.text[:300]}...")
                            
                            if ask_seller_response.status_code == 200:
                                ask_seller_result = ask_seller_response.json()
                                if ask_seller_result.get('code') == 'OK':
                                    print("请求卖家发送报价成功")
                                else:
                                    print(f"请求卖家发送报价失败: {ask_seller_result.get('msg', '未知错误')}")
                            else:
                                print(f"请求卖家发送报价请求失败，状态码: {ask_seller_response.status_code}")
                        else:
                            print("未找到订单号，无法请求卖家发送报价")
                            print("您可以手动在BUFF手机端上请求卖家发送报价")
                        
                        # 使用已经获取到的bill_order_id作为订单号
                        order_id_to_display = bill_order_id if bill_order_id else buy_result.get('data', {}).get('order_id', 'N/A')
                        results.append({
                            'success': True,
                            'message': f"购买成功，饰品ID: {goods_id}，价格: {order_price}元，订单号: {order_id_to_display}"
                        })
                    else:
                        error_msg = buy_result.get('error', buy_result.get('msg', '购买失败'))
                        print(f"购买失败: {error_msg}")
                        results.append({
                            'success': False,
                            'message': f"购买失败: {error_msg}"
                        })
                else:
                    print(f"购买请求失败，状态码: {buy_response.status_code}")
                    results.append({
                        'success': False,
                        'message': f"购买请求失败，状态码: {buy_response.status_code}"
                    })
                
                # 购买间隔
                time.sleep(2)
                
        except Exception as e:
            print(f"购买失败: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'success': False,
                'message': str(e)
            })
        
        return results
    
    def print_purchase_status(self, purchases: List[Dict]):
        """打印购买情况
        
        Args:
            purchases: 购买结果列表
        """
        print("\n=== 购买情况 ===")
        total_cost = 0
        success_count = 0
        
        for i, purchase in enumerate(purchases, 1):
            print(f"{i}. {purchase['message']}")
            if purchase['success']:
                success_count += 1
                # 提取价格并累加
                import re
                price_match = re.search(r'价格: (\d+\.\d+)元', purchase['message'])
                if price_match:
                    total_cost += float(price_match.group(1))
        
        print(f"\n总计: 尝试购买 {len(purchases)} 个饰品")
        print(f"成功: {success_count} 个")
        print(f"失败: {len(purchases) - success_count} 个")
        print(f"总花费: {total_cost:.2f} 元")
    
    def run(self, max_price: float = 0.05, max_items: int = 10, tried_items=None):
        """运行主流程
        
        Args:
            max_price: 最大价格，默认为0.05元
            max_items: 最大购买数量，默认为10
            tried_items: 已尝试购买的商品记录列表
        """
        if tried_items is None:
            tried_items = []
        
        print("=== BUFF饰品购买脚本 ===")
        print(f"游戏: {self.game}")
        print(f"目标: 购买价格 <= {max_price}元的涂鸦饰品")
        print(f"最大购买数量: {max_items}")
        print(f"已尝试商品数量: {len(tried_items)}")
        
        # 测试登录状态
        if not self.test_login():
            print("请先设置有效的cookie")
            return
        
        # 获取涂鸦饰品
        all_items = []
        page = 1
        while len(all_items) < max_items * 2:  # 获取足够的物品进行筛选，默认获取20个物品（刚好一页）
            items = self.get_graffiti(page_num=page, page_size=20)
            if not items:
                break
            all_items.extend(items)
            page += 1
            time.sleep(1)  # 避免请求过快
        
        # 筛选低价饰品
        cheap_items = self.filter_cheap_items(all_items, max_price)
        if not cheap_items:
            print("没有找到符合条件的饰品")
            return
        
        # 不过滤已尝试的商品，允许尝试购买所有符合条件的商品
        # 这样即使是同一个商品，也可以尝试购买多个报价
        filtered_items = cheap_items
        print(f"找到 {len(filtered_items)} 个符合条件的商品，准备尝试购买")
        
        if not filtered_items:
            print("没有找到符合条件的饰品")
            return
        
        # 购买饰品
        purchases = []
        for item in filtered_items[:max_items]:  # 限制购买数量
            print(f"\n准备购买: {item['name']} - {item['price']}元")
            
            # 记录商品信息
            item_info = {
                'id': str(item.get('id', '')),
                'name': item.get('name', ''),
                'price': item.get('price', 0),
                'steam_market_url': item.get('steam_market_url', ''),
                'attempt_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'attempted'
            }
            
            # 尝试购买（支持多个报价）
            results = self.buy_item(item['goods_id'], item['price'], max_price, tried_items=tried_items)
            
            # 处理每个购买结果
            for i, result in enumerate(results):
                # 为每个尝试创建一个新的记录
                item_info = {
                    'id': str(item.get('id', '')),
                    'name': item.get('name', ''),
                    'price': item.get('price', 0),
                    'steam_market_url': item.get('steam_market_url', ''),
                    'attempt_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'attempted'
                }
                
                # 更新尝试状态
                if result.get('success'):
                    item_info['status'] = 'success'
                    # 提取订单号
                    order_id = result.get('message', '').split('订单号: ')[-1] if '订单号: ' in result.get('message', '') else ''
                    item_info['order_id'] = order_id
                    item_info['attempt_number'] = i + 1
                else:
                    item_info['status'] = 'failed'
                    item_info['error_message'] = result.get('message', '')
                    item_info['attempt_number'] = i + 1
                
                # 添加到已尝试列表
                tried_items.append(item_info)
                print(f"已将商品添加到尝试记录: {item['name']} (尝试 #{i+1}, 状态: {item_info['status']})")
            
            # 将所有结果添加到purchases列表
            purchases.extend(results)
            
            time.sleep(2)  # 购买间隔
        
        # 打印购买情况
        self.print_purchase_status(purchases)
        print("\n=== 脚本运行完成 ===")

import os

def save_cookie(cookie_str, file_path=None):
    """保存cookie到环境变量"""
    try:
        # 存储到环境变量
        os.environ['BUFF_COOKIE'] = cookie_str
        print("Cookie已保存到环境变量")
    except Exception as e:
        print(f"保存Cookie失败: {e}")

def load_cookie(file_path=None):
    """从环境变量加载cookie"""
    try:
        cookie_str = os.environ.get('BUFF_COOKIE', '')
        if cookie_str:
            print("从环境变量加载Cookie成功")
            return cookie_str
        print("环境变量中未找到Cookie")
        return ""
    except Exception as e:
        print(f"加载Cookie失败: {e}")
        return ""

def save_tried_items(tried_items, file_path=None):
    """保存已尝试购买的商品记录"""
    # 使用绝对路径，确保从任何目录运行都能找到文件
    if file_path is None:
        try:
            # 尝试获取脚本所在目录的绝对路径
            script_dir = os.path.dirname(os.path.abspath(__file__))
        except Exception:
            # 如果获取失败，使用当前脚本的绝对路径
            script_dir = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
        file_path = os.path.join(script_dir, "tried_items.json")
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(tried_items, f, ensure_ascii=False, indent=2)
        print(f"已尝试商品记录已保存到 {file_path}")
        print(f"共记录 {len(tried_items)} 个已尝试商品")
    except Exception as e:
        print(f"保存已尝试商品记录失败: {e}")

def load_tried_items(file_path=None):
    """从文件加载已尝试购买的商品记录"""
    # 使用绝对路径，确保从任何目录运行都能找到文件
    if file_path is None:
        try:
            # 尝试获取脚本所在目录的绝对路径
            script_dir = os.path.dirname(os.path.abspath(__file__))
        except Exception:
            # 如果获取失败，使用当前脚本的绝对路径
            script_dir = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
        file_path = os.path.join(script_dir, "tried_items.json")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tried_items = json.load(f)
        print(f"从 {file_path} 加载已尝试商品记录成功")
        print(f"共加载 {len(tried_items)} 个已尝试商品")
        return tried_items
    except FileNotFoundError:
        print(f"{file_path} 文件不存在，创建新记录")
        return []
    except Exception as e:
        print(f"加载已尝试商品记录失败: {e}")
        return []

if __name__ == "__main__":
    buyer = BuffBuyer(game="csgo")
    
    print("=== BUFF饰品购买脚本 ===")
    print("使用说明：")
    print("1. 首次运行需要输入BUFF网站的Cookie")
    print("2. Cookie会自动保存，下次运行时无需再输入")
    print("3. 当Cookie失效时，系统会提示重新输入")
    print("4. 脚本会自动跳过已尝试购买的商品（包括购买失败的商品和成功的商品）")
    print("5. 商品购买失败原因（1.因为卖家原因无法发送报价，而导致失败。2.采用余额购买，不支持支付宝支付的商品。3.余额不足）")
    print("-" * 60)
    
    # 尝试加载保存的cookie
    cookie_str = load_cookie()
    
    # 如果没有保存的cookie或cookie无效，要求用户输入
    if not cookie_str or not buyer.set_cookie(cookie_str) or not buyer.test_login():
        print("需要输入新的Cookie")
        print("使用说明：")
        print("1. 在浏览器中登录BUFF网站")
        print("2. 按F12打开开发者工具")
        print("3. 切换到网络标签，刷新页面")
        print("4. 找到任意API请求，复制请求头中的Cookie")
        print("5. 在下方粘贴Cookie值")
        print("-" * 60)
        
        # 改进的Cookie输入
        while True:
            cookie_str = input("请输入BUFF网站的cookie: ")
            if buyer.set_cookie(cookie_str) and buyer.test_login():
                # 保存新的cookie
                save_cookie(cookie_str)
                break
            print("登录测试显示Cookie无效或错误，请重新输入Cookie")
            print("-" * 60)
    
    # 加载已尝试商品记录
    tried_items = load_tried_items()
    
    # 运行脚本
    buyer.run(max_price=0.05, max_items=10, tried_items=tried_items) # 最大价格0.05，最大购买数量10
    
    # 保存已尝试商品记录
    save_tried_items(tried_items)
