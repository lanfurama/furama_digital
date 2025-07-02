# reviews/crawlers/hotelscombined.py

import re
import logging
from selenium.webdriver.common.action_chains import ActionChains
from .base_crawler import BaseCrawler
from multiprocessing import Pool

logger = logging.getLogger(__name__)

class AgodaCrawler(BaseCrawler):
    def __init__(self):
        self.source = "agoda"
        urls = [
            "https://www.agoda.com/furama-resort-danang/hotel/da-nang-vn.html",
            "https://www.agoda.com/fusion-maia-resort-all-spa-inclusive/hotel/da-nang-vn.html",
            "https://www.agoda.com/pullman-danang-beach-resort/hotel/da-nang-vn.html",
            "https://www.agoda.com/premier-village-danang-resort-managed-by-accor-hotels/hotel/da-nang-vn.html",
            "https://www.agoda.com/danang-marriott-resort-spa-non-nuoc-beach-villas/hotel/da-nang-vn.html",
            "https://www.agoda.com/hyatt-regency-danang-resort-and-spa/hotel/da-nang-vn.html",
            "https://www.agoda.com/naman-retreat-resort/hotel/da-nang-vn.html",
            "https://www.agoda.com/furama-villas-danang/hotel/da-nang-vn.html",
            "https://www.agoda.com/sheraton-grand-danang-resort/hotel/da-nang-vn.html",
            "https://www.agoda.com/fusion-resort-and-villas-da-nang/hotel/da-nang-vn.html"
        ]
        super().__init__(urls=urls, use_selenium=True)

    def extract_resort_name(self, url):
        match = re.search(r'agoda\.com/(?:vi-vn/)?([^/]+)/hotel/', url)
        if match:
            return match.group(1).replace("-", " ").title()
        return "Unknown"

    def extract_rating(self, text):
        match = re.search(r"(\d\.\d)\s*(?:/10|out of 10)?", text)
        return float(match.group(1)) if match else None

    def extract_total_reviews(self, text):
        patterns = [r"([\d,]+)\s+bài đánh giá", r"([\d,]+)\s+reviews"]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1).replace(",", ""))
        return None
    
    def extract_breakdown(self, soup):
        data = {}
        breakdown_section = soup.select_one("div.Review-travelerCell--right")

        if not breakdown_section:
            return data

        # Lấy từng cặp <li> tương ứng với từng tiêu chí
        for li in breakdown_section.select("li"):
            try:
                label = li.select_one("span.ikLOWN")
                score = li.select_one("span.bfKWaL, span.kRWALb")  # Có 2 loại class
                if label and score:
                    key = label.text.strip().lower().replace(" ", "_")
                    value = float(score.text.strip())
                    data[key] = value
            except Exception:
                continue

        return data

    def crawl(self, url):
        print(f"🌐 Crawling: {url}")
        try:
            soup = self.get_soup(url)
            text = soup.get_text(separator="\n")

            resort = self.extract_resort_name(url)
            rating = self.extract_rating(text)
            total_reviews = self.extract_total_reviews(text)
            breakdown = self.extract_breakdown(soup)

            return {
                "resort": resort,
                "url": url,
                "source": self.source,
                "rating": rating,
                "total_reviews": total_reviews,
                "scores": breakdown
            }

        except Exception as e:
            logger.error(f"[{self.source.upper()}] Lỗi khi crawl {url}: {str(e)}", exc_info=True)
            return {"url": url, "error": str(e)}
        finally:
            self.close()

    # @staticmethod
    # def _crawl_url_static(url):
    #     crawler = AgodaCrawler()
    #     result = crawler.crawl(url)
    #     return result

    # def crawl_all_parallel(self, processes=4):
    #     with Pool(processes=processes) as pool:
    #         results = pool.map(self._crawl_url_static, self.urls)
    #     return results
