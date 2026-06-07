"""BUFF 指定饰品自动购买脚本

用法：
    python scripts/item_buyer.py --search "AK-47"
    python scripts/item_buyer.py 12345 --max-price 5.0 --max-items 3
    python scripts/item_buyer.py --url https://buff.163.com/goods/12345 --max-price 5.0
    python scripts/item_buyer.py 12345 --max-price 5.0 --interval 30
    python scripts/item_buyer.py --batch items.txt --interval 30
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buff.item_buyer import BuffItemBuyer, parse_goods_id
from buff.utils import load_cookie, prompt_cookie, save_tried_items, load_tried_items
from buff.log import logger

TRIED_ITEMS_FILE = "item_purchases.json"


def do_search(buyer: BuffItemBuyer, keyword: str, limit: int = 20):
    """搜索饰品并打印结果"""
    logger.info("搜索: %s", keyword)
    logger.info("提示: 输入完整名称可精确匹配，如 \"AK-47（纪念品） | 灰变迷彩 (久经沙场)\"")
    logger.info("-" * 60)
    items = buyer.search_items(keyword, page_size=limit)
    if not items:
        logger.info("未找到匹配的饰品")
        return

    logger.info("找到 %d 个结果:", len(items))
    print(f"\n{'序号':<4} {'goods_id':<10} {'最低价':>8} {'在售数':>6}  名称")
    print("-" * 70)
    for i, item in enumerate(items, 1):
        gid = item.get("id", "")
        name = item.get("name", "")
        price = item.get("sell_min_price", "-")
        sell_num = item.get("sell_num", 0)
        print(f"{i:<4} {gid:<10} {price:>8} {sell_num:>6}  {name}")

    print(f"\n复制 goods_id，用以下命令购买:")
    print(f"  python scripts/item_buyer.py {items[0].get('id', 'xxx')} --max-price 5.0")


def parse_batch_file(file_path: str) -> list:
    """解析批量监控文件

    格式：每行一个商品，支持 goods_id 或 URL，可选 max_price
    # 45678 5.0
    # 12345 3.0
    # https://buff.163.com/goods/67890 10.0
    """
    items = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            try:
                goods_id = parse_goods_id(parts[0])
            except SystemExit:
                logger.warning("批量文件第 %d 行格式错误，跳过: %s", line_num, parts[0])
                continue
            max_price = float(parts[1]) if len(parts) > 1 else 1.0
            items.append({"goods_id": goods_id, "max_price": max_price})
            logger.debug("批量文件第 %d 行: %s (最高价 %.2f)", line_num, goods_id, max_price)
    return items


def main():
    parser = argparse.ArgumentParser(
        description="BUFF 指定饰品自动购买脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
        "  python scripts/item_buyer.py --search \"AK-47\"\n"
        "  python scripts/item_buyer.py --search \"AK-47（纪念品） | 灰变迷彩 (久经沙场)\"\n"
        "  python scripts/item_buyer.py 45678 --max-price 5.0\n"
        "  python scripts/item_buyer.py --batch items.txt --interval 30\n",
    )
    parser.add_argument("goods_id", nargs="?", help="饰品的 goods_id")
    parser.add_argument("--url", help="商品页面 URL")
    parser.add_argument("--search", "-s", metavar="KEYWORD",
                        help="按名称搜索饰品，支持完整名称如 \"AK-47（纪念品） | 灰变迷彩 (久经沙场)\"")
    parser.add_argument("--limit", "-l", type=int, default=20, help="搜索结果数量，默认 20")
    parser.add_argument("--max-price", type=float, default=1.0, help="最大购买价格（元），默认 1.0")
    parser.add_argument("--max-items", type=int, default=5, help="最大购买数量，默认 5")
    parser.add_argument("--interval", type=int, default=0, help="轮询间隔（秒），0=单次")
    parser.add_argument("--max-rounds", type=int, default=0, help="最大轮询次数，0=无限")
    parser.add_argument("--batch", metavar="FILE", help="批量监控文件（每行一个 goods_id）")
    parser.add_argument("--tried-file", default=TRIED_ITEMS_FILE, help="尝试记录文件路径")
    parser.add_argument("--dry-run", action="store_true", help="模拟模式，不实际购买")
    parser.add_argument("--verbose", action="store_true", help="详细日志")
    parser.add_argument("--quiet", action="store_true", help="安静模式")
    args = parser.parse_args()

    buyer = BuffItemBuyer(game="csgo", verbose=args.verbose, quiet=args.quiet)
    buyer.dry_run = args.dry_run
    buyer.validate_login_or_prompt()

    tried_items = load_tried_items(args.tried_file)

    # 批量模式
    if args.batch:
        items = parse_batch_file(args.batch)
        if not items:
            logger.error("批量文件为空或格式错误")
            sys.exit(1)
        logger.info("批量监控 %d 个商品", len(items))
        buyer.run_batch(
            items=items,
            interval=args.interval or 30,
            max_rounds=args.max_rounds,
            tried_items=tried_items,
        )
        save_tried_items(tried_items, args.tried_file)
        return

    # 搜索模式
    if args.search:
        do_search(buyer, args.search, args.limit)
        return

    # 购买模式
    goods_id = None
    if args.url:
        goods_id = parse_goods_id(args.url)
    elif args.goods_id:
        goods_id = parse_goods_id(args.goods_id)
    else:
        parser.error("请提供 goods_id、--url、--search 或 --batch")

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
