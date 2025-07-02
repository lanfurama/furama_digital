from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class BaseCrawler:
    def __init__(self, urls=None, use_selenium=False, headers=None):
        self.urls = urls or []
        self.use_selenium = use_selenium
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9"
        }

        # Setup selenium nếu cần
        if self.use_selenium:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0.0.0 Safari/537.36")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
            # Thêm capability vào options
            chrome_options.set_capability("goog:loggingPrefs", {
                "performance": "OFF",
                "browser": "SEVERE"
            })
            self.driver = webdriver.Chrome(options=chrome_options)

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
        # Nếu dùng selenium thì cần quit sau khi xong
        if self.use_selenium and hasattr(self, 'driver'):
            self.driver.quit()
