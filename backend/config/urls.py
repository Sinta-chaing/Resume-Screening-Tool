from django.urls import include, path
from drf_spectacular.renderers import OpenApiJsonRenderer
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


class JsonSpectacularAPIView(SpectacularAPIView):
    renderer_classes = [OpenApiJsonRenderer]


urlpatterns = [
    path("api/schema/", JsonSpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/", include("screening.urls")),
]
