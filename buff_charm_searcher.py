"""
BUFF奥斯汀锦标赛挂件搜枪脚本

功能：
- 自动登录BUFF网站（使用Cookie）
- 遍历"挂件（纪念品）| 2025年奥斯汀锦标赛高光时刻"类的所有饰品
- 点击每个饰品的"挂件搜枪"按钮
- 查找带有该挂件的枪械饰品
- 筛选价格<0.3元的枪械饰品
- 打印符合条件的饰品信息
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
import random

class BuffCharmSearcherAustin:
    """BUFF奥斯汀锦标赛挂件搜枪类
    
    实现从BUFF网站遍历奥斯汀锦标赛挂件饰品，搜索带有该挂件的枪械饰品的完整流程
    """
    
    def __init__(self, game: str = "csgo"):
        """初始化BUFF奥斯汀挂件搜枪器

        输入：
        game: 游戏名称，默认csgo
        """
        self.game = game
        self.session = requests.Session() # 会话对象，用于保持登录状态
        # 设置请求头，模拟浏览器行为
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": f"https://buff.163.com/market/{game}",# 请求的URL
            "X-Requested-With": "XMLHttpRequest",# 标识为Ajax请求
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
    
    def get_charms(self, page_num: int = 1, page_size: int = 20) -> List[Dict]:
        """获取奥斯汀锦标赛挂件（纪念品）类饰品
        
        输入：
        page_num: 页码，默认为1
        page_size: 每页数量，默认为20
        
        返回：
        List[Dict]: 挂件饰品列表
        """
        # 实际接口：https://buff.163.com/api/market/goods?game=csgo&page_num=1&category=csgo_tool_keychain_austin_2025&sort_by=price.asc&tab=selling
        try:
            url = f"https://buff.163.com/api/market/goods"
            
            params = {
                "game": self.game,
                "page_num": page_num,
                "page_size": page_size,
                "category": "csgo_tool_keychain_austin_2025",  # 奥斯汀锦标赛挂件（纪念品）分类参数
                "sort_by": "price.asc",
                "tab": "selling"
            }
            
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
            
            # 增加初始延迟
            # 增加超时重试和429错误处理
            max_retries = 5 # 增加重试次数
            for retry in range(max_retries):
                try:
                    print(f"正在获取奥斯汀锦标赛挂件列表，页码: {page_num} (尝试 {retry+1}/{max_retries})")
                    response = self.session.get(url, params=params, headers=headers, timeout=30)  # 增加超时时间
                    
                    # 检查是否返回429错误
                    if response.status_code == 429:
                        wait_time = random.uniform(5.0, 10.0)  # 增加等待时间
                        print(f"请求过于频繁(429)，正在等待 {wait_time:.2f} 秒并重试 ({retry+1}/{max_retries})...")
                        time.sleep(wait_time)
                        continue
                    break
                except requests.exceptions.Timeout: # 超时异常处理
                    wait_time = random.uniform(5.0, 10.0)
                    print(f"请求超时，正在等待 {wait_time:.2f} 秒并重试 ({retry+1}/{max_retries})...")
                    time.sleep(wait_time)
                    if retry == max_retries - 1:
                        print("达到最大重试次数，无法获取挂件列表")
                        raise # 抛出异常
                except Exception as e:
                    wait_time = random.uniform(5.0, 10.0)
                    print(f"请求异常: {e}，正在等待 {wait_time:.2f} 秒并重试 ({retry+1}/{max_retries})...")
                    time.sleep(wait_time)
                    if retry == max_retries - 1:
                        print("达到最大重试次数，无法获取挂件列表")
                        raise # 抛出异常
            
            # 详细日志
            print(f"请求URL: {response.url}")
            print(f"响应状态: {response.status_code}")
            
            if response.status_code == 200: # 成功响应处理
                data = response.json()
                print(f"响应代码: {data.get('code')}") # 打印响应代码
                
                if data.get('code') == 'OK':
                    items = data.get('data', {}).get('items', []) # 获取物品列表
                    if items:
                        # 检查是否为奥斯汀锦标赛挂件类饰品
                        first_item_name = items[0].get('name', '')
                        print(f"第一个饰品名称: {first_item_name}")
                        
                        # 已确认是奥斯汀锦标赛挂件类饰品，无需再次识别
                        print(f"获取到 {len(items)} 个奥斯汀锦标赛挂件饰品")
                        # 打印第一个饰品的简要信息
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
                    # 打印错误详情
                    print(f"错误详情: {data.get('error', '无错误详情')}")
                    print(f"消息: {data.get('msg', '无消息')}")
            else:
                print(f"请求失败，状态码: {response.status_code}")
                # 尝试打印响应内容
                try:
                    error_data = response.json()
                    print(f"错误响应: {error_data}")
                except:
                    print(f"错误响应内容: {response.text[:200]}...")
            
            return []
        except Exception as e:
            print(f"获取奥斯汀锦标赛挂件饰品异常: {e}")
            import traceback
            traceback.print_exc() # 打印异常栈跟踪
            return []
    
    def get_charm_id(self, goods_id: str) -> str:
        """从页面中获取charm ID
        
        输入：
        goods_id: 挂件商品ID
        
        返回：
        str: charm ID
        """
        # 直接尝试从页面中提取
        try:
            # 访问挂件页面
            url = f"https://buff.163.com/goods/{goods_id}"
            
            # 添加更多反爬措施
            headers = {
                **self.headers, # 合并基础请求头
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
            
            # 增加初始延迟
            print("获取charm ID前延迟...")
            import random
            time.sleep(random.uniform(1.0, 2.0))
            
            # 增加超时重试和429错误处理
            max_retries = 5 # 增加重试次数
            for retry in range(max_retries):
                try:
                    print(f"正在获取挂件页面 {url} (尝试 {retry+1}/{max_retries})")
                    response = self.session.get(url, headers=headers, timeout=30)  # 增加超时时间
                    
                    # 检查是否返回429错误
                    if response.status_code == 429:
                        wait_time = random.uniform(5.0, 10.0)  # 增加等待时间
                        print(f"请求过于频繁(429)，正在等待 {wait_time:.2f} 秒并重试 ({retry+1}/{max_retries})...")
                        time.sleep(wait_time)
                        continue
                    
                    # 检查其他错误状态码
                    if response.status_code != 200:
                        wait_time = random.uniform(5.0, 10.0)
                        print(f"请求失败，状态码: {response.status_code}，正在等待 {wait_time:.2f} 秒并重试 ({retry+1}/{max_retries})...")
                        time.sleep(wait_time)
                        continue
                    
                    break
                except requests.exceptions.Timeout: # 超时异常处理
                    wait_time = random.uniform(5.0, 10.0)
                    print(f"请求超时，正在等待 {wait_time:.2f} 秒并重试 ({retry+1}/{max_retries})...")
                    time.sleep(wait_time)
                    if retry == max_retries - 1:
                        print("达到最大重试次数，无法获取页面内容")
                        raise
                except Exception as e:
                    wait_time = random.uniform(3.0, 5.0)
                    print(f"请求异常: {e}，正在等待 {wait_time:.2f} 秒并重试 ({retry+1}/{max_retries})...")
                    time.sleep(wait_time)
                    if retry == max_retries - 1:
                        print("达到最大重试次数，无法获取页面内容")
                        raise
            
            # 详细日志
            print(f"请求URL: {response.url}")
            print(f"响应状态: {response.status_code}")
            
            if response.status_code == 200: # 成功响应处理
                html_content = response.text
                print(f"页面大小: {len(html_content)} 字符")
                
                # 使用正则表达式从HTML中提取"挂件搜枪"链接
                import re
                # 尝试查找包含"charm"和"id"的JavaScript对象
                # 更精确的正则表达式，匹配用户提供的截图中的模式
                js_charm_match = re.search(r'"charm"\s*:\s*\{[^}]*"id"\s*:\s*(\d+)', html_content)
                if js_charm_match:
                    custom_charm_id = js_charm_match.group(1)
                    print(f"从JavaScript对象中提取到custom_charm ID: {custom_charm_id}")
                    return custom_charm_id
                
                # 打印更多HTML内容，便于分析
                charm_section = re.search(r'[^{]*charm[^{}]*', html_content)
                if charm_section:
                    print(f"页面HTML中包含'charm'的部分: {charm_section.group(0)[:200]}...")
                else:
                    print("未找到包含'charm'的HTML部分")
                
                print("未在页面中找到custom_charm ID")
                # 打印部分HTML内容以便调试
                print(f"页面前500字符: {html_content[:500]}")
            else:
                print(f"请求失败，状态码: {response.status_code}")
            
            return ""
        except Exception as e:
            print(f"从页面提取charm ID异常: {e}")
            import traceback
            traceback.print_exc() # 打印异常栈跟踪
            return ""
        except Exception as e:
            print(f"从页面提取charm ID异常: {e}")
            import traceback
            traceback.print_exc() # 打印异常栈跟踪
            return ""
    
    def get_guns_with_charm(self, charm_id: str, page_num: int = 1, page_size: int = 20) -> List[Dict]:
        """获取带有特定挂件的枪械饰品
        
        输入：
        charm_id: 挂件的charm ID
        page_num: 页码，默认为1
        page_size: 每页数量，默认为20
        
        返回：
        List[Dict]: 枪械饰品列表
        """
        # 检查charm_id是否有效
        if not charm_id:
            print("无效的charm_id，无法获取枪械饰品")
            return []
        
        try:
            # 使用正确的API端点获取带有特定挂件的枪械饰品
            # 注意：这里使用的是市场列表API，需要添加分类参数来过滤出枪械饰品
            url = f"https://buff.163.com/api/market/goods"
            
            # 使用正确的参数
            params = {
                "game": self.game,
                "page_num": page_num,
                "page_size": page_size,
                "charm": charm_id,  # 正确的参数名是charm
                "sort_by": "price.asc",
                "tab": "selling"  # 需要包含tab参数
            }
            
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
            
            # 增加随机延迟，避免429错误
            print("获取枪械饰品前延迟...")
            import random
            time.sleep(random.uniform(1.0, 2.0))
            
            # 增加超时重试和429错误处理
            max_retries = 8 # 增加重试次数
            for retry in range(max_retries):
                try:
                    print(f"正在获取带有挂件的枪械饰品 (尝试 {retry+1}/{max_retries})")
                    response = self.session.get(url, params=params, headers=headers, timeout=30)  # 增加超时时间
                    
                    # 检查是否返回429错误
                    if response.status_code == 429:
                        wait_time = random.uniform(5.0, 10.0)  # 增加等待时间
                        print(f"请求过于频繁(429)，正在等待 {wait_time:.2f} 秒并重试 ({retry+1}/{max_retries})...")
                        time.sleep(wait_time)
                        continue
                    
                    # 检查其他错误状态码
                    if response.status_code != 200:
                        wait_time = random.uniform(5.0, 10.0)
                        print(f"请求失败，状态码: {response.status_code}，正在等待 {wait_time:.2f} 秒并重试 ({retry+1}/{max_retries})...")
                        time.sleep(wait_time)
                        continue
                    
                    break
                except requests.exceptions.Timeout: # 超时异常处理
                    wait_time = random.uniform(5.0, 10.0)
                    print(f"请求超时，正在等待 {wait_time:.2f} 秒并重试 ({retry+1}/{max_retries})...")
                    time.sleep(wait_time)
                    if retry == max_retries - 1:
                        print("达到最大重试次数，无法获取枪械饰品")
                        raise # 抛出异常，重试次数用完仍失败
                except Exception as e:
                    wait_time = random.uniform(5.0, 10.0)
                    print(f"请求异常: {e}，正在等待 {wait_time:.2f} 秒并重试 ({retry+1}/{max_retries})...")
                    time.sleep(wait_time)
                    if retry == max_retries - 1:
                        print("达到最大重试次数，无法获取枪械饰品")
                        raise # 抛出异常，重试次数用完仍失败
            
            # 详细日志
            print(f"API请求URL: {response.url}")
            print(f"响应状态: {response.status_code}")
            
            # 打印正确的浏览器URL格式，便于用户查看
            browser_url = f"https://buff.163.com/market/csgo#game=csgo&page_num={page_num}&custom_charm={charm_id}&sort_by=price.asc&tab=selling"
            print(f"浏览器访问URL: {browser_url}")
            
            if response.status_code == 200: # 成功响应处理
                data = response.json()
                print(f"响应代码: {data.get('code')}") # 打印响应代码
                
                if data.get('code') == 'OK':
                    items = data.get('data', {}).get('items', []) # 获取物品列表
                    if items:
                        print(f"从API获取到 {len(items)} 个饰品")
                        # 打印第一个饰品的简要信息
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
                    # 打印错误详情
                    print(f"错误详情: {data.get('error', '无错误详情')}")
                    print(f"消息: {data.get('msg', '无消息')}")
            else:
                print(f"请求失败，状态码: {response.status_code}")
                # 尝试打印响应内容
                try:
                    error_data = response.json()
                    print(f"错误响应: {error_data}")
                except:
                    print(f"错误响应内容: {response.text[:200]}...")
            
            return []
        except Exception as e:
            print(f"获取枪械饰品异常: {e}")
            import traceback
            traceback.print_exc() # 打印异常栈跟踪
            return []
    
    def filter_cheap_guns(self, items: List[Dict], max_price: float = 0.3) -> List[Dict]:
        """筛选价格小于max_price的枪械饰品
        
        输入:
            items: 饰品列表
            max_price: 最大价格，默认为0.3元
            
        返回:
            List[Dict]: 符合条件的饰品列表
        """
        cheap_items = []
        
        for item in items:
            # 处理价格
            # 尝试获取不同的价格字段
            price_str = item.get('sell_min_price', item.get('price', '0')) # 获取最小销售价格，默认0
            try:
                price = float(price_str)
                # 过滤异常价格（如0元）
                if price > 0 and price < max_price:
                    item_info = {
                        'id': item.get('id'),
                        'name': item.get('name', ''),
                        'price': price,
                        'sell_num': item.get('sell_num', 0),
                        'goods_id': item.get('id'),  # 使用id作为goods_id
                        'steam_market_url': item.get('steam_market_url', '')  # 添加steam市场链接
                    }
                    cheap_items.append(item_info)
                    print(f"找到符合条件的枪械: {item.get('name', '')} - {price}元")
                    print(f"商品ID: {item.get('id')}, Steam市场链接: {item.get('steam_market_url', 'N/A')}")
            except Exception as e:
                print(f"处理价格失败: {e}")
                print(f"价格字段: {item.get('sell_min_price')}, {item.get('price')}")
                pass
        print(f"筛选出 {len(cheap_items)} 个价格小于 {max_price} 元的枪械饰品")
        return cheap_items
    
    def get_sell_orders(self, goods_id: str, charm_id: str = "") -> List[Dict]:
        """获取饰品的所有卖家订单
        
        输入:
            goods_id: 商品ID
            charm_id: 挂件ID，用于筛选带有特定挂件的订单
            
        返回:
            List[Dict]: 卖家订单列表
        """
        try:
            print(f"获取饰品 {goods_id} 的卖家订单列表...")
            sell_order_url = "https://buff.163.com/api/market/goods/sell_order"
            sell_order_params = {
                "game": self.game,
                "goods_id": goods_id,
                "page_num": 1,
                "sort_by": "default",
                "mode": "",
                "allow_tradable_cooldown": 1
            }
        
            # 如果提供了charm_id，添加到参数中
            if charm_id:
                sell_order_params["charm"] = charm_id
                print(f"添加charm参数: {charm_id}")
            
            # 增加超时重试和429错误处理
            max_retries = 5 # 增加重试次数
            for retry in range(max_retries):
                try:
                    sell_order_response = self.session.get(sell_order_url, params=sell_order_params, timeout=15)
                    
                    # 检查是否返回429错误
                    if sell_order_response.status_code == 429:
                        print(f"请求过于频繁，正在等待并重试 ({retry+1}/{max_retries})...")
                        # 增加等待时间
                        import random
                        time.sleep(random.uniform(5.0, 10.0))
                        continue
                    
                    break
                except requests.exceptions.Timeout: # 超时异常处理
                    print(f"请求超时，正在重试 ({retry+1}/{max_retries})...")
                    if retry == max_retries - 1:
                        raise # 抛出异常，重试次数用完仍失败
            
            if sell_order_response.status_code == 200:
                sell_order_data = sell_order_response.json()
                if sell_order_data.get('code') == 'OK':
                        sell_orders = sell_order_data.get('data', {}).get('items', [])
                        print(f"获取到 {len(sell_orders)} 个卖家订单")
                        
                        # 打印第一个订单的详细信息，了解数据结构
                        if sell_orders:
                            print("第一个卖家订单简略:")
                            print(json.dumps({
                                'goods_id': sell_orders[0].get('goods_id'),
                                'price': sell_orders[0].get('price'),
                                'idid': sell_orders[0].get('id'),
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
    
    def buy_item(self, goods_id: str, price: float, charm_id: str = "", max_price: float = 0.3, max_orders: int = 1, tried_items=None) -> List[Dict]:
        """购买饰品（支持购买多个报价）
        
        输入:
            goods_id: 商品ID
            price: 购买价格
            charm_id: 挂件ID，用于筛选带有特定挂件的订单
            max_price: 最大价格，默认为0.35元
            max_orders: 最大尝试购买的订单数量，默认为1
            tried_items: 已尝试购买的商品记录列表
            
        返回:
            List[Dict]: 购买结果列表
        """
        results = []
        if tried_items is None:
            tried_items = []
        
        try:
            print(f"尝试购买饰品 ID: {goods_id}, 目标价格: {price}元")
            
            # 先获取最新的CSRF token
            print("获取最新的CSRF token...")
            csrf_url = "https://buff.163.com/api/market/goods"
            csrf_response = self.session.get(csrf_url, params={"game": self.game, "page_num": 1}, timeout=10)
            
            # 从响应的Set-Cookie头中提取CSRF token
            csrf_token = ""
            if 'Set-Cookie' in csrf_response.headers:
                for cookie in csrf_response.headers['Set-Cookie'].split(';'):
                    if 'csrf_token=' in cookie:
                        csrf_token = cookie.split('csrf_token=')[1].split(';')[0]
                        print(f"获取到新的CSRF token: {csrf_token[:20]}...")
                        break
            
            # 获取卖家订单列表，传递charm_id参数
            sell_orders = self.get_sell_orders(goods_id, charm_id)
            
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
                order_id = order.get('id')
                
                # 检查价格是否符合条件（价格≤max_price）
                if order_price <= max_price:
                    # 检查订单是否已经尝试过
                    is_order_tried = any(
                        tried.get('order_id') == order_id # 根据 订单ID 检查是否已经尝试过
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
                results.append({
                    'success': False,
                    'message': "未找到符合价格条件的卖家订单"
                })
                return results
            
            print(f"共找到 {len(eligible_orders)} 个符合条件的订单，将尝试购买前 {min(max_orders, len(eligible_orders))} 个")
            
            # 添加必要的头信息
            headers = {
                **self.headers, # 合并基础头信息
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Connection": "keep-alive",
                "Origin": "https://buff.163.com",
                "Referer": f"https://buff.163.com/goods/{goods_id}",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin"
            }
            
            # 如果获取到了CSRF token，添加到请求头
            if csrf_token:
                headers["X-CSRFToken"] = csrf_token
            
            # 尝试购买每个符合条件的订单
            for i, order in enumerate(eligible_orders[:max_orders]):
                sell_order_id = order.get('id')
                order_price = float(order.get('price', '0'))
                
                print(f"\n尝试购买第 {i+1} 个订单: ID={sell_order_id}, 价格={order_price}元")
                
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
                    "cdkey_id": "",
                    "hide_non_epay": True,
                    "pay_method": 1,  # BUFF可用资金
                    "seller_order_id": sell_order_id,
                    "steamid": None,
                    "token": ""
                }
                
                # 发起购买请求，增加429错误处理
                max_retries = 5 # 增加重试次数
                buy_success = False
                for retry in range(max_retries):
                    try:
                        buy_response = self.session.post(buy_url, json=buy_data, headers=headers, timeout=15)
                        
                        # 检查是否返回429错误
                        if buy_response.status_code == 429:
                            print(f"购买请求过于频繁，正在等待并重试 ({retry+1}/{max_retries})...")
                            # 增加等待时间
                            import random
                            time.sleep(random.uniform(5.0, 10.0))
                            continue
                        
                        buy_success = True
                        break
                    except requests.exceptions.Timeout: # 超时异常处理
                        print(f"购买请求超时，正在重试 ({retry+1}/{max_retries})...")
                        if retry == max_retries - 1:
                            raise # 抛出异常，重试次数用完仍失败
                
                if not buy_success:
                    print("购买请求失败，达到最大重试次数")
                    results.append({
                        'success': False,
                        'message': "购买请求失败，达到最大重试次数"
                    })
                    continue  # 继续尝试下一个订单
                
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
                        possible_fields = ['bill_order_id', 'order_id', 'id'] # 'id'就可以
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
                            
                            # 请求卖家发送报价，增加429错误处理
                            max_retries = 5 # 增加重试次数
                            ask_success = False
                            for retry in range(max_retries):
                                try:
                                    ask_seller_response = self.session.post(ask_seller_url, json=ask_seller_data, headers=headers, timeout=15)
                                    
                                    # 检查是否返回429错误
                                    if ask_seller_response.status_code == 429:
                                        print(f"请求卖家发送报价过于频繁，正在等待并重试 ({retry+1}/{max_retries})...")
                                        # 增加等待时间
                                        import random
                                        time.sleep(random.uniform(5.0, 10.0))
                                        continue
                                    
                                    ask_success = True
                                    break
                                except requests.exceptions.Timeout: # 超时异常处理
                                    print(f"请求卖家发送报价超时，正在重试 ({retry+1}/{max_retries})...")
                                    if retry == max_retries - 1:
                                        raise # 抛出异常，重试次数用完仍失败
                            
                            if not ask_success:
                                print("请求卖家发送报价失败，达到最大重试次数")
                            else:
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
    
    def run(self, max_price: float = 0.3, max_pages: int = 25, max_items: int = 5, tried_items=None):
        """运行主流程
        
        Args:
            max_price: 最大价格，默认为0.3元
            max_pages: 最大页数，默认为25页
            max_items: 最大购买数量，默认为5
            tried_items: 已尝试购买的商品记录列表
        """
        print("=== BUFF奥斯汀锦标赛挂件搜枪脚本 ===")
        print(f"游戏: {self.game}")
        print(f"目标: 查找价格 < {max_price}元的带有奥斯汀锦标赛挂件的枪械饰品")
        print(f"最大页数: {max_pages}")
        print(f"最大购买数量: {max_items}")
        print(f"已尝试商品数量: {len(tried_items) if tried_items else 0}")
        
        # 测试登录状态
        if not self.test_login():
            print("请先设置有效的cookie")
            return
        
        # 初始化tried_items
        if tried_items is None:
            tried_items = []
        
        # 获取挂件饰品
        all_charms = []
        page = 1
        consecutive_empty_pages = 0  # 连续空页面计数器
        max_consecutive_empty_pages = 3  # 最大连续空页面数
        
        while page <= max_pages and consecutive_empty_pages < max_consecutive_empty_pages:
            print(f"\n=== 获取第 {page} 页奥斯汀锦标赛挂件饰品 ===")
            items = self.get_charms(page_num=page, page_size=20)
            
            if not items:
                consecutive_empty_pages += 1
                print(f"第 {page} 页未获取到饰品，连续空页面数: {consecutive_empty_pages}")
                if consecutive_empty_pages >= max_consecutive_empty_pages:
                    print(f"连续 {max_consecutive_empty_pages} 页未获取到饰品，停止获取更多页面")
                    break
            else:
                consecutive_empty_pages = 0  # 重置计数器
                all_charms.extend(items)
            
            page += 1
            # 增加页面间延迟以避免429错误
            print(f"页面 {page-1} 处理完成，等待下一页...")
            import random
            time.sleep(random.uniform(1.0, 2.0))
        
        print(f"\n=== 总计获取到 {len(all_charms)} 个奥斯汀锦标赛挂件饰品 ===")
        
        # 实现购买功能
        print(f"\n=== 开始查找并购买符合条件的饰品 ===")
        print(f"最大购买数量: {max_items}")
        
        purchases = []
        purchased_count = 0
        all_cheap_guns = []
        
        # 对每个挂件进行搜枪
        for i, charm in enumerate(all_charms):
            # 检查是否已达到最大购买数量
            if purchased_count >= max_items:
                break
            
            charm_id = charm.get('id')
            charm_name = charm.get('name', '')
            print(f"\n=== 处理第 {i+1} 个挂件: {charm_name} (ID: {charm_id}) ===")
            
            # 从挂件的API响应中提取charm ID
            extracted_charm_id = self.get_charm_id(charm_id)
            print(f"提取到的charm ID: {extracted_charm_id}")
            
            # 检查提取到的charm ID是否有效
            if not extracted_charm_id:
                print(f"无法提取有效的charm ID，跳过处理挂件: {charm_name} (ID: {charm_id})")
                continue
            
            print(f"使用的charm ID: {extracted_charm_id}")
            
            # 获取带有该挂件的枪械饰品
            guns = self.get_guns_with_charm(extracted_charm_id, page_num=1, page_size=20)
            if not guns:
                continue
            
            # 筛选低价枪械饰品
            cheap_guns = self.filter_cheap_guns(guns, max_price)
            all_cheap_guns.extend(cheap_guns)
            
            # 对每个符合条件的枪械饰品立即购买
            for gun in cheap_guns:
                # 检查是否已达到最大购买数量
                if purchased_count >= max_items:
                    break
                
                gun_id = gun['id']
                gun_name = gun['name']
                gun_price = gun['price']
                
                print(f"\n=== 购买第 {purchased_count+1} 个饰品: {gun_name} (ID: {gun_id}) ===")
                print(f"价格: {gun_price}元")
                
                # 尝试购买，传递当前挂件的charm_id
                results = self.buy_item(gun_id, gun_price, charm_id=charm_id, max_price=max_price, max_orders=2, tried_items=tried_items)
                purchases.extend(results)
                
                # 检查是否购买成功
                for result in results:
                    if result.get('success'):
                        purchased_count += 1
                        print(f"购买成功，已购买 {purchased_count} 个饰品")
                        break
                
                # 增加购买间隔以避免429错误
                print("购买完成，等待下一次购买...")
                import random
                time.sleep(random.uniform(5.0, 10.0))
            
            # 增加挂件处理间隔以避免429错误
            print("挂件处理完成，等待下一个挂件...")
            import random
            time.sleep(random.uniform(1.0, 2.0))
        
        # 打印所有符合条件的枪械饰品
        print(f"\n=== 总计找到 {len(all_cheap_guns)} 个价格小于 {max_price} 元的带有奥斯汀锦标赛挂件的枪械饰品 ===")
        if all_cheap_guns:
            print("\n符合条件的饰品列表：")
            for i, gun in enumerate(all_cheap_guns):
                print(f"{i+1}. {gun['name']} - {gun['price']}元")
                print(f"   商品ID: {gun['id']}")
                print(f"   Steam市场链接: {gun.get('steam_market_url', 'N/A')}")
                print("-" * 80)
        else:
            print("未找到符合条件的饰品")
        
        # 打印购买情况
        self.print_purchase_status(purchases)
        
        print("\n=== 脚本运行完成 ===")

import os

def save_cookie(cookie_str, file_path=None):
    """保存cookie到文件"""
    # 使用绝对路径，确保从任何目录运行都能找到文件
    if file_path is None:
        try:
            # 尝试获取脚本所在目录的绝对路径
            script_dir = os.path.dirname(os.path.abspath(__file__))
        except Exception:
            # 如果获取失败，使用当前脚本的绝对路径
            script_dir = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
        file_path = os.path.join(script_dir, "cookie.txt")
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(cookie_str)
        print(f"Cookie已保存到 {file_path}")
    except Exception as e:
        print(f"保存Cookie失败: {e}")

def load_cookie(file_path=None):
    """从文件加载cookie"""
    # 使用绝对路径，确保从任何目录运行都能找到文件
    if file_path is None:
        try:
            # 尝试获取脚本所在目录的绝对路径
            script_dir = os.path.dirname(os.path.abspath(__file__))
        except Exception:
            # 如果获取失败，使用当前脚本的绝对路径
            script_dir = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
        file_path = os.path.join(script_dir, "cookie.txt")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            cookie_str = f.read().strip()
        if cookie_str:
            print(f"从 {file_path} 加载Cookie成功")
            return cookie_str
        return ""
    except FileNotFoundError:
        print(f"{file_path} 文件不存在")
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
        file_path = os.path.join(script_dir, "austin_charm_tried_items.json")
    
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
        file_path = os.path.join(script_dir, "austin_charm_tried_items.json")
    
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
    searcher = BuffCharmSearcherAustin(game="csgo")
    
    print("=== BUFF奥斯汀锦标赛挂件搜枪脚本 ===")
    print("使用说明：")
    print("1. 首次运行需要输入BUFF网站的Cookie")
    print("2. Cookie会自动保存，下次运行时无需再输入")
    print("3. 当Cookie失效时，系统会提示重新输入")
    print("4. 脚本会自动跳过已尝试购买的商品（因为卖家原因无法发送报价，而导致失败）")
    print("-" * 60)
    
    # 尝试加载保存的cookie
    cookie_str = load_cookie()
    
    # 如果没有保存的cookie或cookie无效，要求用户输入
    if not cookie_str or not searcher.set_cookie(cookie_str) or not searcher.test_login():
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
            if searcher.set_cookie(cookie_str) and searcher.test_login():
                # 保存新的cookie
                save_cookie(cookie_str)
                break
            print("登录测试显示Cookie无效或错误，请重新输入Cookie")
            print("-" * 60)
    
    # 加载已尝试商品记录
    tried_items_file = "austin_charm_tried_items.json"
    tried_items = load_tried_items(file_path=tried_items_file)
    
    # 运行脚本，设置最大购买价格为0.3，最大购买数量为5
    searcher.run(max_price=0.3, max_pages=18, max_items=5, tried_items=tried_items)
    
    # 保存已尝试商品记录
    save_tried_items(tried_items, file_path=tried_items_file)