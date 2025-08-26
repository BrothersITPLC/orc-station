from django.core.management.base import BaseCommand

from orcSync.functions import run_sync_cycle


class Command(BaseCommand):
    help = "Executes one full synchronization cycle with the central server."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting manual synchronization..."))
        try:
            run_sync_cycle()
            self.stdout.write(self.style.SUCCESS("Synchronization cycle finished."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An unexpected error occurred: {e}"))
