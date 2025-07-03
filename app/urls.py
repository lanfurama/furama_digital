from django.urls import path
from . import views

urlpatterns = [
    # rate_views
    path("rates", views.rate_views.index, name="rates"),
    path("ota/", views.ota_crawler_home, name="ota"),
]
