from django.core.management.base import BaseCommand
from concurrent.futures import ThreadPoolExecutor
from app.ota_crawlers.hotelscombined import HotelsCombinedCrawler
from app.ota_crawlers.booking import BookingCrawler
from app.ota_crawlers.agoda import AgodaCrawler
from app.ota_crawlers.expedia import ExpediaCrawler
from app.ota_crawlers.tripadvisor import TripAdvisorCrawler
from app.ota_crawlers.naver import NaverCrawler
from app.ota_crawlers.google import GoogleReviewCrawler
from app.utils import save_review_data

class Command(BaseCommand):
    help = 'Crawl hotel reviews using different crawlers'

    def handle(self, *args, **options):
        # Danh sách các crawler bạn muốn sử dụng
        crawlers = [
            HotelsCombinedCrawler(),
            BookingCrawler(),
            AgodaCrawler(),
            ExpediaCrawler(),
            TripAdvisorCrawler(),
            GoogleReviewCrawler(),
            NaverCrawler(),
        ]
        
        results = []

       # Lặp qua các crawler và xử lý tuần tự
        for crawler in crawlers:
            for url in crawler.urls:
                # Gọi hàm crawl() cho mỗi URL tuần tự
                result = crawler.crawl(url)
                if "error" in result:
                    results.append(result)
                    continue
                
                # Lưu kết quả vào cơ sở dữ liệu nếu cần
                # save_review_data(result, crawler)
                results.append(result)

        # Đảm bảo rằng các driver selenium được đóng sau khi crawl xong
        for crawler in crawlers:
            crawler.close()  # Đảm bảo đóng driver selenium sau khi hoàn thành

        # In kết quả ra màn hình hoặc lưu vào file nếu cần
        self.stdout.write(self.style.SUCCESS('Crawl completed successfully!'))
        for result in results:
            self.stdout.write(str(result))  # In kết quả lên màn hình

