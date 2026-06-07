# BUFF 饰品自动化购买工具集

自动化购买 [BUFF](https://buff.163.com) 低价饰品的工具集，支持多种购买模式。

## 工具一览

| 工具 | 脚本 | 功能 |
|------|------|------|
| 指定饰品购买 | `scripts/item_buyer.py` | 传入 goods_id，按价格阈值购买 |
| 涂鸦饰品购买 | `scripts/buff_buyer.py` | 自动筛选低价涂鸦并购买 |
| 挂件搜枪 | `scripts/buff_charm_searcher.py` | 查找带挂件的低价枪械并购买 |
| 价格仪表盘 | `scripts/dashboard.py` | 本地 Web 监控面板 |

## 安装

```bash
pip install requests

# 仪表盘功能（可选）
pip install flask
```

## Cookie 获取

所有工具共用一个 Cookie，首次运行时会提示输入：

1. 浏览器登录 buff.163.com
2. F12 → 网络 → 刷新页面
3. 复制任意请求的 Cookie 值

Cookie 保存在 `cookie.txt`，后续运行自动加载。失效时会重新提示。

---

## 通用参数

所有工具支持以下通用参数：

| 参数 | 说明 |
|------|------|
| `--dry-run` | 模拟模式，只显示会购买什么，不实际下单 |
| `--verbose` | 详细日志（DEBUG 级别） |
| `--quiet` | 安静模式（仅警告和错误） |

---

## 工具 1：指定饰品购买

传入饰品的 goods_id 或商品页面 URL，自动检查卖单并按价格阈值购买。

### 获取 goods_id

```bash
python scripts/item_buyer.py --search "AK-47"
python scripts/item_buyer.py -s "二西莫夫" --limit 50
python scripts/item_buyer.py -s "AK-47（纪念品） | 灰变迷彩 (久经沙场)"
```

### 使用方式

```bash
# 按 ID 购买
python scripts/item_buyer.py 45678 --max-price 5.0 --max-items 3

# 传入完整 URL
python scripts/item_buyer.py --url https://buff.163.com/goods/45678 --max-price 5.0

# 轮询模式
python scripts/item_buyer.py 45678 --max-price 5.0 --interval 30
python scripts/item_buyer.py 45678 --max-price 5.0 --interval 60 --max-rounds 20

# 批量监控（从文件读取多个商品）
python scripts/item_buyer.py --batch items.txt --interval 30

# 模拟模式（预览不购买）
python scripts/item_buyer.py 45678 --max-price 5.0 --dry-run
```

### 批量监控文件格式

在项目根目录下创建 `items.txt`（文件名随意），每行一个商品：

```
# 格式：goods_id 或 URL  [最高价]
# 最高价可选，不填默认 1.0 元
# 以 # 开头的行为注释，会被跳过

# 按 goods_id，最高价 5 元
45678 5.0

# 按 goods_id，使用默认最高价 1 元
12345

# 按 URL，最高价 10 元
https://buff.163.com/goods/67890 10.0
```

获取 goods_id：先用搜索功能找到饰品，如 `python scripts/item_buyer.py -s "AK-47"`，从结果中复制 goods_id。

运行：
```bash
python scripts/item_buyer.py --batch items.txt --interval 30
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `goods_id` | - | 饰品 ID（与 `--search` 二选一） |
| `--url` | - | 商品页面 URL |
| `--search`, `-s` | - | 按名称搜索饰品 |
| `--limit`, `-l` | 20 | 搜索结果数量 |
| `--max-price` | 1.0 | 最大购买价格（元） |
| `--max-items` | 5 | 单轮最大购买数量 |
| `--interval` | 0 | 轮询间隔（秒），0=单次运行 |
| `--max-rounds` | 0 | 最大轮询次数，0=无限 |
| `--batch` | - | 批量监控文件路径 |
| `--tried-file` | item_purchases.json | 购买记录文件路径 |

### BAT 快速启动

双击 `start_buy.bat`，选择工具后按提示操作。支持所有四种工具。

---

## 工具 2：涂鸦饰品购买

自动筛选 BUFF 上价格 ≤ 0.05 元的涂鸦饰品并批量购买。

```bash
python scripts/buff_buyer.py
python scripts/buff_buyer.py --max-price 0.05 --max-items 10
python scripts/buff_buyer.py --dry-run
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--max-price` | 0.05 | 最大价格（元） |
| `--max-items` | 10 | 最大购买数量 |
| `--game` | csgo | 游戏 |
| `--tried-file` | graffiti_purchases.json | 购买记录文件路径 |

---

## 工具 3：挂件搜枪

遍历指定赛事的所有挂件，查找带有该挂件且价格低于阈值的枪械并购买。

```bash
# 列出可用赛事
python scripts/buff_charm_searcher.py --list-events

# Austin 赛事
python scripts/buff_charm_searcher.py --event austin

# Budapest 赛事，自定义参数
python scripts/buff_charm_searcher.py --event budapest --max-price 0.5 --max-items 20

# 模拟模式
python scripts/buff_charm_searcher.py --event austin --dry-run
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--event` | - | 赛事名称（austin / budapest） |
| `--max-price` | 0.3 | 最大价格（元） |
| `--max-items` | 10 | 最大购买数量 |
| `--max-pages` | 赛事默认 | 最大页数 |
| `--game` | csgo | 游戏 |

### 添加新赛事

在 `buff/config.py` 的 `CHARM_EVENTS` 中添加：

```python
CHARM_EVENTS["new_event"] = CharmEvent(
    name="new_event",
    category="csgo_tool_keychain_new_event_2025",
    default_max_pages=10,
    tried_items_file="charm_new_purchases.json",
)
```

---

## 工具 4：价格监控仪表盘

本地 Web 面板，查看价格走势、购买统计，并可在界面中直接执行所有购买工具。

```bash
pip install flask
python scripts/dashboard.py
# 浏览器打开 http://127.0.0.1:5000
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--port` | 5000 | 端口 |
| `--host` | 127.0.0.1 | 主机 |
| `--db` | buff_data.db | 数据库文件 |

---

## 文件结构

```
Buff/
├── buff/                           # 核心库
│   ├── __init__.py
│   ├── client.py                   # BuffClient 基类（会话、CSRF、购买流程）
│   ├── buyer.py                    # BuffBuyer（涂鸦购买）
│   ├── charm_searcher.py           # BuffCharmSearcher（挂件搜枪）
│   ├── item_buyer.py               # BuffItemBuyer（指定饰品购买）
│   ├── config.py                   # 赛事配置
│   ├── utils.py                    # Cookie / tried_items 持久化
│   ├── log.py                      # 日志配置
│   ├── retry.py                    # 请求重试
│   ├── db.py                       # SQLite 数据层
│   ├── dashboard.py                # Flask 仪表盘
│   └── templates/
│       └── dashboard.html
├── scripts/                        # 入口脚本
│   ├── item_buyer.py               # 指定饰品购买 CLI
│   ├── buff_buyer.py               # 涂鸦购买 CLI
│   ├── buff_charm_searcher.py      # 挂件搜枪 CLI
│   └── dashboard.py                # 仪表盘启动
├── start_buy.bat                   # Windows 快速启动
├── cookie.txt                      # Cookie 存储（自动）
├── .gitignore
├── CLAUDE.md
├── README.md
└── requirements.txt
```

## 数据文件（自动生成）

| 文件 | 说明 |
|------|------|
| `buff_data.db` | SQLite 数据库（价格历史、购买记录） |
| `graffiti_purchases.json` | 涂鸦购买记录 |
| `charm_austin_purchases.json` | Austin 挂件搜枪记录 |
| `charm_budapest_purchases.json` | Budapest 挂件搜枪记录 |
| `item_purchases.json` | 指定饰品购买记录 |
| `cookie.txt` | Cookie 存储 |

## 注意事项

1. **请求频率**：脚本内置随机延迟和重试机制，避免被封禁
2. **购买失败原因**：卖家无法发送报价 / 不支持余额支付 / 余额不足
3. **Cookie 有效期**：过期后会自动提示重新输入
4. **模拟模式**：使用 `--dry-run` 预览会购买什么，不实际下单
5. **使用风险**：自动化脚本可能违反 BUFF 用户协议，请谨慎使用

## 免责声明

本工具仅用于学习和研究目的，使用本工具产生的一切后果由使用者自行承担。
