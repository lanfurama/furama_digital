# reviews/crawlers/hotelscombined.py

import re
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from time import sleep
from .base_crawler import BaseCrawler

logger = logging.getLogger(__name__)

class AgodaCrawler(BaseCrawler):
    def __init__(self):
        self.source = "agoda"
        self.urls = [
            "https://www.agoda.com/furama-resort-danang/hotel/da-nang-vn.html",
            "https://www.agoda.com/aoa-hotel-apartment-da-nang-by-thg/hotel/all/da-nang-vn.html?"
        ]

    def _init_driver(self):
        options = Options()
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36")
        options.add_argument("start-maximized")
        options.add_experimental_option("detach", True)
        options.add_argument("--headless")  # Bật nếu chạy background
        return webdriver.Chrome(options=options)

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
        driver = self._init_driver()
        try:
            driver.implicitly_wait(15)
            driver.get(url)

            html = driver.page_source
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
            logger.error(f"[{self.source.upper()}] Lỗi khi crawl {url}: {str(e)}", exc_info=True)
            return None  # hoặc raise e nếu muốn báo lỗi ở API
        finally:
            driver.quit()
