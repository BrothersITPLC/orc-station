import logging

from celery import shared_task
from django.db import close_old_connections

from orcSync.functions.orchestrator import run_sync_cycle

logging.basicConfig(
    filename="/app/logs/celery.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


@shared_task(
    bind=True,
    soft_time_limit=300,  
    time_limit=360,       
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_sync_task(self):
    """
    Celery task to run the synchronization cycle with the central server.
    
    Features:
    - Soft timeout at 5 minutes, hard timeout at 6 minutes
    - Auto-retry up to 3 times with exponential backoff
    - Explicit database connection cleanup to prevent pool exhaustion
    - Late acknowledgment to prevent lost tasks on worker crashes
    """
    logging.info("Starting sync cycle ****************")
    try:
        # Close any stale database connections before starting
        close_old_connections()
        logging.info("Closed stale database connections")
        
        run_sync_cycle()
        
        logging.info("Sync cycle finished successfully")
    except Exception as e:
        logging.error("ERROR during sync cycle", exc_info=True)
        # Re-raise to trigger Celery's retry mechanism
        raise
    finally:
        # Ensure database connections are closed after task completes
        close_old_connections()
        logging.info("Cleaned up database connections after sync")

