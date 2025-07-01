# reviews/crawlers/hotelscombined.py

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from .base_crawler import BaseCrawler

class HotelsCombinedCrawler(BaseCrawler):
    def __init__(self):
        self.source = "hotelscombined"
        self.headers = {"User-Agent": "Mozilla/5.0"}

        urls = [
            "https://www.hotelscombined.com/hotels/Furama-Resort-Danang,Da-Nang-p17850-h2259-details",
            "https://www.hotelscombined.com/hotels/Tia-Wellness-Resort,Spa-Inclusive,Da-Nang-p17850-h367310-details",
            "https://www.hotelscombined.com/hotels/Pullman-Danang-Beach-Resort,Da-Nang-p17850-h399727-details",
            "https://www.hotelscombined.com/hotels/Premier-Village-Danang-Resort,Managed-by-Accor,Da-Nang-p17850-h2069660-details",
            "https://www.hotelscombined.com/hotels/Danang-Marriott-Resort--Spa,Non-Nuoc-Beach-Villas,Da-Nang-p17850-h2733746-details",
            "https://www.hotelscombined.com/hotels/Hyatt-Regency-Danang-Resort-and-Spa,Da-Nang-p17850-h419224-details",
            "https://www.hotelscombined.com/hotels/Naman-Retreat,Da-Nang-p17850-h2230903-details",
            "https://www.hotelscombined.com/hotels/Sheraton-Grand-Danang-Beach-Resort--SPA,Da-Nang-p17850-h3602259-details",
            "https://www.hotelscombined.com/hotels/Fusion-Resort-and-Villas-Da-Nang,Da-Nang-p17850-h9260634-details"
        ]
        self.urls = urls

    def extract_resort_name(self, url):
        match = re.search(r'hotels/([^,]+)', url)
        if match:
            # Trích xuất tên resort và thay thế "_" bằng " " (dấu cách)
            resort_name = match.group(1).replace("-", " ").title()
            return resort_name
        else:
            return "unknown"

    def extract_rating(self, soup):
        div_tag = soup.find('div', attrs={'data-automation': 'bubbleRatingValue'})
        if div_tag:
            text = div_tag.get_text(strip=True)
            try:
                return float(text)
            except ValueError:
                return None
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
        blocks = soup.select("div.Utcy") 
        for block in blocks:
            label_elem = block.select_one(".Utcy-title")
            count_elem = block.select_one(".Utcy-count")
            if label_elem and count_elem:
                key = label_elem.text.strip().lower().replace(" ", "_")
                try:
                    count = int(count_elem.text.strip().replace(",", ""))
                    data[key] = count
                except:
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
