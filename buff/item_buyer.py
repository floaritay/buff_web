"""BuffItemBuyer - 指定饰品自动购买类"""

import random
import re
import sys
import time
from typing import Dict, List, Optional

from buff.client import BuffClient
from buff.log import logger


def parse_goods_id(raw: str) -> str:
    """从 URL 或纯数字中提取 goods_id"""
    raw = raw.strip()
    m = re.search(r"buff\.163\.com/goods/(\d+)", raw)
    if m:
        return m.group(1)
    m = re.search(r"/goods/(\d+)", raw)
    if m:
        return m.group(1)
    if raw.isdigit():
        return raw
    logger.error("无法从 '%s' 中解析 goods_id", raw)
    logger.info("支持: https://buff.163.com/goods/12345 或 12345")
    sys.exit(1)


class BuffItemBuyer(BuffClient):
    """BUFF 指定饰品购买器"""

    def search_items(self, keyword: str, page_size: int = 10) -> List[Dict]:
        """按名称搜索饰品

        支持完整名称精确匹配，如 "AK-47（纪念品） | 灰变迷彩 (久经沙场)"
        """
        url = f"{self.BASE_URL}/api/market/goods"
        params = {
            "game": self.game,
            "page_num": 1,
            "page_size": page_size,
            "search": keyword,
            "sort_by": "price.asc",
        }
        try:
            resp = self._api_request("GET", url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "OK":
                    return data.get("data", {}).get("items", [])
                logger.warning("搜索失败: %s", data.get("msg"))
            else:
                logger.warning("搜索 HTTP %d", resp.status_code)
        except Exception as e:
            logger.error("搜索异常: %s", e)
        return []

    def run(
        self,
        goods_id: str,
        max_price: float = 1.0,
        max_items: int = 5,
        tried_items: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """单次执行：检查指定饰品并购买低于价格阈值的卖单"""
        if tried_items is None:
            tried_items = []

        logger.info("=" * 50)
        logger.info("goods_id: %s | 最高价: %.2f 元 | 最大量: %d | 已尝试: %d",
                     goods_id, max_price, max_items, len(tried_items))
        logger.info("=" * 50)

        if not self.test_login():
            logger.error("请先设置有效的 cookie")
            return []

        # 使用基类统一购买流程
        return self.buy_item(
            goods_id,
            max_price=max_price,
            max_orders=max_items,
            tried_items=tried_items,
        )

    def run_polling(
        self,
        goods_id: str,
        max_price: float = 1.0,
        max_items: int = 5,
        interval: int = 30,
        max_rounds: int = 0,
        tried_items: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """轮询监控模式"""
        if tried_items is None:
            tried_items = []

        logger.info("轮询模式，间隔 %d 秒", interval)
        if max_rounds > 0:
            logger.info("最大轮询次数: %d", max_rounds)
        else:
            logger.info("无限轮询，按 Ctrl+C 停止")

        all_results = []
        round_num = 0
        try:
            while True:
                round_num += 1
                if max_rounds > 0 and round_num > max_rounds:
                    logger.info("已达到最大轮询次数 %d", max_rounds)
                    break

                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                logger.info("#" * 50)
                logger.info("# 第 %d 轮 | %s", round_num, ts)
                logger.info("#" * 50)

                results = self.run(
                    goods_id=goods_id,
                    max_price=max_price,
                    max_items=max_items,
                    tried_items=tried_items,
                )
                all_results.extend(results)

                if max_rounds > 0 and round_num >= max_rounds:
                    break

                logger.info("等待 %d 秒...", interval)
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("用户中断，共完成 %d 轮", round_num)

        return all_results

    def run_batch(
        self,
        items: List[Dict],
        interval: int = 30,
        max_rounds: int = 0,
        tried_items: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """批量监控多个商品

        Args:
            items: [{"goods_id": str, "max_price": float}, ...]
            interval: 每轮之间的间隔秒数
            max_rounds: 最大轮次，0=无限
            tried_items: 已尝试记录
        """
        if tried_items is None:
            tried_items = []

        logger.info("批量监控 %d 个商品，间隔 %d 秒", len(items), interval)
        if max_rounds > 0:
            logger.info("最大轮次: %d", max_rounds)
        else:
            logger.info("无限轮询，按 Ctrl+C 停止")

        all_results = []
        round_num = 0
        try:
            while True:
                round_num += 1
                if max_rounds > 0 and round_num > max_rounds:
                    logger.info("已达到最大轮次 %d", max_rounds)
                    break

                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                logger.info("=" * 60)
                logger.info("第 %d 轮 | %s | 共 %d 个商品", round_num, ts, len(items))
                logger.info("=" * 60)

                for idx, item_info in enumerate(items):
                    gid = item_info["goods_id"]
                    mp = item_info.get("max_price", 1.0)
                    logger.info("─── 商品 %d/%d: %s (最高价 %.2f) ───", idx + 1, len(items), gid, mp)

                    results = self.buy_item(
                        gid,
                        max_price=mp,
                        max_orders=5,
                        tried_items=tried_items,
                    )
                    all_results.extend(results)

                    # 商品间随机延迟
                    if idx < len(items) - 1:
                        wait = random.uniform(2, 5)
                        logger.debug("等待 %.1f 秒...", wait)
                        time.sleep(wait)

                # 每轮保存一次
                from buff.utils import save_tried_items
                save_tried_items(tried_items)

                if max_rounds > 0 and round_num >= max_rounds:
                    break

                logger.info("等待 %d 秒后下一轮...", interval)
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("用户中断，共完成 %d 轮", round_num)

        return all_results
