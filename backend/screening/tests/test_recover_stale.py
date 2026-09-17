from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from screening.models import AnalysisSession


class RecoverStaleTests(TestCase):
    def _stale_session(self, status):
        session = AnalysisSession.objects.create(
            resume_filename="r.pdf",
            jd_filename="j.txt",
            status=status,
        )
        AnalysisSession.objects.filter(pk=session.pk).update(
            created_at=timezone.now() - timezone.timedelta(hours=2)
        )
        return session

    def _fresh_session(self, status):
        return AnalysisSession.objects.create(
            resume_filename="r.pdf",
            jd_filename="j.txt",
            status=status,
        )

    def test_stale_pending_and_processing_are_marked_failed(self):
        stale_pending = self._stale_session(AnalysisSession.Status.PENDING)
        stale_processing = self._stale_session(AnalysisSession.Status.PROCESSING)

        call_command("recover_stale")

        stale_pending.refresh_from_db()
        stale_processing.refresh_from_db()
        self.assertEqual(stale_pending.status, AnalysisSession.Status.FAILED)
        self.assertIn("aborted", stale_pending.error_message)
        self.assertEqual(stale_processing.status, AnalysisSession.Status.FAILED)

    def test_fresh_sessions_are_untouched(self):
        fresh_pending = self._fresh_session(AnalysisSession.Status.PENDING)
        fresh_processing = self._fresh_session(AnalysisSession.Status.PROCESSING)
        completed = self._fresh_session(AnalysisSession.Status.COMPLETED)

        call_command("recover_stale")

        fresh_pending.refresh_from_db()
        fresh_processing.refresh_from_db()
        completed.refresh_from_db()
        self.assertEqual(fresh_pending.status, AnalysisSession.Status.PENDING)
        self.assertEqual(fresh_processing.status, AnalysisSession.Status.PROCESSING)
        self.assertEqual(completed.status, AnalysisSession.Status.COMPLETED)
        self.assertEqual(fresh_pending.error_message, "")

    def test_completed_stale_sessions_are_untouched(self):
        stale_completed = self._stale_session(AnalysisSession.Status.COMPLETED)
        call_command("recover_stale")
        stale_completed.refresh_from_db()
        self.assertEqual(stale_completed.status, AnalysisSession.Status.COMPLETED)