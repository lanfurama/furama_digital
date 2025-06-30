from django.db import models

class DailyRate(models.Model):
    reported_date = models.DateField(db_column="reported_date")
    my_otb = models.FloatField()
    market_demand = models.FloatField()
    furama_resort = models.FloatField(db_column="Furama Resort Danang")
    hyatt_regency = models.FloatField(db_column="Hyatt Regency Danang Resort and Spa")
    pullman_beach = models.FloatField(db_column="Pullman Danang Beach Resort")
    sheraton_grand = models.FloatField(db_column="Sheraton Grand Danang Resort & Convention Center")
    danang_marriott = models.FloatField(db_column="Danang Marriott Resort & Spa")
    fusion_resort = models.FloatField(db_column="Fusion Resort and Villas Da Nang")
    shilla_monogram = models.FloatField(db_column="Shilla Monogram Quangnam Danang")
    koi_resort = models.FloatField(db_column="KOI Resort & Residence Da Nang")
    marriott_non_nuoc = models.FloatField(db_column="Danang Marriott Resort & Spa, Non Nuoc Beach Villas")
    premier_village = models.FloatField(db_column="Premier Village Danang Resort Managed By Accor")
    furama_villas = models.FloatField(db_column="Furama Villas Danang")
    updated_date = models.DateField(db_column="updated_date")

    class Meta:
        db_table = "daily_rates"  # khớp với tên bảng trong PostgreSQL

class OtaReview(models.Model):
    resort = models.CharField(max_length=255)
    url = models.TextField()
    source = models.CharField(max_length=50)
    rating = models.FloatField(null=True, blank=True)
    total_reviews = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ota_reviews"

    def __str__(self):
        return f"{self.resort} ({self.source})"

class OtaReviewCriterion(models.Model):
    source = models.CharField(max_length=50)
    key = models.CharField(max_length=100)  # e.g. 'staff', 'cleanliness'
    label = models.CharField(max_length=255)  # e.g. 'Staff Score'

    class Meta:
        db_table = "ota_review_criterion"

    def __str__(self):
        return f"{self.source}: {self.key}"

class OtaReviewScore(models.Model):
    review = models.ForeignKey(OtaReview, on_delete=models.CASCADE, related_name='scores')
    criterion = models.ForeignKey(OtaReviewCriterion, on_delete=models.CASCADE)
    value = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "ota_review_score"

    def __str__(self):
        return f"{self.review.resort} - {self.criterion.key}: {self.value}"