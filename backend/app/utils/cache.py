"""
任务状态缓存模块 - 用于减少数据库查询压力
"""
import time
import threading
from typing import Dict, Optional, Any, Tuple
from collections import defaultdict

# 配置
_CACHE_EXPIRE_SECONDS = 300  # 缓存有效期5分钟
_RATE_LIMIT_SECONDS = 1.0  # 每个任务每秒最多1次请求

# 内存存储
_task_status_cache: Dict[int, Tuple[Any, float]] = {}  # task_id -> (response_data, timestamp)
_task_request_times: Dict[int, list] = defaultdict(list)  # task_id -> [timestamps]
_cache_lock = threading.Lock()


def get_cached_or_fetch(task_id: int, fetch_func):
    """
    获取缓存的任务数据，如果缓存不存在或已过期则调用 fetch_func 获取
    """
    current_time = time.time()

    # 先检查是否超过频率限制
    with _cache_lock:
        times = _task_request_times[task_id]
        times[:] = [t for t in times if current_time - t < _RATE_LIMIT_SECONDS]
        is_rate_limited = len(times) >= 3
        times.append(current_time)

    # 检查缓存
    with _cache_lock:
        if task_id in _task_status_cache:
            data, timestamp = _task_status_cache[task_id]
            if current_time - timestamp < _CACHE_EXPIRE_SECONDS:
                # 缓存有效，返回缓存数据
                return data, is_rate_limited

    # 缓存不存在、已过期或需要刷新，从数据库获取
    data = fetch_func()

    # 更新缓存
    with _cache_lock:
        _task_status_cache[task_id] = (data, current_time)

    return data, is_rate_limited


def clear_cache(task_id: int):
    """清除指定任务的缓存"""
    with _cache_lock:
        _task_status_cache.pop(task_id, None)
        _task_request_times.pop(task_id, None)


def clear_all_cache():
    """清除所有缓存"""
    with _cache_lock:
        _task_status_cache.clear()
        _task_request_times.clear()
