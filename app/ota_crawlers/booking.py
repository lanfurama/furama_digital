# reviews/crawlers/booking.py

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from .base_crawler import BaseCrawler

class BookingCrawler(BaseCrawler):
    def __init__(self):
        self.source = "booking"
        self.headers = {"User-Agent": "Mozilla/5.0"}

        urls = [
            "https://www.booking.com/hotel/vn/pullman-saigon-centre.html",
            "https://www.booking.com/hotel/vn/furama-resort-danang.html",
        ]
        self.urls = urls

    def extract_resort_name(self, url):
        match = re.search(r'/hotel/[^/]+/([^/.]+)(?:\.[a-z]{2})?\.html', url)
        if match:
            # Trích xuất tên resort và thay thế "_" bằng " " (dấu cách)
            resort_name = match.group(1).replace("-", " ").title()
            return resort_name
        else:
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
            r"Based on\s+([\d,]+)\s+verified guest reviews",
            r"([\d,]+)\s+verified guest reviews",
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
            html = requests.get(url, headers=self.headers, timeout=20).text
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
