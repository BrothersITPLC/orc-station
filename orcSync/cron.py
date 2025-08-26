from .functions.orchestrator import run_sync_cycle


def run_sync():
    """
    This is the function that will be executed by the cron job.
    It's a simple wrapper around your existing orchestrator.
    """
    print("--- Django-Crontab: Starting sync cycle ---")
    try:
        run_sync_cycle()
        print("--- Django-Crontab: Sync cycle finished successfully ---")
    except Exception as e:
        print(f"--- Django-Crontab: ERROR during sync cycle ---")
        print(e)
        raise
