# reviews/crawlers/naver.py

import re
from .base_crawler import BaseCrawler
from time import sleep
from urllib.parse import urlparse
from googletrans import Translator
import asyncio
from selenium.webdriver.common.by import By
import time


class NaverCrawler(BaseCrawler):
    def __init__(self):
        urls = [
            "https://hotels.naver.com/detail/hotels/N1048536?",
            "https://hotels.naver.com/detail/hotels/N5304673",
            "https://hotels.naver.com/detail/hotels/N1596536",
            "https://hotels.naver.com/detail/hotels/KYK9260634",
            "https://hotels.naver.com/detail/hotels/N1625353",
            "https://hotels.naver.com/detail/hotels/N2653626",
            "https://hotels.naver.com/detail/hotels/N2850754",
            "https://hotels.naver.com/detail/hotels/N3900229",
            "https://hotels.naver.com/detail/hotels/N2311667"
        ]
        self.source = "naver"
        super().__init__(urls=urls, use_selenium=True)

    def extract_resort_info(self, soup):        
        # Extract the title (Resort Name)
        title = soup.title.get_text() if soup.title else None
        
        # Extract the description (Resort Rating and Description)
        description = soup.find('meta', {'name': 'description'})
        if description and description.get('content'):
            rating = description.get('content').split('이용자 평가 ')[1].split('점')[0]  # Extract the rating
        else:
            rating = None

        return title, rating

    def extract_total_reviews(self, soup):
        # Tìm div có thuộc tính data-automation="bubbleReviewCount"
        element = soup.find("small", class_="KayakReview_sub__IFl55")
        if element:
            text = element.get_text(strip=True)  # "(6,422reviews)"
            match = re.search(r"\(?([\d,]+)", text)
            if match:
                return int(match.group(1).replace(",", ""))
        return None
    
    async def translate_text(self,text):
        translator = Translator()
        result = await translator.translate(text, src='ko', dest='en')
        return result.text

    def extract_scores(self, soup):
        valid_ratings_with_labels = {}
        rating_elements = soup.find_all('em', class_='RatingGraph_score__ebTMY')
        for element in rating_elements:
            try:
                score = float(element.text)
                if score > 0:
                    label = element.find_next_sibling('span').text  # Get the label (e.g., 직원 친절도)
                    translated_label = asyncio.run(self.translate_text(label)) if label else None
                    valid_ratings_with_labels[translated_label.lower()] = score
            except ValueError:
                continue  # Skip if the score is not a valid float
        return valid_ratings_with_labels
    
    def scroll_to_end_of_div(self, driver, div_class):
        # Tìm phần tử div với class cụ thể
        div_element = driver.find_element(By.CLASS_NAME, div_class)

        # Lấy chiều cao hiện tại của div
        last_height = driver.execute_script("return arguments[0].scrollHeight", div_element)

        while True:
            # Cuộn xuống trong div
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", div_element)
            time.sleep(2)  # Đợi 2 giây để trang tải thêm dữ liệu

            # Kiểm tra chiều cao mới của div
            new_height = driver.execute_script("return arguments[0].scrollHeight", div_element)
            if new_height == last_height:
                break  # Dừng lại nếu chiều cao không thay đổi (tức là đã cuộn hết div)
            last_height = new_height

    def crawl(self, url):
        print(f"🌐 Crawling: {url}")
        self.create_driver()  # Tạo driver nếu chưa có
        try:
            self.driver.get(url) 
            self.scroll_to_end_of_div(self.driver, "Layout_list_container__qcdsL")
            soup = self.get_soup(url)
            title, rating = self.extract_resort_info(soup)
            translated_title = asyncio.run(self.translate_text(title)) if title else None
            total_reviews = self.extract_total_reviews(soup)
            scores = self.extract_scores(soup)

            return {
                "resort": translated_title,
                "url": url,
                "source": self.source,
                "rating": rating,
                "total_reviews": total_reviews,
                "scores": scores
            }

        except Exception as e:
            return {"url": url, "error": str(e)}
        finally:
            self.close()
