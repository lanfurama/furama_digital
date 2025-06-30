# app/ota_crawlers/base_crawler.py
class BaseCrawler:
    def __init__(self, urls):
        self.urls = urls  # Danh sách các URL cần cào

    def crawl(self, url):
        raise NotImplementedError("The crawl method should be implemented by subclasses.")
