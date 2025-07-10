from bs4 import BeautifulSoup
import time
import random
from .base_crawler import BaseCrawler
from time import sleep
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import re
from urllib.parse import unquote

class GoogleReviewCrawler(BaseCrawler):
    def __init__(self):
        urls = [
            "https://www.google.com/maps/place/Furama+Resort+Danang/@16.0399507,108.2484932,16z/data=!3m1!4b1!4m9!3m8!1s0x31420fdbc8cc38ef:0x9a6a3e31121225d2!5m2!4m1!1i2!8m2!3d16.0399456!4d108.2510681!16s%2Fg%2F1hc12jlwq?entry=ttu&g_ep=EgoyMDI1MDYzMC4wIKXMDSoASAFQAw%3D%3D",
            "https://www.google.com/maps/place/Furama+Villas+Danang/@16.0370365,108.2485747,17z/data=!3m1!4b1!4m9!3m8!1s0x31421742c2fd4ea1:0xbe5b6da59bfb421c!5m2!4m1!1i2!8m2!3d16.0370314!4d108.2511496!16s%2Fg%2F1tgj69jp?entry=ttu&g_ep=EgoyMDI1MDcwOC4wIKXMDSoASAFQAw%3D%3D",
            "https://www.google.com/maps/place/Caf%C3%A9+Indochine/@16.0402024,108.2512154,21z/data=!4m17!1m10!3m9!1s0x31421742c2fd4ea1:0xbe5b6da59bfb421c!2sFurama+Villas+Danang!5m2!4m1!1i2!8m2!3d16.0370314!4d108.2511496!16s%2Fg%2F1tgj69jp!3m5!1s0x314217efbb84bfb5:0xc25f9454366a4941!8m2!3d16.0402552!4d108.2512153!16s%2Fg%2F11h06z3km7?entry=ttu&g_ep=EgoyMDI1MDcwOC4wIKXMDSoASAFQAw%3D%3D"
        ]
        super().__init__(urls=urls, use_selenium=True)

    def extract_name(self, url):
        match = re.search(r"/maps/place/([^/@]+)", url)
        if match:
            raw_name = match.group(1)  
            place_name = unquote(raw_name).replace("+", " ")
            return place_name
        
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
        try:            
            soup = self.get_soup(url)
            sleep(4)
            
            name = self.extract_name(url)
            rating = self.extract_rating(soup)
            total_reviews = self.get_total_reviews(soup)
            return {
                "url": url,
                "source": "google",
                "resort": name,
                "rating": rating,
                "total_reviews": total_reviews,
                "scores": {}
            }
        except Exception as e:
            return {"url": url, "error": str(e)}

        finally:
            self.close()
