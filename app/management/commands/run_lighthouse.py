# from django.core.management.base import BaseCommand
# from app.services.automation.lighthouse.fetch_rates import LighthouseRateFetcher

# class Command(BaseCommand):
#     help = "Tự động fetch rates từ Lighthouse"

#     def handle(self, *args, **kwargs):
#         fetcher = LighthouseRateFetcher(headless=False)
#         try:
#             self.stdout.write("Đang bắt đầu lấy dữ liệu từ Lighthouse...")
#             fetcher.login()
#             result = fetcher.fetch_rates()
#             self.stdout.write(str(result))
#         finally:
#             self.stdout.write('Done !')
#             fetcher.close()


from django.core.management.base import BaseCommand
from app.services.automation.lighthouse.fetch_rates import LighthouseRateFetcher


class Command(BaseCommand):
    help = "Tự động fetch rates từ Lighthouse cho nhiều tháng liên tiếp"

    def add_arguments(self, parser):
        parser.add_argument(
            '--before',
            type=int,
            default=2,
            help="Số tháng lùi về quá khứ từ tháng hiện tại (mặc định: 2)"
        )
        parser.add_argument(
            '--after',
            type=int,
            default=1,
            help="Số tháng tiến tới tương lai từ tháng hiện tại (mặc định: 1)"
        )
        parser.add_argument(
            '--headless',
            action='store_true',
            help="Chạy ở chế độ headless (ẩn trình duyệt)"
        )

    def handle(self, *args, **options):
        before = options['before']
        after = options['after']
        headless = options['headless']

        fetcher = LighthouseRateFetcher(headless=headless)
        try:
            self.stdout.write("🚀 Đang bắt đầu đăng nhập vào Lighthouse...")
            fetcher.login()

            self.stdout.write(f"📅 Đang lấy dữ liệu từ {before} tháng trước đến {after} tháng sau...")
            results = fetcher.fetch_multiple_months_auto(months_before=before, months_after=after)

            for month, status in results:
                self.stdout.write(f"✅ {month}: {status}")

        except Exception as e:
            self.stderr.write(f"❌ Đã xảy ra lỗi: {str(e)}")
        finally:
            fetcher.close()
            self.stdout.write("✅ Đã hoàn tất.")
