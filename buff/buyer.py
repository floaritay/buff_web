"""BuffBuyer - 涂鸦饰品自动购买类"""

import json
import random
import time
from typing import Dict, List

import requests

from buff.client import BuffClient
from buff.log import logger


class BuffBuyer(BuffClient):
    """BUFF 涂鸦饰品购买类"""

    GRAFFITI_KEYWORDS = ["涂鸦", "spray", "Graffiti", "喷漆"]

    def get_graffiti(self, page_num: int = 1, page_size: int = 20) -> List[Dict]:
        """获取涂鸦类饰品"""
        try:
            url = f"{self.BASE_URL}/api/market/goods"
            params_list = [
                {"game": self.game, "page_num": page_num, "page_size": page_size,
                 "category": "csgo_type_spray", "sort_by": "price.asc"},
                {"game": self.game, "page_num": page_num, "page_size": page_size,
                 "category_group": "spray", "sort_by": "price.asc"},
                {"game": self.game, "page_num": page_num, "page_size": page_size,
                 "category": "spray", "sort_by": "price.asc"},
            ]

            for params in params_list:
                time.sleep(random.uniform(0.5, 1.5))

                try:
                    resp = self._api_request("GET", url, params=params, timeout=20)
                except requests.exceptions.Timeout:
                    logger.warning("获取涂鸦超时")
                    continue

                logger.debug("请求 %s, 状态 %d", resp.url, resp.status_code)

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == "OK":
                        items = data.get("data", {}).get("items", [])
                        if items:
                            first_name = items[0].get("name", "")
                            if any(kw in first_name for kw in self.GRAFFITI_KEYWORDS):
                                logger.info("获取到 %d 个涂鸦饰品", len(items))
                                return items
                            logger.debug("不是涂鸦饰品，尝试下一种参数")
                    else:
                        logger.warning("API 错误: %s", data.get("code"))
                else:
                    logger.warning("请求失败 HTTP %d", resp.status_code)

            logger.warning("所有参数组合都失败")
            return []
        except Exception as e:
            logger.error("获取涂鸦异常: %s", e)
            return []

    def filter_cheap_items(self, items: List[Dict], max_price: float = 0.05) -> List[Dict]:
        """筛选价格 <= max_price 的涂鸦饰品"""
        cheap = []
        for item in items:
            name = item.get("name", "")
            if not any(kw in name for kw in self.GRAFFITI_KEYWORDS):
                continue
            try:
                price = float(item.get("sell_min_price", item.get("price", "0")))
                if 0 < price <= max_price:
                    cheap.append({
                        "id": item.get("id"),
                        "name": name,
                        "price": price,
                        "sell_num": item.get("sell_num", 0),
                        "goods_id": item.get("id"),
                        "steam_market_url": item.get("steam_market_url", ""),
                    })
                    logger.info("符合条件: %s - %.2f 元", name, price)
            except (ValueError, TypeError) as e:
                logger.debug("处理价格失败: %s", e)

        logger.info("筛选出 %d 个 <= %.2f 元的涂鸦", len(cheap), max_price)
        return cheap

    def run(self, max_price: float = 0.05, max_items: int = 10, tried_items=None):
        """运行主流程"""
        if tried_items is None:
            tried_items = []

        logger.info("=== BUFF 涂鸦饰品购买 ===")
        logger.info("游戏: %s | 最高价: %.2f 元 | 最大量: %d | 已尝试: %d",
                     self.game, max_price, max_items, len(tried_items))

        if not self.test_login():
            logger.error("请先设置有效的 cookie")
            return

        all_items = []
        page = 1
        while len(all_items) < max_items * 2:
            items = self.get_graffiti(page_num=page, page_size=20)
            if not items:
                break
            all_items.extend(items)
            page += 1
            time.sleep(1)

        cheap_items = self.filter_cheap_items(all_items, max_price)
        if not cheap_items:
            logger.info("没有找到符合条件的饰品")
            return

        logger.info("找到 %d 个商品，准备购买", len(cheap_items))

        purchases = []
        for item in cheap_items[:max_items]:
            logger.info("准备购买: %s - %.2f 元", item["name"], item["price"])
            results = self.buy_item(
                item["goods_id"],
                max_price=max_price,
                max_orders=5,
                tried_items=tried_items,
            )
            purchases.extend(results)
            time.sleep(2)

        self.print_purchase_status(purchases)
        logger.info("=== 脚本运行完成 ===")
