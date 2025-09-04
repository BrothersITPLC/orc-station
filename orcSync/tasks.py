# from .functions.orchestrator import run_sync_cycle


# def run_sync():
#     """
#     This is the function that will be executed by the cron job.
#     It's a simple wrapper around your existing orchestrator.
#     """
#     print("--- Django-Crontab: Starting sync cycle **************** ---")
#     try:
#         run_sync_cycle()
#         print("--- Django-Crontab: Sync cycle finished successfully ---")
#     except Exception as e:
#         print(f"--- Django-Crontab: ERROR during sync cycle ---")
#         print(e)
#         raise

import logging

from celery import shared_task  # FIXED

from orcSync.functions.orchestrator import run_sync_cycle

logging.basicConfig(
    filename="/app/logs/celery.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@shared_task
def run_sync_task():
    logging.info("Starting sync cycle ****************")
    try:
        run_sync_cycle()
        logging.info("Sync cycle finished successfully")
    except Exception as e:
        logging.error("ERROR during sync cycle", exc_info=True)
