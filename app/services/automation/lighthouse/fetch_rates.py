import os
from datetime import datetime
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .config import EMAIL, PASSWORD, LOGIN_URL, RATES_URL_TEMPLATE
from app.services.excel_importer import import_excel_file


class LighthouseRateFetcher:
    def __init__(self, headless=True, download_dir=None):
        """
        Khởi tạo ChromeDriver với tùy chọn headless và thư mục tải file.
        """
        if download_dir is None:
            download_dir = os.path.abspath("downloads")

         # ⚙️ Tùy chọn trình duyệt
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--start-maximized")               # ✅ Maximize
        options.add_argument("--disable-blink-features=AutomationControlled")  # ✅ Chống phát hiện
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("prefs", {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })

        # ✅ Khởi tạo Chrome driver
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                  get: () => undefined
                })
            """
        })

        self.wait = WebDriverWait(self.driver, 15)

    def login(self):
        """
        Đăng nhập vào Lighthouse.
        """
        self.driver.get(LOGIN_URL)

        email_input = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"]')))
        email_input.send_keys(EMAIL)

        next_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="button"]')))
        next_btn.click()

        password_input = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"]')))
        password_input.send_keys(PASSWORD)

        login_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="button"]')))
        login_btn.click()

        self.wait.until(EC.url_contains("overview"))

    def fetch_rates(self, month="2025-07"):
        """
        Mở trang rates với month chỉ định, chọn "Selected Month", tải file và import.
        """
        url = RATES_URL_TEMPLATE.format(month=month)
        self.driver.get(url)
        sleep(5)

        try:
            trigger = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-ebd-id="ember12-trigger"]')))
            ActionChains(self.driver).move_to_element(trigger).click().perform()

            option = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'li[data-option-index="0.2"]')))
            ActionChains(self.driver).move_to_element(option).click().perform()

            download_dir = os.path.abspath("downloads")
            before_files = set(os.listdir(download_dir))
            timeout = 30
            start_time = datetime.now()

            while (datetime.now() - start_time).seconds < timeout:
                current_files = set(os.listdir(download_dir))
                new_files = current_files - before_files
                if new_files:
                    file_name = new_files.pop()
                    file_path = os.path.join(download_dir, file_name)

                    if not file_path.endswith('.crdownload') and os.path.exists(file_path):
                        sleep(2)
                        try:
                            data = import_excel_file(file_path)
                            os.remove(file_path)
                            return {"status": "success", "data": data}
                        except Exception as e:
                            return {"status": "import_error", "message": str(e)}
                sleep(1)
        except Exception as e:
            return {"status": "fetch_error", "message": str(e)}

        return {"status": "timeout", "message": "Không tìm thấy file sau khi export."}

    @staticmethod
    def generate_months_around_current(current_month=None, months_before=6, months_after=5):
        """
        Sinh danh sách tháng quanh tháng hiện tại: [YYYY-MM]
        """
        if current_month is None:
            current_month = datetime.today().replace(day=1)

        month_list = []
        for i in range(-months_before, months_after + 1):
            y = current_month.year + ((current_month.month - 1 + i) // 12)
            m = (current_month.month - 1 + i) % 12 + 1
            month_str = f"{y}-{m:02d}"
            month_list.append(month_str)

        return month_list

    def fetch_multiple_months_auto(self, months_before=2, months_after=1):
        """
        Lấy dữ liệu từ các tháng trước/sau so với tháng hiện tại.
        """
        month_list = self.generate_months_around_current(
            datetime.today().replace(day=1), months_before, months_after
        )
        results = []

        for month in month_list:
            print(f"▶️ Fetching rates for {month}...")
            result = self.fetch_rates(month=month)
            results.append((month, result['status']))

        return results

    def close(self):
        """
        Đóng trình duyệt.
        """
        self.driver.quit()
