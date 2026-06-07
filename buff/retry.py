"""带指数退避的请求重试工具"""

import random
import time

import requests

from buff.log import logger


def api_request(
    session: requests.Session,
    method: str,
    url: str,
    *,
    max_retries: int = 3,
    base_delay: float = 2.0,
    backoff_factor: float = 2.0,
    **kwargs,
) -> requests.Response:
    """发送 HTTP 请求，遇到临时错误时自动重试。

    重试条件：
    - HTTP 429 (Too Many Requests)
    - HTTP 5xx
    - requests.exceptions.Timeout / ConnectionError

    其他 4xx 错误直接抛出。
    """
    kwargs.setdefault("timeout", 15)
    resp = None

    for attempt in range(max_retries + 1):
        try:
            resp = session.request(method, url, **kwargs)

            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt < max_retries:
                    delay = base_delay * (backoff_factor ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        "HTTP %d on %s %s, retrying in %.1fs (%d/%d)",
                        resp.status_code, method, url, delay, attempt + 1, max_retries,
                    )
                    time.sleep(delay)
                    continue
            return resp

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < max_retries:
                delay = base_delay * (backoff_factor ** attempt) + random.uniform(0, 1)
                logger.warning(
                    "%s on %s %s, retrying in %.1fs (%d/%d)",
                    type(e).__name__, method, url, delay, attempt + 1, max_retries,
                )
                time.sleep(delay)
            else:
                raise

    return resp  # resp is always set after at least one iteration
