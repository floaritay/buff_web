"""市场情报模块 - BUFF 市场行情、Steam 价格对比、订单管理"""

import json
import random
import re
import time
from typing import Dict, List, Optional
from urllib.parse import quote, unquote

import requests

from buff.log import logger


class BuffMarket:
    """BUFF 市场数据抓取与 Steam 价格对比"""

    def __init__(self, client):
        self.client = client
        self._steam_session = requests.Session()
        self._steam_session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        # USD to CNY approximate rate
        self._usd_cny = 7.25
        self._last_request_ts = 0.0

    def _throttle(self, min_delay: float = 1.0, max_delay: float = 2.5):
        """确保两次请求之间有足够间隔，避免触发 BUFF 限流"""
        elapsed = time.time() - self._last_request_ts
        wait = random.uniform(min_delay, max_delay)
        if elapsed < wait:
            time.sleep(wait - elapsed)
        self._last_request_ts = time.time()

    # ── BUFF 市场行情 ─────────────────────────────────────────

    def get_trending_items(self, sort_by: str = "default", page_num: int = 1,
                           page_size: int = 20, search: str = "") -> List[Dict]:
        """获取热门/趋势商品列表，支持关键词搜索

        sort_by: default(不传参), price.asc, price.desc, sell_num
        search: 搜索关键词（商品名称或 goods_id）
        """
        url = f"{self.client.BASE_URL}/api/market/goods"
        params = {
            "game": self.client.game,
            "page_num": page_num,
            "page_size": page_size,
        }
        # BUFF API 不接受 sort_by=default，只在有明确排序时传入
        if sort_by and sort_by != "default":
            params["sort_by"] = sort_by
        if search:
            params["search"] = search
        try:
            self._throttle()
            resp = self.client._api_request("GET", url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "OK":
                    items = data.get("data", {}).get("items", [])
                    result = []
                    for item in items:
                        result.append({
                            "goods_id": str(item.get("id", "")),
                            "name": item.get("name", ""),
                            "sell_min_price": float(item.get("sell_min_price", 0)),
                            "sell_num": int(item.get("sell_num", 0)),
                            "steam_market_url": item.get("steam_market_url", ""),
                            "icon_url": item.get("goods_icon_url", item.get("icon", "")),
                            "market_hash_name": item.get("market_hash_name", ""),
                        })
                    logger.info("获取到 %d 个趋势商品 (sort_by=%s)", len(result), sort_by)
                    return result
                logger.warning("获取趋势商品失败: code=%s, msg=%s, error=%s",
                               data.get("code"), data.get("msg"), data.get("error"))
            else:
                logger.warning("获取趋势商品 HTTP %d", resp.status_code)
        except Exception as e:
            logger.error("获取趋势商品异常: %s", e)
        return []

    # ── 商品详情 ──────────────────────────────────────────────

    def _fetch_raw_sell_orders(self, goods_id: str) -> tuple:
        """直接获取卖单原始数据，返回 (items_list, goods_infos_dict)"""
        url = f"{self.client.BASE_URL}/api/market/goods/sell_order"
        params = {
            "game": self.client.game,
            "goods_id": goods_id,
            "page_num": 1,
            "sort_by": "default",
            "mode": "",
            "allow_tradable_cooldown": 1,
        }
        try:
            self._throttle()
            resp = self.client._api_request("GET", url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "OK":
                    raw = data.get("data", {})
                    return raw.get("items", []), raw.get("goods_infos", {})
                logger.warning("获取卖单失败: code=%s, error=%s", data.get("code"), data.get("error"))
        except Exception as e:
            logger.error("获取卖单异常: %s", e)
        return [], {}

    def get_item_detail(self, goods_id: str) -> Dict:
        """获取商品详情：卖单 + 求购 + 价格走势"""
        result = {"goods_id": goods_id, "name": "", "icon_url": "",
                  "buff_sell_min": 0, "buff_sell_num": 0,
                  "sell_orders": [], "buy_orders": [], "price_history": []}

        raw_orders, goods_infos = self._fetch_raw_sell_orders(goods_id)

        # 从 goods_infos 提取商品名称和图标
        info = goods_infos.get(str(goods_id), goods_infos.get(goods_id, {}))
        if isinstance(info, dict):
            result["name"] = info.get("name", "")
            result["icon_url"] = info.get("icon_url", "")

        if raw_orders:
            # 从卖单中提取价格
            prices = [float(o.get("price", 0)) for o in raw_orders if o.get("price") is not None]
            if prices:
                result["buff_sell_min"] = min(prices)
            result["buff_sell_num"] = len(raw_orders)

            # 备用图标
            if not result["icon_url"]:
                result["icon_url"] = raw_orders[0].get("asset_info", {}).get("info", {}).get("icon_url", "")

            # 精简卖单列表（paintwear 在 asset_info 顶层）
            for o in raw_orders[:30]:
                o_asset = o.get("asset_info", {})
                result["sell_orders"].append({
                    "id": o.get("id", ""),
                    "price": float(o.get("price", 0)),
                    "seller": o.get("user_id", ""),
                    "paintwear": o_asset.get("paintwear", ""),
                })

        # 获取求购单
        self._throttle()
        result["buy_orders"] = self._fetch_buy_orders(goods_id)

        # 获取价格走势
        self._throttle()
        result["price_history"] = self._fetch_price_history(goods_id)

        return result

    def _fetch_buy_orders(self, goods_id: str) -> List[Dict]:
        """获取商品的求购单"""
        url = f"{self.client.BASE_URL}/api/market/goods/buy_order"
        params = {"game": self.client.game, "goods_id": goods_id, "page_num": 1}
        try:
            resp = self.client._api_request("GET", url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "OK":
                    orders = data.get("data", {}).get("items", [])
                    result = []
                    for o in orders:
                        created_ts = o.get("created_at", 0)
                        result.append({
                            "id": str(o.get("id", "")),
                            "price": float(o.get("price", 0)),
                            "num": int(o.get("num", 0)),
                            "user_id": o.get("user_id", ""),
                            "state": o.get("state", ""),
                            "created_at": time.strftime("%Y-%m-%d %H:%M", time.localtime(created_ts))
                            if isinstance(created_ts, (int, float)) and created_ts > 0 else "",
                        })
                    return result
        except Exception as e:
            logger.debug("获取求购单失败: %s", e)
        return []

    def _fetch_price_history(self, goods_id: str) -> List[Dict]:
        """获取商品价格走势（BUFF 提供的 Steam 历史价格）"""
        url = f"{self.client.BASE_URL}/api/market/goods/price_history"
        params = {"game": self.client.game, "goods_id": goods_id}
        try:
            resp = self.client._api_request("GET", url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "OK":
                    ph = data.get("data", {}).get("price_history", [])
                    result = []
                    for entry in ph:
                        if isinstance(entry, list) and len(entry) >= 2:
                            ts_ms, price = entry[0], entry[1]
                            result.append({
                                "date": time.strftime("%m-%d", time.localtime(ts_ms / 1000)),
                                "price": float(price),
                            })
                    return result
        except Exception as e:
            logger.debug("获取价格走势失败: %s", e)
        return []

    # ── 订单管理 ──────────────────────────────────────────────

    def get_buy_orders(self, page_num: int = 1, page_size: int = 20) -> List[Dict]:
        """获取用户购买订单历史 (buy_order/history)"""
        url = f"{self.client.BASE_URL}/api/market/buy_order/history"
        params = {
            "game": self.client.game,
            "page_num": page_num,
            "page_size": page_size,
        }
        try:
            self._throttle()
            resp = self.client._api_request("GET", url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "OK":
                    orders = data.get("data", {}).get("items", [])
                    result = []
                    for order in orders:
                        asset = order.get("asset_info", {})
                        created_ts = order.get("created_at", 0)
                        created_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(created_ts)) if isinstance(created_ts, (int, float)) and created_ts > 0 else str(created_ts)
                        result.append({
                            "id": str(order.get("id", "")),
                            "goods_id": str(order.get("goods_id", "")),
                            "goods_name": asset.get("goods_info", {}).get("name", ""),
                            "price": float(order.get("price", 0)),
                            "state": order.get("state", ""),
                            "state_text": order.get("state_text", ""),
                            "seller_id": str(order.get("seller_id", "")),
                            "created_at": created_str,
                            "icon_url": asset.get("info", {}).get("icon_url", ""),
                        })
                    logger.info("获取到 %d 个购买订单", len(result))
                    return result
                logger.warning("获取购买订单失败: code=%s, error=%s", data.get("code"), data.get("error"))
            else:
                logger.warning("获取购买订单 HTTP %d", resp.status_code)
        except Exception as e:
            logger.error("获取购买订单异常: %s", e)
        return []

    def get_sell_orders_history(self, page_num: int = 1, page_size: int = 20) -> List[Dict]:
        """获取用户出售订单历史 (sell_order/history)"""
        url = f"{self.client.BASE_URL}/api/market/sell_order/history"
        params = {
            "game": self.client.game,
            "page_num": page_num,
            "page_size": page_size,
        }
        try:
            self._throttle()
            resp = self.client._api_request("GET", url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "OK":
                    orders = data.get("data", {}).get("items", [])
                    result = []
                    for order in orders:
                        asset = order.get("asset_info", {})
                        created_ts = order.get("created_at", 0)
                        created_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(created_ts)) if isinstance(created_ts, (int, float)) and created_ts > 0 else str(created_ts)
                        result.append({
                            "id": str(order.get("id", "")),
                            "goods_id": str(order.get("goods_id", "")),
                            "goods_name": asset.get("goods_info", {}).get("name", ""),
                            "price": float(order.get("price", 0)),
                            "state": order.get("state", ""),
                            "state_text": order.get("state_text", ""),
                            "buyer_id": str(order.get("buyer_id", "")),
                            "created_at": created_str,
                            "icon_url": asset.get("info", {}).get("icon_url", ""),
                        })
                    logger.info("获取到 %d 个出售订单", len(result))
                    return result
                logger.warning("获取出售订单失败: code=%s, error=%s", data.get("code"), data.get("error"))
            else:
                logger.warning("获取出售订单 HTTP %d", resp.status_code)
        except Exception as e:
            logger.error("获取出售订单异常: %s", e)
        return []

    # ── Steam 价格 ────────────────────────────────────────────

    def _parse_steam_url(self, steam_market_url: str) -> Optional[str]:
        """从 Steam 市场 URL 提取 market_hash_name"""
        # https://steamcommunity.com/market/listings/730/AK-47%20%7C%20Redline%20%28Field-Tested%29
        m = re.search(r"/market/listings/730/(.+?)(?:\?|$)", steam_market_url)
        if m:
            return unquote(m.group(1))
        return None

    def get_steam_price(self, steam_market_url: str, cache_conn=None, goods_id: str = "") -> Optional[Dict]:
        """获取 Steam 市场价格

        Returns: {"lowest_price": float, "volume": int, "median_price": float, "currency": "USD"} or None
        """
        market_hash_name = self._parse_steam_url(steam_market_url)
        if not market_hash_name:
            logger.debug("无法解析 Steam URL: %s", steam_market_url)
            return None

        # 检查缓存
        if cache_conn:
            from buff.db import cache_get
            cache_key = f"steam_price:{market_hash_name}"
            cached = cache_get(cache_conn, cache_key)
            if cached:
                try:
                    return json.loads(cached)
                except Exception:
                    pass

        # 调用 Steam priceoverview API
        try:
            url = "https://steamcommunity.com/market/priceoverview/"
            params = {
                "appid": 730,
                "currency": 1,  # USD
                "market_hash_name": market_hash_name,
            }
            time.sleep(random.uniform(3.0, 6.0))
            resp = self._steam_session.get(url, params=params, timeout=20)

            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") == 1:
                    lowest = data.get("lowest_price", "$0")
                    volume = data.get("volume", "0")
                    median = data.get("median_price", "$0")

                    def parse_usd(s):
                        m2 = re.search(r"[\d.]+", s.replace(",", ""))
                        return float(m2.group()) if m2 else 0.0

                    result = {
                        "lowest_price_usd": parse_usd(lowest),
                        "volume": int(re.sub(r"[^\d]", "", volume) or 0),
                        "median_price_usd": parse_usd(median),
                        "lowest_price_cny": round(parse_usd(lowest) * self._usd_cny, 2),
                        "median_price_cny": round(parse_usd(median) * self._usd_cny, 2),
                    }

                    # 缓存结果
                    if cache_conn:
                        from buff.db import cache_set, record_steam_price
                        cache_set(cache_conn, f"steam_price:{market_hash_name}", json.dumps(result), 3600)
                        if goods_id:
                            record_steam_price(cache_conn, goods_id,
                                               result["lowest_price_usd"], result["lowest_price_cny"], result["volume"])

                    logger.info("Steam 价格: %s = $%.2f (¥%.2f)", market_hash_name,
                                result["lowest_price_usd"], result["lowest_price_cny"])
                    return result
                else:
                    logger.debug("Steam API 返回失败: %s", data)
            else:
                logger.debug("Steam API HTTP %d", resp.status_code)
        except Exception as e:
            logger.debug("获取 Steam 价格异常: %s", e)

        return None

    # ── 价格对比 ──────────────────────────────────────────────

    def compare_prices(self, items: List[Dict], cache_conn=None) -> List[Dict]:
        """对比 BUFF 和 Steam 价格，计算套利空间

        items: 每项需有 goods_id, name, sell_min_price (BUFF), steam_market_url
        Returns: 原 items 增加 steam_price_cny, diff, diff_pct, arbitrage_opportunity
        """
        result = []
        for item in items:
            enriched = dict(item)
            buff_price = float(item.get("sell_min_price", 0))
            steam_url = item.get("steam_market_url", "")

            if steam_url:
                steam_data = self.get_steam_price(steam_url, cache_conn=cache_conn, goods_id=item.get("goods_id", ""))
                if steam_data:
                    steam_cny = steam_data["lowest_price_cny"]
                    enriched["steam_price_cny"] = steam_cny
                    enriched["steam_volume"] = steam_data["volume"]
                    if buff_price > 0:
                        enriched["diff"] = round(steam_cny - buff_price, 2)
                        enriched["diff_pct"] = round((steam_cny - buff_price) / buff_price * 100, 1)
                        # Steam 抽成 15%，套利需 > 15% 价差
                        enriched["arbitrage_opportunity"] = enriched["diff_pct"] > 15
                    else:
                        enriched["diff"] = 0
                        enriched["diff_pct"] = 0
                        enriched["arbitrage_opportunity"] = False
                else:
                    enriched["steam_price_cny"] = None
                    enriched["steam_volume"] = None
                    enriched["diff"] = None
                    enriched["diff_pct"] = None
                    enriched["arbitrage_opportunity"] = False
            else:
                enriched["steam_price_cny"] = None
                enriched["steam_volume"] = None
                enriched["diff"] = None
                enriched["diff_pct"] = None
                enriched["arbitrage_opportunity"] = False

            result.append(enriched)
        return result
