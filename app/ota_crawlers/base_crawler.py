from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import random
import undetected_chromedriver as uc
from time import sleep
import time

class BaseCrawler:
    def __init__(self, urls=None, use_selenium=False, headers=None):
        self.urls = urls or []
        self.use_selenium = use_selenium
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9"
        }
        self.driver = None  # Initialize driver as None

    def create_driver(self):
        if self.use_selenium and not self.driver:
            # Khởi tạo driver nếu dùng selenium
            # chrome_options = Options()
            # # chrome_options.add_argument("--headless")  # Chạy ở chế độ headles
            # # chrome_options.add_argument("--headless=new")
            # # chrome_options.add_argument("--no-sandbox")
            # # chrome_options.add_argument("--disable-gpu")
            # chrome_options.add_argument("--disable-dev-shm-usage")
            # chrome_options.add_argument("--disable-software-rasterizer")
            # chrome_options.add_argument("--disable-extensions")
            # user_agents = [
            #     "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.3",
            # ]
            # chrome_options.add_argument(f"user-agent={random.choice(user_agents)}")
            # chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Prevent detection of WebDriver
            # chrome_options.add_argument("--start-maximized")  # Open browser maximized
            # self.driver = webdriver.Chrome(options=chrome_options)

            # Tạo trình duyệt ẩn danh
            options = uc.ChromeOptions()
            prefs = {"profile.managed_default_content_settings.images": 2}  # Disable images
            options.add_experimental_option("prefs", prefs)
            options.headless = False  # Bật trình duyệt (nên bật để tránh bị phát hiện)

            # Khởi tạo trình duyệt
            self.driver = uc.Chrome(options=options)

    def get_html(self, url):  
        if self.use_selenium:
            self.driver.get(url)
            self.driver.implicitly_wait(10)
            html = self.driver.page_source
        else:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            html = response.text
        return html

    def get_soup(self, url):
        html = self.get_html(url)
        return BeautifulSoup(html, "html.parser")

    def crawl(self, url):
        raise NotImplementedError("Subclasses must implement the crawl() method.")

    def close(self):
        if self.driver:
            try:
                self.driver.quit()  # Gracefully quit the driver
            except Exception as e:
                print(f"Error while closing driver: {e}")
            finally:
                self.driver = None  # Ensure driver is set to None after quitting
