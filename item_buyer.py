"""BUFF 指定饰品自动购买脚本

功能：
- 按名称搜索饰品，获取 goods_id
- 传入 goods_id 或商品页面 URL，自动获取该饰品的卖单列表
- 按价格阈值筛选卖单并自动购买
- 支持单次运行和轮询监控模式
- 购买后自动请求卖家发送 Steam 交易报价
- 记录已尝试的订单，避免重复购买

使用方式：
    python item_buyer.py --search "AK-47 | 二西莫夫"
    python item_buyer.py 12345 --max-price 5.0 --max-items 3
    python item_buyer.py https://buff.163.com/goods/12345 --max-price 5.0
    python item_buyer.py 12345 --max-price 5.0 --interval 30
"""

import argparse
import time

from buff.item_buyer import BuffItemBuyer, parse_goods_id
from buff.utils import load_cookie, prompt_cookie, save_tried_items, load_tried_items

TRIED_ITEMS_FILE = "item_tried_items.json"


def do_search(buyer: BuffItemBuyer, keyword: str, limit: int = 20):
    """搜索饰品并打印结果"""
    print(f"\n搜索: {keyword}")
    print("-" * 60)
    items = buyer.search_items(keyword, page_size=limit)
    if not items:
        print("未找到匹配的饰品")
        return

    print(f"找到 {len(items)} 个结果:\n")
    print(f"{'序号':<4} {'goods_id':<10} {'最低价':>8} {'在售数':>6}  名称")
    print("-" * 70)
    for i, item in enumerate(items, 1):
        gid = item.get("id", "")
        name = item.get("name", "")
        price = item.get("sell_min_price", "-")
        sell_num = item.get("sell_num", 0)
        print(f"{i:<4} {gid:<10} {price:>8} {sell_num:>6}  {name}")

    print(f"\n复制上方 goods_id 或 URL，用以下命令购买:")
    print(f"  python item_buyer.py {items[0].get('id', 'xxx')} --max-price 5.0")


def main():
    parser = argparse.ArgumentParser(
        description="BUFF 指定饰品自动购买脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
        "  python item_buyer.py --search \"AK-47\"              # 按名称搜索\n"
        "  python item_buyer.py 45678 --max-price 5.0           # 按 ID 购买\n"
        "  python item_buyer.py --url https://buff.163.com/goods/45678\n"
        "  python item_buyer.py 45678 --max-price 5.0 --interval 30",
    )
    parser.add_argument("goods_id", nargs="?", help="饰品的 goods_id（与 --search 二选一）")
    parser.add_argument("--url", help="商品页面 URL")
    parser.add_argument("--search", "-s", metavar="KEYWORD", help="按名称搜索饰品，获取 goods_id")
    parser.add_argument("--limit", "-l", type=int, default=20, help="搜索结果数量，默认 20")
    parser.add_argument("--max-price", type=float, default=1.0, help="最大购买价格（元），默认 1.0")
    parser.add_argument("--max-items", type=int, default=5, help="最大购买数量，默认 5")
    parser.add_argument("--interval", type=int, default=0, help="轮询间隔（秒），不传则单次运行")
    parser.add_argument("--max-rounds", type=int, default=0, help="最大轮询次数，0=无限，默认 0")
    parser.add_argument("--tried-file", default=TRIED_ITEMS_FILE, help="尝试记录文件路径")
    args = parser.parse_args()

    buyer = BuffItemBuyer(game="csgo")

    # Cookie
    cookie_str = load_cookie()
    if not (cookie_str and buyer.set_cookie(cookie_str) and buyer.test_login()):
        prompt_cookie(buyer)

    # 搜索模式
    if args.search:
        do_search(buyer, args.search, args.limit)
        return

    # 购买模式：确定 goods_id
    goods_id = None
    if args.url:
        goods_id = parse_goods_id(args.url)
    elif args.goods_id:
        goods_id = parse_goods_id(args.goods_id)
    else:
        parser.error("请提供 goods_id、--url 或 --search")

    # Tried items
    tried_items = load_tried_items(args.tried_file)

    # 运行
    if args.interval > 0:
        buyer.run_polling(
            goods_id=goods_id,
            max_price=args.max_price,
            max_items=args.max_items,
            interval=args.interval,
            max_rounds=args.max_rounds,
            tried_items=tried_items,
        )
    else:
        buyer.run(
            goods_id=goods_id,
            max_price=args.max_price,
            max_items=args.max_items,
            tried_items=tried_items,
        )

    save_tried_items(tried_items, args.tried_file)


if __name__ == "__main__":
    main()
