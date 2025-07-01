# reviews/crawlers/booking.py

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from .base_crawler import BaseCrawler
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class TripAdvisorCrawler(BaseCrawler):
    def __init__(self):
        self.source = "tripadvisor"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Connection": "keep-alive",
        }

        self.urls = [
            "https://www.tripadvisor.com.vn/Hotel_Review-g298085-d302750-Reviews-Furama_Resort_Danang-Da_Nang.html",
        ]
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=chrome_options)

    def extract_resort_name(self, url):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raise error nếu mã status không phải 200

            soup = BeautifulSoup(response.text, 'html.parser')
            header_tag = soup.find('h2', class_=lambda x: x and 'pp-header__title' in x)

            if header_tag:
                return header_tag.get_text(strip=True)
            else:
                return "unknown"
        except Exception as e:
            print(f"Error fetching resort name: {e}")
            return "unknown"

    def extract_rating(self, soup):
        possible_tags = soup.find_all(string=re.compile(r"Scored\s*[\d,.]+"))
        for tag in possible_tags:
            m = re.search(r"Scored\s*([\d.,]+)", tag)
            if m:
                try:
                    return float(m.group(1).replace(",", "."))
                except ValueError:
                    continue
        return None

    def extract_total_reviews(self, text):
        for pattern in [
            r"([\d,]+)\s+đánh giá"
            r"Based on\s+([\d,]+)\s+đánh giá",
            r"([\d,]+)\s+reviews"
        ]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1).replace(",", ""))
        return None

    def extract_breakdown(self, soup):
        data = {}
        blocks = soup.select('[data-testid="review-subscore"]')
        for block in blocks:
            label_tag = block.select_one("span.d96a4619c0")
            score_tag = block.select_one("div.f87e152973")
            if label_tag and score_tag:
                label = label_tag.text.strip().lower()
                label = re.sub(r"\s+", "_", label)
                label = re.sub(r"[^\w_]", "", label)
                try:
                    score = float(score_tag.text.strip().replace(",", "."))
                    data[label] = score
                except ValueError:
                    continue
        return data

    def crawl(self, url):
        print(f"🌐 Crawling: {url}")
        try:
            # html = requests.get(url, headers=self.headers, timeout=20).text
            # Sử dụng Selenium để tải trang và lấy nội dung
            self.driver.get(url)

            # Đợi trang tải đầy đủ (có thể cần điều chỉnh thời gian)
            self.driver.implicitly_wait(10)  # seconds
            html = self.driver.page_source
            self.driver.quit()  # 🧹 Quan trọng: đóng driver đúng lúc
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(separator="\n")

            resort = self.extract_resort_name(url)
            rating = self.extract_rating(soup)
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
            return {"url": url, "error": str(e)}
