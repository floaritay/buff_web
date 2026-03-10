# CSRF Token 过期问题解决方案说明

## 问题描述

在使用 BUFF 挂件搜枪脚本时，出现了"页面已过期"的错误，具体表现为：
- 脚本初始运行正常
- 隔几天后再次运行时，在购买饰品过程中出现 CSRF token 验证失败
- 错误信息显示为"页面已过期"

## 问题分析

经过分析，问题的根本原因是：

1. **CSRF Token 时效性**：BUFF 网站的 CSRF token 具有一定的时效性，过期后需要重新获取
2. **会话状态管理**：原脚本使用的会话状态可能在长时间运行后失效
3. **token 提取方式单一**：原脚本只从 cookie 中提取 CSRF token，方式不够全面
4. **请求头信息不完整**：缺少一些必要的请求头，导致服务器可能拒绝请求
5. **模拟浏览器行为不足**：没有完全模拟真实用户的浏览行为，容易被服务器识别为机器人

## 解决思路

1. **完全重新初始化会话**：每次购买前重新创建会话，确保获取最新的会话状态
2. **多步骤页面访问**：模拟真实用户的浏览流程，访问主页 → 市场页面 → 商品页面
3. **多种 token 提取方式**：从多个来源提取 CSRF token，提高成功率
4. **完整的请求头信息**：模拟真实浏览器的完整请求头
5. **购买前再次刷新 token**：确保使用最新的 token 进行购买
6. **增加请求间隔**：减少被反爬的风险

## 代码修改详情

### 1. 会话管理优化

- 保存当前 cookie
- 创建新的会话对象
- 恢复 cookie 到新会话
- 模拟完整的页面访问流程

```python
# 完全重新初始化会话，模拟浏览器全新访问
print("重新初始化会话以获取最新的CSRF token...")

# 保存当前cookie
current_cookies = self.session.cookies.get_dict()

# 创建新的会话
new_session = requests.Session()

# 更全面的浏览器头信息
browser_headers = {
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

new_session.headers.update(browser_headers)

# 恢复cookie
for key, value in current_cookies.items():
    new_session.cookies.set(key, value, domain='buff.163.com', path='/')

# 访问主页
print("访问BUFF主页...")
home_response = new_session.get("https://buff.163.com", timeout=15)
time.sleep(1.5)

# 访问市场页面
market_url = f"https://buff.163.com/market/{self.game}"
print(f"访问市场页面: {market_url}")
market_response = new_session.get(market_url, timeout=15)
time.sleep(1.5)

# 访问商品页面
goods_page_url = f"https://buff.163.com/goods/{goods_id}"
print(f"访问商品页面: {goods_page_url}")
goods_response = new_session.get(goods_page_url, timeout=15)
time.sleep(1.5)
```

### 2. 多种 CSRF Token 提取方式

- 从 meta 标签提取
- 从 script 标签提取
- 从 window.csrf_token 提取
- 从 cookie 中提取
- 从表单隐藏字段提取

```python
# 从HTML中提取CSRF token
csrf_token = ""
html_content = goods_response.text

# 尝试多种模式提取CSRF token
import re

# 模式1: 从meta标签提取
meta_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html_content)
if meta_match:
    csrf_token = meta_match.group(1)
    print(f"从meta标签获取到CSRF token: {csrf_token[:20]}...")

# 模式2: 从script标签提取
if not csrf_token:
    script_match = re.search(r'csrf_token\s*=\s*["\']([^"\']+)"\'', html_content)
    if script_match:
        csrf_token = script_match.group(1)
        print(f"从script标签获取到CSRF token: {csrf_token[:20]}...")

# 模式3: 从script标签的另一种格式提取
if not csrf_token:
    script_match2 = re.search(r'window\.csrf_token\s*=\s*["\']([^"\']+)"\'', html_content)
    if script_match2:
        csrf_token = script_match2.group(1)
        print(f"从window.csrf_token获取到CSRF token: {csrf_token[:20]}...")

# 模式4: 从cookie中提取
if not csrf_token:
    for cookie in new_session.cookies:
        if cookie.name == 'csrf_token':
            csrf_token = cookie.value
            print(f"从cookie获取到CSRF token: {csrf_token[:20]}...")
            break

# 模式5: 从HTML中的表单隐藏字段提取
if not csrf_token:
    form_match = re.search(r'<input[^>]+name="csrfmiddlewaretoken"[^>]+value="([^"]+)"', html_content)
    if form_match:
        csrf_token = form_match.group(1)
        print(f"从表单隐藏字段获取到CSRF token: {csrf_token[:20]}...")

if not csrf_token:
    print("警告: 未能获取CSRF token")
    # 打印HTML的前1000字符，便于调试
    print("页面HTML前1000字符:")
    print(html_content[:1000])
```

