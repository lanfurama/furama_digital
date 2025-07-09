from bs4 import BeautifulSoup
import time
import random
from .base_crawler import BaseCrawler
from time import sleep
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import re

class GoogleReviewCrawler(BaseCrawler):
    def __init__(self):
        urls = [
            "https://www.google.com/maps/place/Furama+Resort+Danang/@16.0399507,108.2484932,16z/data=!3m1!4b1!4m9!3m8!1s0x31420fdbc8cc38ef:0x9a6a3e31121225d2!5m2!4m1!1i2!8m2!3d16.0399456!4d108.2510681!16s%2Fg%2F1hc12jlwq?entry=ttu&g_ep=EgoyMDI1MDYzMC4wIKXMDSoASAFQAw%3D%3D"
        ]
        super().__init__(urls=urls, use_selenium=True)

    def extract_rating(self, soup):
        rating_candidates = soup.find_all("span", attrs={"aria-hidden": "true"})
        for span in rating_candidates:
            if re.match(r"^\d\.\d$", span.text.strip()):
                return span.text.strip()
                break
        else:
            return None
        
    def get_total_reviews(self, soup):
        review_tag = soup.find("span", attrs={"aria-label": re.compile(r"\d[\d,\.]* reviews")})
        if review_tag:
            reviews_match = re.search(r'([\d,\.]+)', review_tag['aria-label'])
            if reviews_match:
                # Loại bỏ dấu phẩy và dấu chấm
                review_str = reviews_match.group(1).replace(',', '').replace('.', '')
                return int(review_str)  # Chuyển thành số nguyên
        return None

    def crawl(self, url):
        self.create_driver() 
        sleep(10)
        try:
            html = self.get_html(url)
            with open("furama_maps_page.html", "w", encoding="utf-8") as f:
                f.write(html)   
            soup = self.get_soup(url)
            
            rating = self.extract_rating(soup)
            total_reviews = self.get_total_reviews(soup)
            return {
                "url": url,
                "source": "googlereview",
                "resort": "Furama Resort",
                "rating": rating,
                "total_reviews": total_reviews
            }
        except Exception as e:
            return {"url": url, "error": str(e)}

        finally:
            self.close()
