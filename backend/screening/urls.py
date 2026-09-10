from django.urls import path

from .views import AnalyzeView, ChatView, HealthView, RecordDetailView, RecordsListView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("analyze", AnalyzeView.as_view(), name="analyze"),
    path("chat", ChatView.as_view(), name="chat"),
    path("records", RecordsListView.as_view(), name="records-list"),
    path("records/<uuid:session_id>", RecordDetailView.as_view(), name="record-detail"),
]