### 3. 使用新会话获取卖家订单

- 使用新创建的会话获取卖家订单列表
- 确保订单列表的获取也使用最新的会话状态

```python
# 获取卖家订单列表，传递charm_id参数
# 注意：使用新会话获取订单列表
print("获取卖家订单列表...")
sell_order_url = "https://buff.163.com/api/market/goods/sell_order"
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

# 添加CSRF token到请求头
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
```

### 4. 购买前再次刷新 Token

- 在发起购买请求前，再次访问商品页面
- 提取最新的 CSRF token
- 确保使用最新的 token 进行购买

```python
# 再次访问商品页面，确保获取最新的token
print("再次访问商品页面以确保token新鲜...")
goods_response = new_session.get(goods_page_url, timeout=15)
time.sleep(1)

# 再次提取CSRF token
fresh_csrf_token = csrf_token
html_content = goods_response.text
meta_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', html_content)
if meta_match:
    fresh_csrf_token = meta_match.group(1)
    print(f"获取到新鲜的CSRF token: {fresh_csrf_token[:20]}...")

if fresh_csrf_token:
    headers["X-CSRFToken"] = fresh_csrf_token
    headers["X-CSRF-Token"] = fresh_csrf_token
    headers["Csrf-Token"] = fresh_csrf_token
```

### 5. 增强的请求头信息

- 添加更多的 CSRF 相关头信息
- 确保请求头的完整性

```python
# 添加必要的头信息
headers = {
    **browser_headers,
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
    "Origin": "https://buff.163.com",
    "Referer": goods_page_url,
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

# 如果获取到了CSRF token，添加到请求头
if csrf_token:
    headers["X-CSRFToken"] = csrf_token
    headers["X-CSRF-Token"] = csrf_token
    headers["Csrf-Token"] = csrf_token
```

### 6. 增加请求间隔

- 增加页面访问之间的间隔
- 增加购买操作之间的间隔
- 减少被反爬的风险

```python
# 页面访问间隔
time.sleep(1.5)

# 购买间隔
time.sleep(4)
```

## 验证结果

修改后，脚本成功执行购买操作，不再出现"页面已过期"的错误：

```
=== 购买第 1 个饰品: MP7（纪念品） | 掠夺者 (略有磨损) (ID: 877145) ===
价格: 0.35元
尝试购买饰品 ID: 877145, 目标价格: 0.35元
重新初始化会话以获取最新的CSRF token...
访问BUFF主页...
访问市场页面: https://buff.163.com/market/csgo
访问商品页面: https://buff.163.com/goods/877145
从cookie获取到CSRF token: IjI1N2E1ODhiNTQ4Y2U2...
获取卖家订单列表...
添加charm参数: 138685
获取到 4 个卖家订单
找到符合条件的订单: ID=3977408067-ADA4-153990517, 价格=0.35元
共找到 1 个符合条件的订单，将尝试购买前 1 个

尝试购买第 1 个订单: ID=3977408067-ADA4-153990517, 价格=0.35元
订单ID类型: <class 'str'>
再次访问商品页面以确保token新鲜...
发起购买请求...
购买请求状态码: 200
购买请求响应: {"code":"OK","data":{"appid":730,"asset_info":{"action_link":"/api/market/cs2_inspect/?assetid=50158249063","appid":730,"assetid":"50158249063","classid":"7993035632","contextid":2,"goods_id":877145,"...
购买成功
请求卖家发送报价...
从id字段获取到订单号: 260310T3637750466
请求卖家发送报价状态码: 200
请求卖家发送报价响应: {"code":"OK","data":{"260310T3637750466":"OK"},"msg":null}
请求卖家发送报价成功
购买成功，已购买 1 个饰品
```

## 结论

通过以上修改，成功解决了 CSRF token 过期的问题。核心改进是：

1. **完全重新初始化会话**：确保每次购买都使用最新的会话状态
2. **模拟完整的浏览器行为**：访问多个页面，模拟真实用户的浏览流程
3. **多种 token 提取方式**：提高 CSRF token 获取的成功率
4. **购买前刷新 token**：确保使用最新的 token 进行购买
5. **完整的请求头信息**：模拟真实浏览器的请求
6. **合理的请求间隔**：减少被反爬的风险

这些改进不仅解决了当前的问题，也提高了脚本的稳定性和可靠性，使其能够长期正常运行。