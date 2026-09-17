from django.utils import timezone
from django.core.management.base import BaseCommand

from screening.models import AnalysisSession

# Sessions stuck in these states for longer than this are presumed orphaned
# (e.g. the container restarted mid-analysis and the in-process worker thread
# died, or the queue never picked the job up).
STALE_MINUTES = 30


class Command(BaseCommand):
    help = "Mark pending/processing sessions older than STALE_MINUTES as failed."

    def handle(self, *args, **options):
        stale_before = timezone.now() - timezone.timedelta(minutes=STALE_MINUTES)
        updated = AnalysisSession.objects.filter(
            status__in=[AnalysisSession.Status.PENDING, AnalysisSession.Status.PROCESSING],
            created_at__lt=stale_before,
        ).update(
            status=AnalysisSession.Status.FAILED,
            error_message=(
                "Session aborted (server restart or timeout). "
                f"Please resubmit the resume and job description."
            ),
        )
        if updated:
            self.stdout.write(self.style.WARNING(f"Marked {updated} stale session(s) as failed."))
        else:
            self.stdout.write("No stale sessions to recover.")