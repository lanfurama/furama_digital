from django.contrib import admin

# Register your models here.
from .models import DailyRate, OtaReview, OtaReviewScore, OtaReviewCriterion

admin.site.register(DailyRate)
admin.site.register(OtaReview)
admin.site.register(OtaReviewScore)
admin.site.register(OtaReviewCriterion)