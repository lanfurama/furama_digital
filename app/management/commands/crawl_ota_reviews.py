from django.core.management.base import BaseCommand
from concurrent.futures import ThreadPoolExecutor
from app.ota_crawlers import HotelsCombinedCrawler, BookingCrawler, AgodaCrawler, ExpediaCrawler, TripAdvisorCrawler 
class Command(BaseCommand):
    help = 'Crawl hotel reviews using different crawlers'

    def handle(self, *args, **options):
        # Danh sách các crawler bạn muốn sử dụng
        crawlers = [
            # HotelsCombinedCrawler(),
            # BookingCrawler()
            # AgodaCrawler()
            ExpediaCrawler()
            # TripAdvisorCrawler(),
        ]
        
        results = []

        # Sử dụng ThreadPoolExecutor để cào các URL song song
        with ThreadPoolExecutor(max_workers=10) as executor:  # Điều chỉnh max_workers tuỳ theo yêu cầu
            futures = []
            
            # Lặp qua các crawler và các URL của chúng
            for crawler in crawlers:
                for url in crawler.urls:
                    # Gọi hàm crawl() cho mỗi URL song song
                    futures.append(executor.submit(crawler.crawl, url))
            
            # Chờ tất cả các task hoàn thành và xử lý kết quả
            for future in futures:
                result = future.result()
                if "error" in result:
                    results.append(result)
                    continue

                # Lưu kết quả vào cơ sở dữ liệu nếu cần
                # saved_data = save_review_data(result, crawler)
                results.append(result)

        # In kết quả ra màn hình hoặc lưu vào file nếu cần
        self.stdout.write(self.style.SUCCESS('Crawl completed successfully!'))
        for result in results:
            self.stdout.write(str(result))  # In kết quả lên màn hình

