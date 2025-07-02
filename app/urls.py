from django.urls import path
from . import views

urlpatterns = [
    # rate_views
    path("rates", views.rate_views.index, name="rates"),
    path("ota/", views.ota_crawler_home, name="ota_review_crawler"),

    #ota_crawler_views
    path("api/reviews/crawl", views.ota_crawler_views.crawl_hotel_reviews)
]
