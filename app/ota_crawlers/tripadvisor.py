# reviews/crawlers/booking.py

import re
from .base_crawler import BaseCrawler
from time import sleep
from urllib.parse import urlparse

class TripAdvisorCrawler(BaseCrawler):
    def __init__(self):
        urls = [
            "https://www.tripadvisor.com/Hotel_Review-g298085-d302750-Reviews-Furama_Resort_Danang-Da_Nang.html",
            "https://www.tripadvisor.com/Hotel_Review-g27704560-d1823746-Reviews-TIA_Wellness_Resort-Ngu_Hanh_Son_Da_Nang.html",
            "https://www.tripadvisor.com/Hotel_Review-g298085-d1732187-Reviews-Pullman_Danang_Beach_Resort-Da_Nang.html",
            "https://www.tripadvisor.com/Hotel_Review-g298085-d6370235-Reviews-Premier_Village_Danang_Resort_Managed_by_Accor-Da_Nang.html",
            "https://www.tripadvisor.com/Hotel_Review-g27704560-d2179507-Reviews-Danang_Marriott_Resort_Spa-Ngu_Hanh_Son_Da_Nang.html",
            "https://www.tripadvisor.com/Hotel_Review-g298085-d2340470-Reviews-Hyatt_Regency_Danang_Resort_Spa-Da_Nang.html",
            "https://www.tripadvisor.com/Hotel_Review-g298085-d7617524-Reviews-Naman_Retreat-Da_Nang.html",
            "https://www.tripadvisor.com/Hotel_Review-g298085-d12404186-Reviews-Furama_Villas_Danang-Da_Nang.html",
            "https://www.tripadvisor.com/Hotel_Review-g298085-d13326393-Reviews-Sheraton_Grand_Danang_Resort_Convention_Center-Da_Nang.html",
            "https://www.tripadvisor.com/Hotel_Review-g26818864-d27775804-Reviews-Fusion_Resort_Villas_Da_Nang-Hoa_Hai_Da_Nang.html"
        ]
        self.source = "tripadvisor"
        super().__init__(urls=urls, use_selenium=True)

    def extract_resort_name(self, url):
        path = urlparse(url).path
        match = re.search(r'Reviews-([^-]+)', path)
        if match:
            name = match.group(1)
            name = name.replace('_', ' ').strip()
            return name

    def extract_rating(self, soup):
        try:
            rating_tag = soup.find(attrs={"data-automation": "bubbleRatingValue"})
            if rating_tag:
                text = rating_tag.get_text(strip=True)
                return float(text.replace(",", "."))
        except Exception as e:
            print(f"Error extracting rating: {e}")
        
        return None

    def extract_total_reviews(self, soup):
        # Tìm div có thuộc tính data-automation="bubbleReviewCount"
        review_div = soup.find("div", attrs={"data-automation": "bubbleReviewCount"})
        if review_div:
            text = review_div.get_text(strip=True)  # "(6,422reviews)"
            # Tìm số trong chuỗi có dạng "(6,422reviews)" hoặc "(6422reviews)"
            match = re.search(r"\(?([\d,]+)", text)
            if match:
                return int(match.group(1).replace(",", ""))
        return None

    def extract_breakdown(self, soup):
        data = {}
        blocks = soup.find_all("div", class_="jxnKb")  # Mỗi block chứa 1 tiêu chí

        for block in blocks:
            label_tag = block.find("div", class_="Ygqck")
            score_tag = block.find("div", class_="biGQs _P fiohW biKBZ navcl")

            if label_tag and score_tag:
                label = label_tag.get_text(strip=True).lower()
                # Chuyển "Sleep Quality" -> "sleep_quality"
                label = re.sub(r"\s+", "_", label)
                label = re.sub(r"[^\w_]", "", label)

                try:
                    score = float(score_tag.get_text(strip=True).replace(",", "."))
                    data[label] = score
                except ValueError:
                    continue

        return data

    def crawl(self, url):
        print(f"🌐 Crawling: {url}")
        self.create_driver()  # Tạo driver nếu chưa có
        if not self.driver:
            raise Exception("Selenium driver is not initialized.")
        try:
            soup = self.get_soup(url)
            text = soup.get_text(separator="\n")

            resort_name = self.extract_resort_name(url)
            rating = self.extract_rating(soup)
            total_reviews = self.extract_total_reviews(soup)
            breakdown = self.extract_breakdown(soup)

            return {
                "resort": resort_name,
                "url": url,
                "source": self.source,
                "rating": rating,
                "total_reviews": total_reviews,
                "scores": breakdown
            }

        except Exception as e:
            return {"url": url, "error": str(e)}
        finally:
            self.close()
