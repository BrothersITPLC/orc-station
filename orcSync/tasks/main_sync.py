import logging

from celery import shared_task

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
