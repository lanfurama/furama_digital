# reviews/crawlers/booking.py

import re
from .base_crawler import BaseCrawler

class TripAdvisorCrawler(BaseCrawler):
    def __init__(self):
        urls = [
            "https://www.tripadvisor.com.vn/Hotel_Review-g298085-d302750-Reviews-Furama_Resort_Danang-Da_Nang.html",
        ]
        self.source = "tripadvisor"
        super().__init__(urls=urls, use_selenium=True)

    def extract_resort_name(self, soup):
        try:
            header_tag = soup.find('h2', class_=lambda x: x and 'pp-header__title' in x)
            if header_tag:
                return header_tag.get_text(strip=True)
            else:
                return "unknown"
        except Exception as e:
            print(f"Error fetching resort name: {e}")
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
            r"([\d,]+)\s+đánh giá"
            r"Based on\s+([\d,]+)\s+đánh giá",
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
            soup = self.get_soup(url)
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
        finally:
            self.close()
