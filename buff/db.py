"""SQLite 数据层 - 价格快照和购买历史"""

import sqlite3
import threading
import time
from typing import Dict, List, Optional

from buff.log import logger

DEFAULT_DB = "buff_data.db"
_lock = threading.Lock()


def init_db(db_path: str = DEFAULT_DB) -> sqlite3.Connection:
    """初始化数据库，返回连接"""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS price_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goods_id TEXT NOT NULL,
            name TEXT,
            sell_min_price REAL,
            sell_num INTEGER,
            recorded_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS purchase_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goods_id TEXT NOT NULL,
            name TEXT,
            order_id TEXT,
            price REAL,
            status TEXT,
            error TEXT,
            bill_order_id TEXT,
            bought_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS monitored_items (
            goods_id TEXT PRIMARY KEY,
            name TEXT,
            max_price REAL,
            added_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_price_goods ON price_snapshots(goods_id, recorded_at);
        CREATE INDEX IF NOT EXISTS idx_purchase_goods ON purchase_history(goods_id, bought_at);

        CREATE TABLE IF NOT EXISTS market_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cache_key TEXT NOT NULL,
            cache_value TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_market_cache_key ON market_cache(cache_key, expires_at);

        CREATE TABLE IF NOT EXISTS steam_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goods_id TEXT NOT NULL,
            steam_price_usd REAL,
            steam_price_cny REAL,
            steam_volume INTEGER,
            recorded_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_steam_goods ON steam_prices(goods_id, recorded_at);
    """)
    conn.commit()

    logger.info("数据库初始化完成: %s", db_path)
    return conn


def record_price(conn: sqlite3.Connection, goods_id: str, name: str, sell_min_price: float, sell_num: int):
    """记录价格快照"""
    try:
        with _lock:
            conn.execute(
                "INSERT INTO price_snapshots (goods_id, name, sell_min_price, sell_num, recorded_at) VALUES (?, ?, ?, ?, ?)",
                (goods_id, name, sell_min_price, sell_num, time.strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
    except Exception as e:
        logger.debug("记录价格失败: %s", e)


def record_purchase(
    conn: sqlite3.Connection,
    goods_id: str,
    name: str,
    order_id: str = "",
    price: float = 0,
    status: str = "attempted",
    error: Optional[str] = None,
    bill_order_id: Optional[str] = None,
):
    """记录购买历史"""
    try:
        with _lock:
            conn.execute(
                "INSERT INTO purchase_history (goods_id, name, order_id, price, status, error, bill_order_id, bought_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (goods_id, name, order_id, price, status, error, bill_order_id, time.strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
    except Exception as e:
        logger.debug("记录购买失败: %s", e)


def add_monitored_item(conn: sqlite3.Connection, goods_id: str, name: str, max_price: float):
    """添加监控商品"""
    try:
        with _lock:
            conn.execute(
                "INSERT OR REPLACE INTO monitored_items (goods_id, name, max_price, added_at) VALUES (?, ?, ?, ?)",
                (goods_id, name, max_price, time.strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
    except Exception as e:
        logger.debug("添加监控商品失败: %s", e)


def get_price_history(conn: sqlite3.Connection, goods_id: str, days: int = 30) -> List[Dict]:
    """获取价格历史"""
    cutoff = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - days * 86400))
    with _lock:
        rows = conn.execute(
            "SELECT sell_min_price, sell_num, recorded_at FROM price_snapshots "
            "WHERE goods_id = ? AND recorded_at > ? ORDER BY recorded_at",
            (goods_id, cutoff),
        ).fetchall()
    return [dict(r) for r in rows]


def get_purchase_stats(conn: sqlite3.Connection, days: Optional[int] = None) -> Dict:
    """获取购买统计"""
    where = ""
    params: list = []
    if days:
        cutoff = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - days * 86400))
        where = "WHERE bought_at > ?"
        params = [cutoff]

    with _lock:
        rows = conn.execute(
            f"SELECT status, COUNT(*) as cnt, SUM(price) as total FROM purchase_history {where} GROUP BY status",
            params,
        ).fetchall()

        if where:
            daily_sql = (
                "SELECT DATE(bought_at) as day, COUNT(*) as cnt, SUM(price) as total "
                "FROM purchase_history WHERE bought_at > ? AND status = ? GROUP BY day ORDER BY day DESC LIMIT 30"
            )
            daily_params = [params[0], "success"]
        else:
            daily_sql = (
                "SELECT DATE(bought_at) as day, COUNT(*) as cnt, SUM(price) as total "
                "FROM purchase_history WHERE status = ? GROUP BY day ORDER BY day DESC LIMIT 30"
            )
            daily_params = ["success"]
        daily = conn.execute(daily_sql, daily_params).fetchall()

    stats = {"total_attempted": 0, "total_success": 0, "total_failed": 0, "total_spent": 0.0}
    for r in rows:
        stats["total_attempted"] += r["cnt"]
        if r["status"] == "success":
            stats["total_success"] = r["cnt"]
            stats["total_spent"] = r["total"] or 0.0
        elif r["status"] == "failed":
            stats["total_failed"] = r["cnt"]

    stats["daily"] = [dict(r) for r in daily]
    return stats


def get_all_monitored(conn: sqlite3.Connection) -> List[Dict]:
    """获取所有监控商品及其最新价格"""
    with _lock:
        rows = conn.execute("""
            SELECT m.goods_id, m.name, m.max_price, m.added_at,
                   p.sell_min_price as latest_price, p.sell_num as latest_sell_num, p.recorded_at as latest_recorded
            FROM monitored_items m
            LEFT JOIN (
                SELECT goods_id, sell_min_price, sell_num, recorded_at,
                       ROW_NUMBER() OVER (PARTITION BY goods_id ORDER BY recorded_at DESC) as rn
                FROM price_snapshots
            ) p ON m.goods_id = p.goods_id AND p.rn = 1
            ORDER BY m.added_at DESC
        """).fetchall()
    return [dict(r) for r in rows]


def get_purchase_history(conn: sqlite3.Connection, limit: int = 50, offset: int = 0) -> List[Dict]:
    """获取购买历史（分页）"""
    with _lock:
        rows = conn.execute(
            "SELECT * FROM purchase_history ORDER BY bought_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [dict(r) for r in rows]


def cache_get(conn: sqlite3.Connection, cache_key: str) -> Optional[str]:
    """获取缓存值（未过期则返回，否则返回 None）"""
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with _lock:
        row = conn.execute(
            "SELECT cache_value FROM market_cache WHERE cache_key = ? AND expires_at > ?",
            (cache_key, now),
        ).fetchone()
    return row["cache_value"] if row else None


def cache_set(conn: sqlite3.Connection, cache_key: str, value: str, ttl_seconds: int = 3600):
    """设置缓存值"""
    try:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        expires = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + ttl_seconds))
        with _lock:
            conn.execute(
                "INSERT OR REPLACE INTO market_cache (cache_key, cache_value, fetched_at, expires_at) VALUES (?, ?, ?, ?)",
                (cache_key, value, now, expires),
            )
            conn.commit()
    except Exception as e:
        logger.debug("设置缓存失败: %s", e)


def record_steam_price(conn: sqlite3.Connection, goods_id: str, usd: float, cny: float, volume: int):
    """记录 Steam 价格快照"""
    try:
        with _lock:
            conn.execute(
                "INSERT INTO steam_prices (goods_id, steam_price_usd, steam_price_cny, steam_volume, recorded_at) VALUES (?, ?, ?, ?, ?)",
                (goods_id, usd, cny, volume, time.strftime("%Y-%m-%d %H:%M:%S")),
            )
            conn.commit()
    except Exception as e:
        logger.debug("记录 Steam 价格失败: %s", e)


def get_steam_price_history(conn: sqlite3.Connection, goods_id: str, days: int = 30) -> List[Dict]:
    """获取 Steam 价格历史"""
    cutoff = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - days * 86400))
    with _lock:
        rows = conn.execute(
            "SELECT steam_price_usd, steam_price_cny, steam_volume, recorded_at FROM steam_prices "
            "WHERE goods_id = ? AND recorded_at > ? ORDER BY recorded_at",
            (goods_id, cutoff),
        ).fetchall()
    return [dict(r) for r in rows]
