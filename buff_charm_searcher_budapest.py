"""BUFF挂件搜枪脚本 (Budapest)

功能：
- 遍历 Budapest 挂件类的所有饰品
- 查找带有该挂件的低价枪械饰品
- 自动购买符合条件的饰品
"""

from buff.charm_searcher import BuffCharmSearcher
from buff.config import CHARM_EVENTS
from buff.utils import load_cookie, prompt_cookie, load_tried_items, save_tried_items

if __name__ == "__main__":
    event = CHARM_EVENTS["budapest"]
    searcher = BuffCharmSearcher(game="csgo", event_config=event)

    print("=== BUFF挂件搜枪脚本 (Budapest) ===")
    print(f"目标: 购买带有 Budapest 挂件的价格 <= 0.3 元的枪械")
    print(f"最大购买数量: 10")
    print("-" * 60)

    # Cookie
    cookie_str = load_cookie()
    if not (cookie_str and searcher.set_cookie(cookie_str) and searcher.test_login()):
        prompt_cookie(searcher)

    # 加载已尝试商品记录
    tried_items = load_tried_items(event.tried_items_file)

    # 运行
    searcher.run(max_price=0.3, max_items=10, tried_items=tried_items)

    # 保存
    save_tried_items(tried_items, event.tried_items_file)
