# linkedin/tgb_urls.py
"""TGB Hunt URL configuration."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.shortcuts import redirect
from linkedin.views import daemon_api


def root_redirect(request):
    from linkedin.models import JobHuntProfile
    if JobHuntProfile.objects.exists():
        return redirect("/dashboard/job-hunt/")
    return redirect("/setup/")


def setup_bc_redirect(request, step=None):
    return redirect("/setup/")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("setup/", include("linkedin.views.jh_setup")),
    path("setup/job-hunt/<int:step>/", setup_bc_redirect),
    path("setup/job-hunt/", setup_bc_redirect),
    path("dashboard/", lambda r: redirect("/dashboard/job-hunt/")),
    path("dashboard/job-hunt/", include("linkedin.tgb_dashboard")),
    path("api/daemon/status", daemon_api.status_view),
    path("api/daemon/start", daemon_api.start_view),
    path("api/daemon/stop", daemon_api.stop_view),
    path("", root_redirect),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
