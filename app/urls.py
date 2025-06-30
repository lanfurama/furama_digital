from django.urls import path
from . import views

urlpatterns = [
    # rate_views
    path("", views.rate_views.dashboard, name="daily_rates_dashboard"),
    path("import_excel/", views.rate_views.import_excel, name="import_excel"),
    path('compare/<int:comparison_period>/', views.rate_views.dashboard, name='compare_dashboard'),
    path("ota/", views.ota_crawler_home, name="ota_review_crawler"),

    #ota_crawler_views
    path("api/reviews/crawl", views.ota_crawler_views.crawl_hotel_reviews)
]
