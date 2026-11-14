"""后台 worker 入口。

M0 只提供骨架：启动、日志、信号处理、优雅退出。
M4 接入真实任务（超时释放座位、违约结算、预约提醒）。

启动方式：
    python -m app.tasks.worker

设计约束：
- 多实例部署时，具体任务执行前必须抢 Redis 锁（见 app.core.redis）。
- 收到 SIGTERM 时先停止取新任务，等在途任务完成再退出。
"""

from __future__ import annotations

import asyncio
import logging
import signal

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.redis import close_redis, ping_redis

logger = logging.getLogger("app.worker")

TICK_SECONDS = 5


async def run_once() -> None:
    """一次调度循环。M4 在这里接入 ZSET 扫描。"""
    logger.debug("worker tick")


async def main() -> None:
    setup_logging("DEBUG" if settings.debug else "INFO")
    logger.info("worker starting", extra={"env": settings.env})

    try:
        await ping_redis()
        logger.info("redis reachable")
    except Exception:
        logger.warning("redis unreachable at startup, will retry in loop")

    stop_event = asyncio.Event()

    def _handle_signal(signum: int) -> None:
        logger.info("signal received, shutting down", extra={"status": signum})
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal, sig)

    while not stop_event.is_set():
        try:
            await run_once()
        except Exception:
            logger.exception("tick failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=TICK_SECONDS)
        except TimeoutError:
            continue

    await close_redis()
    logger.info("worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
