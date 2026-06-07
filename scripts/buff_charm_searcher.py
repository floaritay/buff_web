"""BUFF 挂件搜枪统一脚本

用法：
    python scripts/buff_charm_searcher.py --event austin
    python scripts/buff_charm_searcher.py --event budapest --max-price 0.5 --max-items 20
    python scripts/buff_charm_searcher.py --event austin --dry-run
    python scripts/buff_charm_searcher.py --list-events
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buff.charm_searcher import BuffCharmSearcher
from buff.config import CHARM_EVENTS
from buff.utils import load_cookie, prompt_cookie, load_tried_items, save_tried_items
from buff.log import logger


def main():
    parser = argparse.ArgumentParser(description="BUFF 挂件搜枪自动购买")
    parser.add_argument("--event", choices=list(CHARM_EVENTS.keys()), help="赛事名称")
    parser.add_argument("--list-events", action="store_true", help="列出所有可用赛事")
    parser.add_argument("--max-price", type=float, default=0.3, help="最大价格（元），默认 0.3")
    parser.add_argument("--max-items", type=int, default=10, help="最大购买数量，默认 10")
    parser.add_argument("--max-pages", type=int, default=None, help="最大页数（默认使用赛事配置）")
    parser.add_argument("--game", default="csgo", help="游戏，默认 csgo")
    parser.add_argument("--dry-run", action="store_true", help="模拟模式")
    parser.add_argument("--verbose", action="store_true", help="详细日志")
    parser.add_argument("--quiet", action="store_true", help="安静模式")
    args = parser.parse_args()

    if args.list_events:
        print("可用赛事:")
        for name, event in CHARM_EVENTS.items():
            print(f"  {name}: {event.category} (最大 {event.default_max_pages} 页)")
        return

    if not args.event:
        parser.error("请指定 --event 或 --list-events")

    event = CHARM_EVENTS[args.event]
    searcher = BuffCharmSearcher(game=args.game, event_config=event, verbose=args.verbose, quiet=args.quiet)
    searcher.dry_run = args.dry_run
    searcher.validate_login_or_prompt()

    tried_items = load_tried_items(event.tried_items_file)

    searcher.run(
        max_price=args.max_price,
        max_pages=args.max_pages,
        max_items=args.max_items,
        tried_items=tried_items,
    )

    save_tried_items(tried_items, event.tried_items_file)


if __name__ == "__main__":
    main()
