import uuid

from django.db import models
from pgvector.django import VectorField


class AnalysisSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resume_filename = models.CharField(max_length=255)
    jd_filename = models.CharField(max_length=255)
    candidate_name = models.CharField(max_length=255, blank=True, default="")
    position = models.CharField(max_length=255, blank=True, default="")
    evaluation = models.JSONField(default=dict)
    resume_summary = models.TextField(blank=True)
    chunk_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Session {self.id} ({self.resume_filename})"


class ResumeChunk(models.Model):
    session = models.ForeignKey(
        AnalysisSession,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_key = models.CharField(max_length=64)
    text = models.TextField()
    embedding = VectorField(dimensions=1024)

    class Meta:
        ordering = ["chunk_key"]
        indexes = [
            models.Index(fields=["session", "chunk_key"]),
        ]

    def __str__(self) -> str:
        return self.chunk_key
