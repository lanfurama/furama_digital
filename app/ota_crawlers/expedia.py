# reviews/crawlers/expedia.py

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from .base_crawler import BaseCrawler
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

class ExpediaCrawler(BaseCrawler):
    def __init__(self):
        self.source = "expedia"
        urls = [
            "https://www.expedia.com/Da-Nang-Hotels-Furama-Resort-Danang.h526011.Hotel-Information",
            "https://www.expedia.com/Da-Nang-Hotels-TIA-Wellness-Resort-Spa-Inclusive.h3844044.Hotel-Information",
            "https://www.expedia.com/Da-Nang-Hotels-Pullman-Danang-Beach-Resort.h3520339.Hotel-Information",
            "https://www.expedia.com/Phu-Quoc-Hotels-Premier-Village-Phu-Quoc-Resort-Managed-By-AccorHotels.h22862139.Hotel-Information",
            "https://www.expedia.com/Da-Nang-Hotels-Danang-Marriott-Resort-Spa.h27825698.Hotel-Information",
            "https://www.expedia.com/Da-Nang-Hotels-Hyatt-Regency-Danang-Resort-And-Spa.h4624340.Hotel-Information",
            "https://www.expedia.com/Da-Nang-Hotels-Naman-Retreat.h9713657.Hotel-Information",
            "https://www.expedia.com/Da-Nang-Hotels-Furama-Villas-Danang.h8508851.Hotel-Information",
            "https://www.expedia.com/Da-Nang-Hotels-Sheraton-Grand-Danang-Resort.h21943289.Hotel-Information",
            "https://www.expedia.com/Da-Nang-Hotels-Fusion-Resort-Villas-Da-Nang.h99047995.Hotel-Information"
        ]
        super().__init__(urls=urls, use_selenium=True)

    def extract_resort_name(self, soup):
        h1_tag = soup.find('h1', class_='uitk-heading uitk-heading-3')
        if h1_tag:
            resort_name = h1_tag.get_text(strip=True)
            return resort_name
        else:   
            return "unknown"
        
    
    def extract_rating(self, soup):
        possible_tags = soup.find_all(string=re.compile(r"(\d+(?:\.\d+)?)\s*out of\s*10"))
        for tag in possible_tags:
            m = re.search(r"(\d+(?:\.\d+)?)\s*out of\s*10", tag)
            if m:
                try:
                    return m.group(1)
                except ValueError:
                    continue
        return None

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

        blocks = soup.select("div.uitk-layout-flex-flex-direction-column")
        for block in blocks:
            score_tag = block.select_one("h3[aria-label]")
            label_tag = block.select_one("div.uitk-text.uitk-type-300")

            if score_tag and label_tag:
                label = label_tag.text.strip().lower().replace(" ", "_")
                aria = score_tag.get("aria-label", "")
                match = re.search(r"(\d+(?:\.\d+)?)", aria)
                if match:
                    try:
                        score = float(match.group(1))
                        data[label] = score
                    except ValueError:
                        continue
        return data
    
    def scroll_until_reviews(self, max_scrolls=20, pause=0.5):
        for _ in range(max_scrolls):
            try:
                review_section = self.driver.find_element(By.CSS_SELECTOR, "section#Reviews")
                return review_section  # ✅ Đã tìm thấy
            except:
                self.driver.execute_script("window.scrollBy(0, window.innerHeight);")  # cuộn xuống 1 khung hình
                sleep(pause)
        return None  # ❌ Sau max_scrolls vẫn không thấy

    def crawl(self, url):
        print(f"🌐 Crawling: {url}")
        self.create_driver()  # Tạo driver nếu chưa có
        if not self.driver:
            raise Exception("Selenium driver is not initialized.")
        try:
            self.driver.get(url)
            sleep(1)

            review_section = self.scroll_until_reviews()
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", review_section)
            sleep(2)

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            text = soup.get_text(separator="\n")

            resort = self.extract_resort_name(soup)
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

