"""BuffCharmSearcher - 挂件搜枪自动购买类"""

import json
import random
import re
import time
from typing import Dict, List

import requests

from buff.client import BuffClient
from buff.config import CharmEvent
from buff.log import logger


class BuffCharmSearcher(BuffClient):
    """BUFF 挂件搜枪类

    通过 event_config 参数区分不同赛事（Austin / Budapest 等）。
    """

    CHARM_KEYWORDS = ["挂件", "keychain", "charm"]

    def __init__(self, game: str = "csgo", event_config: CharmEvent = None, **kwargs):
        super().__init__(game, **kwargs)
        if event_config is None:
            raise ValueError("event_config 不能为空，请传入 CharmEvent 配置")
        self.event_config = event_config

    def get_charms(self, page_num: int = 1, page_size: int = 20) -> List[Dict]:
        """获取挂件类饰品"""
        try:
            url = f"{self.BASE_URL}/api/market/goods"
            params = {
                "game": self.game,
                "page_num": page_num,
                "page_size": page_size,
                "category": self.event_config.category,
                "sort_by": "price.asc",
            }

            time.sleep(random.uniform(0.5, 1.5))

            try:
                resp = self._api_request("GET", url, params=params, timeout=20)
            except requests.exceptions.Timeout:
                logger.warning("获取挂件超时")
                return []

            logger.debug("请求 %s, 状态 %d", resp.url, resp.status_code)

            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "OK":
                    items = data.get("data", {}).get("items", [])
                    if items:
                        first_name = items[0].get("name", "")
                        if any(kw in first_name for kw in self.CHARM_KEYWORDS):
                            logger.info("获取到 %d 个挂件饰品", len(items))
                            return items
                        logger.warning("获取到的不是挂件饰品")
                    else:
                        logger.info("未获取到饰品")
                else:
                    logger.warning("API 错误: %s", data.get("code"))
            else:
                logger.warning("请求失败 HTTP %d", resp.status_code)

            return []
        except Exception as e:
            logger.error("获取挂件异常: %s", e)
            return []

    def get_custom_charm_id(self, goods_id: str) -> str:
        """从页面中提取 custom_charm ID"""
        try:
            url = f"{self.BASE_URL}/goods/{goods_id}"
            time.sleep(random.uniform(0.5, 1.5))

            try:
                resp = self._api_request("GET", url, timeout=20)
            except requests.exceptions.Timeout:
                logger.warning("获取挂件页面超时")
                return ""

            if resp.status_code != 200:
                logger.warning("请求失败 HTTP %d", resp.status_code)
                return ""

            html = resp.text

            # 按优先级尝试多种模式
            patterns = [
                (r'挂件搜枪[^<]+href=["\']([^"\']+)"', "挂件搜枪链接"),
                (r'custom_charm=(\d+)', "custom_charm 参数"),
                (r'"charm"\s*:\s*\{[^}]*"id"\s*:\s*(\d+)', "JS charm 对象"),
                (r'charm_id\s*=\s*(\d+)', "JS charm_id 变量"),
                (r'charm\s*:\s*(\d+)', "JS charm 简写"),
            ]

            for pattern, source in patterns:
                m = re.search(pattern, html)
                if m:
                    val = m.group(1)
                    # 链接模式需要再提取 custom_charm 参数
                    if source == "挂件搜枪链接":
                        cm = re.search(r'custom_charm=(\d+)', val)
                        if cm:
                            logger.debug("从%s提取 custom_charm ID: %s", source, cm.group(1))
                            return cm.group(1)
                    else:
                        logger.debug("从%s提取 custom_charm ID: %s", source, val)
                        return val

            logger.warning("未找到 custom_charm ID (goods_id=%s)", goods_id)
            return ""
        except Exception as e:
            logger.error("提取 custom_charm ID 异常: %s", e)
            return ""

    def get_guns_with_charm(self, custom_charm_id: str, page_num: int = 1, page_size: int = 50) -> List[Dict]:
        """获取带有特定挂件的枪械饰品"""
        try:
            url = f"{self.BASE_URL}/api/market/goods"
            params = {
                "game": self.game,
                "page_num": page_num,
                "page_size": page_size,
                "charm": custom_charm_id,
                "sort_by": "price.asc",
                "tab": "selling",
            }

            time.sleep(random.uniform(1.5, 3.0))

            try:
                resp = self._api_request("GET", url, params=params, timeout=20)
            except requests.exceptions.Timeout:
                logger.warning("获取带挂件枪械超时")
                return []

            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "OK":
                    items = data.get("data", {}).get("items", [])
                    if items:
                        logger.info("获取到 %d 个带挂件枪械 (charm=%s)", len(items), custom_charm_id)
                        return items
                    logger.debug("未获取到饰品 (charm=%s)", custom_charm_id)
                else:
                    logger.warning("API 错误: %s", data.get("code"))
            else:
                logger.warning("请求失败 HTTP %d", resp.status_code)

            return []
        except Exception as e:
            logger.error("获取枪械异常: %s", e)
            return []

    def filter_cheap_guns(self, items: List[Dict], max_price: float = 0.3) -> List[Dict]:
        """筛选价格 < max_price 的枪械饰品"""
        cheap = []
        for item in items:
            try:
                price = float(item.get("sell_min_price", item.get("price", "0")))
                if 0 < price < max_price:
                    cheap.append({
                        "id": item.get("id"),
                        "name": item.get("name", ""),
                        "price": price,
                        "sell_num": item.get("sell_num", 0),
                        "goods_id": item.get("id"),
                        "steam_market_url": item.get("steam_market_url", ""),
                    })
                    logger.info("符合条件: %s - %.2f 元", item.get("name", ""), price)
            except (ValueError, TypeError) as e:
                logger.debug("处理价格失败: %s", e)

        logger.info("筛选出 %d 个 < %.2f 元的枪械", len(cheap), max_price)
        return cheap

    def run(self, max_price: float = 0.3, max_pages: int = None, max_items: int = 5, tried_items=None):
        """运行主流程"""
        if max_pages is None:
            max_pages = self.event_config.default_max_pages

        if tried_items is None:
            tried_items = []

        logger.info("=== BUFF 挂件搜枪 ===")
        logger.info("事件: %s | 最高价: %.2f 元 | 最大页数: %d | 最大量: %d",
                     self.event_config.name, max_price, max_pages, max_items)

        if not self.test_login():
            logger.error("请先设置有效的 cookie")
            return

        # 获取所有挂件
        all_charms = []
        for page in range(1, max_pages + 1):
            logger.info("获取第 %d/%d 页挂件", page, max_pages)
            items = self.get_charms(page_num=page, page_size=20)
            if not items:
                break
            all_charms.extend(items)
            time.sleep(1)

        logger.info("总计获取 %d 个挂件", len(all_charms))

        purchases = []
        purchased_count = 0
        all_cheap_guns = []

        for i, charm in enumerate(all_charms):
            if purchased_count >= max_items:
                break

            charm_id = charm.get("id")
            charm_name = charm.get("name", "")
            logger.info("处理挂件 %d/%d: %s (ID: %s)", i + 1, len(all_charms), charm_name, charm_id)

            custom_charm_id = self.get_custom_charm_id(charm_id)
            if not custom_charm_id:
                custom_charm_id = str(charm_id)
                logger.info("未找到 custom_charm ID，使用备选: %s", custom_charm_id)

            time.sleep(random.uniform(0.5, 1.5))

            guns = self.get_guns_with_charm(custom_charm_id)
            if not guns:
                continue

            cheap_guns = self.filter_cheap_guns(guns, max_price)
            all_cheap_guns.extend(cheap_guns)

            for gun in cheap_guns:
                if purchased_count >= max_items:
                    break

                gun_id = gun["id"]
                gun_name = gun["name"]
                gun_price = gun["price"]

                logger.info("购买 %d: %s (%.2f 元)", purchased_count + 1, gun_name, gun_price)

                results = self.buy_item(
                    gun_id,
                    max_price=max_price,
                    max_orders=1,
                    charm_id=custom_charm_id,
                    tried_items=tried_items,
                )
                purchases.extend(results)

                for result in results:
                    if result.get("success"):
                        purchased_count += 1
                        logger.info("已购买 %d 个", purchased_count)
                        break

                time.sleep(2)
            time.sleep(1)

        # 汇总
        logger.info("总计找到 %d 个 < %.2f 元的带挂件枪械", len(all_cheap_guns), max_price)
        if all_cheap_guns:
            for i, gun in enumerate(all_cheap_guns):
                logger.info("  %d. %s - %.2f 元 (ID: %s)", i + 1, gun["name"], gun["price"], gun["id"])

        self.print_purchase_status(purchases)
        logger.info("=== 脚本运行完成 ===")
