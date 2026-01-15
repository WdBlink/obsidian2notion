"""
Main entry point for the Obsidian to Notion sync service.

此脚本启动定时同步任务或执行一次性同步。
Author: wdblink
"""

import time
import schedule
import argparse
from src.config import get_config
from src.sync_service import SyncService
from src.utils import setup_logger

logger = setup_logger(__name__)

def job():
    """定时任务函数。"""
    logger.info("Scheduled sync job started.")
    try:
        service = SyncService()
        service.sync()
    except Exception as e:
        logger.error(f"Job failed: {e}")
    logger.info("Scheduled sync job finished.")

def main():
    """主函数。"""
    parser = argparse.ArgumentParser(description="Obsidian to Notion Sync Service")
    parser.add_argument("--once", action="store_true", help="Run sync once and exit")
    args = parser.parse_args()

    try:
        config = get_config()
    except ValueError as e:
        logger.critical(f"Configuration error: {e}")
        return

    # 初始化一次服务以确保连接正常
    try:
        # 可以在这里做一些连通性测试
        pass
    except Exception as e:
        logger.critical(f"Initialization failed: {e}")
        return

    if args.once:
        logger.info("Running one-time sync...")
        job()
        return

    interval = config.SYNC_INTERVAL_MINUTES
    logger.info(f"Starting scheduler. Sync interval: {interval} minutes.")
    
    # 立即运行一次
    job()
    
    schedule.every(interval).minutes.do(job)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Service stopped by user.")

if __name__ == "__main__":
    main()
