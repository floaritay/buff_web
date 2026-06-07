"""涂鸦饰品自动购买脚本

用法：
    python scripts/buff_buyer.py
    python scripts/buff_buyer.py --max-price 0.05 --max-items 10
    python scripts/buff_buyer.py --dry-run
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buff.buyer import BuffBuyer
from buff.utils import load_cookie, prompt_cookie, load_tried_items, save_tried_items
from buff.log import logger

TRIED_ITEMS_FILE = "graffiti_purchases.json"


def main():
    parser = argparse.ArgumentParser(description="BUFF 涂鸦饰品自动购买")
    parser.add_argument("--max-price", type=float, default=0.05, help="最大价格（元），默认 0.05")
    parser.add_argument("--max-items", type=int, default=10, help="最大购买数量，默认 10")
    parser.add_argument("--game", default="csgo", help="游戏，默认 csgo")
    parser.add_argument("--tried-file", default=TRIED_ITEMS_FILE, help="尝试记录文件")
    parser.add_argument("--dry-run", action="store_true", help="模拟模式")
    parser.add_argument("--verbose", action="store_true", help="详细日志")
    parser.add_argument("--quiet", action="store_true", help="安静模式")
    args = parser.parse_args()

    buyer = BuffBuyer(game=args.game, verbose=args.verbose, quiet=args.quiet)
    buyer.dry_run = args.dry_run
    buyer.validate_login_or_prompt()

    tried_items = load_tried_items(args.tried_file)

    buyer.run(max_price=args.max_price, max_items=args.max_items, tried_items=tried_items)

    save_tried_items(tried_items, args.tried_file)


if __name__ == "__main__":
    main()
