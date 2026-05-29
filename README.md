# BUFF 饰品自动化购买工具集

自动化购买 [BUFF](https://buff.163.com) 低价饰品的工具集，支持三种购买模式。

## 工具一览

| 工具 | 脚本 | 功能 |
|------|------|------|
| 指定饰品购买 | `item_buyer.py` | 传入 goods_id，按价格阈值购买 |
| 涂鸦饰品购买 | `buff_buyer.py` | 自动筛选低价涂鸦并购买 |
| 挂件搜枪 (Austin) | `buff_charm_searcher_austin.py` | 查找带 Austin 挂件的低价枪械并购买 |
| 挂件搜枪 (Budapest) | `buff_charm_searcher_budapest.py` | 查找带 Budapest 挂件的低价枪械并购买 |

## 安装

```bash
pip install requests
```

## Cookie 获取

所有工具共用一个 Cookie，首次运行时会提示输入：

1. 浏览器登录 buff.163.com
2. F12 → 网络 → 刷新页面
3. 复制任意请求的 Cookie 值

Cookie 保存在 `cookie.txt`，后续运行自动加载。失效时会重新提示。

---

## 工具 1：指定饰品购买

传入饰品的 goods_id 或商品页面 URL，自动检查卖单并按价格阈值购买。支持所有饰品类型（枪械、贴纸、印花、纪念品等）。

### 获取 goods_id

**方式 1：搜索（推荐）**

```bash
python item_buyer.py --search "AK-47"
python item_buyer.py -s "二西莫夫"
python item_buyer.py -s "二西莫夫 | AK-47"
python item_buyer.py -s "AK-47" --limit 50   # 返回 50 个搜索结果
python item_buyer.py -s "AK-47" -l 5         # 返回 5 个搜索结果
```

会返回匹配的饰品列表，包含 goods_id、最低价、在售数量。

**方式 2：从网站复制**

打开饰品详情页，地址栏中的数字即为 goods_id：

```
https://buff.163.com/goods/12345  →  goods_id = 12345
```

### 使用方式

```bash
# 搜索饰品（默认返回 20 个结果）
python item_buyer.py --search "AK-47"
python item_buyer.py -s "二西莫夫"

# 搜索更多结果
python item_buyer.py -s "AK-47" --limit 50

# 按 ID 购买
python item_buyer.py 45678 --max-price 5.0 --max-items 3

# 传入完整 URL
python item_buyer.py --url https://buff.163.com/goods/45678 --max-price 5.0

# 轮询模式：每 30 秒检查一次，无限循环
python item_buyer.py 45678 --max-price 5.0 --interval 30

# 轮询模式：每 60 秒检查一次，最多 20 轮
python item_buyer.py 45678 --max-price 5.0 --interval 60 --max-rounds 20
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `goods_id` | - | 饰品 ID（与 `--search` 二选一） |
| `--url` | - | 商品页面 URL |
| `--search`, `-s` | - | 按名称搜索饰品，获取 goods_id |
| `--limit`, `-l` | 20 | 搜索结果数量 |
| `--max-price` | 1.0 | 最大购买价格（元） |
| `--max-items` | 5 | 单轮最大购买数量 |
| `--interval` | 0 | 轮询间隔（秒），0=单次运行 |
| `--max-rounds` | 0 | 最大轮询次数，0=无限 |
| `--tried-file` | item_tried_items.json | 购买记录文件路径 |

### BAT 快速启动

双击 `start_buy.bat`，按提示输入参数即可。支持选择单次运行或轮询模式。

---

## 工具 2：涂鸦饰品购买

自动筛选 BUFF 上价格 ≤ 0.05 元的涂鸦饰品并批量购买。

```bash
python buff_buyer.py
```

脚本会自动：
- 筛选涂鸦类饰品（按分类和关键词过滤）
- 查找价格 ≤ 0.05 元的涂鸦
- 逐个购买，每个最多尝试 5 个卖单
- 购买后自动请求卖家发送 Steam 报价
- 修改价格和最大数量需要在文件最后手动修改
---

## 工具 3：挂件搜枪

遍历指定赛事的所有挂件，对每个挂件执行"挂件搜枪"，查找带有该挂件且价格低于阈值的枪械并购买。

```bash
# Austin 赛事挂件
python buff_charm_searcher_austin.py

# Budapest 赛事挂件
python buff_charm_searcher_budapest.py
```

脚本会自动：
- 遍历所有挂件（Austin 18 页，Budapest 15 页）
- 提取每个挂件的 custom_charm_id
- 搜索带有该挂件的在售枪械
- 筛选价格 < 0.3 元的枪械并购买
- 修改价格和最大数量需要在文件最后手动修改

### 添加新赛事

在 `buff/config.py` 的 `CHARM_EVENTS` 中添加新条目：

```python
CHARM_EVENTS["new_event"] = CharmEvent(
    name="new_event",
    category="csgo_tool_keychain_new_event_2025",
    default_max_pages=10,
    tried_items_file="charm_tried_items_new.json",
)
```

---

## 文件结构

```
Buff/
├── buff/                           # 核心库
│   ├── __init__.py                 # 包导出
│   ├── client.py                   # BuffClient 基类（会话、CSRF、购买流程）
│   ├── buyer.py                    # BuffBuyer（涂鸦购买）
│   ├── charm_searcher.py           # BuffCharmSearcher（挂件搜枪）
│   ├── item_buyer.py               # BuffItemBuyer（指定饰品购买）
│   ├── config.py                   # 赛事配置
│   └── utils.py                    # Cookie / tried_items 持久化
├── item_buyer.py                   # 指定饰品购买 CLI
├── buff_buyer.py                   # 涂鸦购买 CLI
├── buff_charm_searcher_austin.py   # Austin 挂件搜枪 CLI
├── buff_charm_searcher_budapest.py # Budapest 挂件搜枪 CLI
├── start_buy.bat                   # Windows 快速启动
├── cookie.txt                      # Cookie 存储（自动）
├── .env                            # 环境变量（可选）
└── requirements.txt                # 依赖
```

## 数据文件（自动生成）

| 文件 | 说明 |
|------|------|
| `tried_items.json` | 涂鸦购买记录 |
| `charm_tried_items.json` | Austin 挂件搜枪记录 |
| `charm_tried_items_budapest.json` | Budapest 挂件搜枪记录 |
| `item_tried_items.json` | 指定饰品购买记录 |
| `cookie.txt` | Cookie 存储 |

## 注意事项

1. **请求频率**：脚本内置随机延迟和重试机制，避免被封禁
2. **购买失败原因**：卖家无法发送报价 / 不支持余额支付 / 余额不足
3. **Cookie 有效期**：过期后会自动提示重新输入
4. **使用风险**：自动化脚本可能违反 BUFF 用户协议，请谨慎使用

## 免责声明

本工具仅用于学习和研究目的，使用本工具产生的一切后果由使用者自行承担。
