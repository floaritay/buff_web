"""涂鸦饰品自动购买脚本

功能：
- 自动筛选涂鸦类饰品
- 查找价格≤5分钱的饰品
- 使用BUFF可用资金购买
- 购买后请求卖家发送报价
"""

from buff.buyer import BuffBuyer
from buff.utils import load_cookie, prompt_cookie, load_tried_items, save_tried_items

TRIED_ITEMS_FILE = "tried_items.json"

if __name__ == "__main__":
    buyer = BuffBuyer(game="csgo")

    print("=== BUFF涂鸦饰品购买脚本 ===")
    print(f"目标: 购买价格 <= 0.05 元的涂鸦饰品")
    print(f"最大购买数量: 10")
    print("-" * 60)

    # Cookie
    cookie_str = load_cookie()
    if not (cookie_str and buyer.set_cookie(cookie_str) and buyer.test_login()):
        prompt_cookie(buyer)

    # 加载已尝试商品记录
    tried_items = load_tried_items(TRIED_ITEMS_FILE)

    # 运行
    buyer.run(max_price=0.05, max_items=10, tried_items=tried_items)

    # 保存
    save_tried_items(tried_items, TRIED_ITEMS_FILE)
