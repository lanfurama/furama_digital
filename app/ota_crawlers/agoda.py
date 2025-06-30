# reviews/crawlers/hotelscombined.py

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from .base_crawler import BaseCrawler
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class AgodaCrawler(BaseCrawler):
    def __init__(self):
        self.source = "agoda"
        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.urls = [
            "https://www.agoda.com/furama-resort-danang/hotel/da-nang-vn.html",
            "https://www.agoda.com/aoa-hotel-apartment-da-nang-by-thg/hotel/all/da-nang-vn.html?"
        ]

         # Cấu hình Selenium để không mở giao diện trình duyệt
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=chrome_options)

    def extract_resort_name(self, url):
        match = re.search(r'agoda\.com/(?:vi-vn/)?([^/]+)/hotel/', url)
        if match:
            resort_name = match.group(1).replace("-", " ").title()
            return resort_name
        else:
            return "unknown"

    def extract_rating(self, text):
        match = re.search(r"(\d\.\d)\s*(?:/10|out of 10)?", text)
        return float(match.group(1)) if match else None

    def extract_total_reviews(self, text):
        for pattern in [
            r"([\d,]+)\s+bài đánh giá",
            r"([\d,]+)\s+reviews"
        ]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1).replace(",", ""))
        return None

    def extract_breakdown(self, soup):
        data = {}
        score_blocks = soup.select("div.Review-travelerCell--right")
        for block in score_blocks:
            label_elem = block.select_one(".sc-hKgILt")
            score_elem = block.select_one(".kkDVzi")
            if label_elem and score_elem:
                key = label_elem.text.strip().lower().replace(" ", "_")
                try:
                    score = float(score_elem.text.strip())
                    data[key] = score
                except:
                    continue
        return data

    def crawl(self, url):
        print(f"🌐 Crawling: {url}")
        try:
            # Sử dụng Selenium để tải trang và lấy nội dung
            self.driver.get(url)

            # Đợi trang tải đầy đủ (có thể cần điều chỉnh thời gian)
            self.driver.implicitly_wait(3)  # seconds

            # Lấy HTML của trang
            html = self.driver.page_source
            self.driver.quit()  # 🧹 Quan trọng: đóng driver đúng lúc
            soup = BeautifulSoup(html, "html.parser")
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
            return {"url": url, "error": str(e)}
        
    def __del__(self):
        if self.driver:
            self.driver.quit()

