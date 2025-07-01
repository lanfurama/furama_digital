# reviews/crawlers/hotelscombined.py

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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

class ExpediaCrawler(BaseCrawler):
    def __init__(self):
        self.source = "expedia"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Connection": "keep-alive",
        }
        self.urls = [
            "https://www.expedia.com/Da-Nang-Hotels-Furama-Resort-Danang.h526011.Hotel-Information",
        ]

         # Cấu hình Selenium để không mở giao diện trình duyệt
        chrome_options = Options()
        # chrome_options.add_argument("--headless")
        # ✅ Chỉ định đường dẫn đến Cốc Cốc
        chrome_options.binary_location = "C:\\Program Files\\CocCoc\\Browser\\Application\\browser.exe"
        self.driver = webdriver.Chrome(options=chrome_options)

    def extract_resort_name(self, soup):
        h1_tag = soup.find('h1', class_='uitk-heading uitk-heading-3')
        if h1_tag:
            resort_name = h1_tag.get_text(strip=True)
            return resort_name
        else:   
            return "unknown"

    def extract_rating(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        div_tag = soup.find('div', class_='uitk-text uitk-type-900 uitk-text-default-theme')
        if div_tag:
            text = div_tag.get_text(strip=True)
            match = re.search(r"(\d\.\d)", text)
            return float(match.group(1)) if match else None
        else:
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
        self.driver.implicitly_wait(15)
        self.driver.get(url)

        while True:
                sleep(3)  # Đợi một chút để trang tải
                try:
                    review_button = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-stid="reviews-link"]'))
                    )
                    
                    # Scroll và click bằng ActionChains
                    actions = ActionChains(self.driver)
                    actions.move_to_element(review_button).pause(1).click().perform()
                    sleep(3)  # Đợi trang review tải

                    # Tìm container review
                    html = self.driver.page_source
                    # Lấy toàn bộ text trong div
                    soup = BeautifulSoup(html, "html.parser")
                    text = soup.get_text(separator="\n")

                    resort = self.extract_resort_name(soup)
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
                
                    self.driver.quit()

                except TimeoutException:
                    print("Không tìm thấy nút review trong thời gian cho phép.")
                except Exception as e:
                    print("Lỗi khi click nút review:", e)

            # Lấy HTML của trang
            # html = self.driver.page_source
        self.driver.quit() 
            # return html
        #     soup = BeautifulSoup(html, "html.parser")
        #     text = soup.get_text(separator="\n")

        #     resort = self.extract_resort_name(soup)
        #     rating = self.extract_rating(text)
        #     total_reviews = self.extract_total_reviews(text)
        #     breakdown = self.extract_breakdown(soup)

        #     return {
        #         "resort": resort,
        #         "url": url,
        #         "source": self.source,
        #         "rating": rating,
        #         "total_reviews": total_reviews,
        #         "scores": breakdown
        #     }
        
    def __del__(self):
        if self.driver:
            self.driver.quit()

