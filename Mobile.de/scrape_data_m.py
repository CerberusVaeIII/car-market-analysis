import json
import pandas as pd
from bs4 import BeautifulSoup
import requests
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import re
from selenium.common.exceptions import NoSuchElementException


options = Options()
#options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

root_url = "https://www.mobile.de/?lang=en"
base_url = "https://suchen.mobile.de/fahrzeuge/search.html?dam=false&isSearchRequest=true&ref=quickSearch&s=Car&vc=Car&lang=en"
placeholder_url = "https://suchen.mobile.de/fahrzeuge/search.html?dam=false&isSearchRequest=true&pageNumber=1&ref=srpNextPage&refId=b459a424-b9c7-2cbe-a77a-0256f462311b&s=Car&vc=Car"

def scrape_data(n):
    results = []
    for i in range(1, n):
        try:
            url = f"{base_url}&pageNumber={i}"
            driver.get(url)
            wait = WebDriverWait(driver, 10)
            print(f"Scraping page {i}: {url}")
            try:
                consent_btn = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept')]"))
                )
                consent_btn.click()
                print("Consent popup closed")
            except:
                print("No consent popup found")
            soup = BeautifulSoup(driver.page_source, "html.parser")

            listings = soup.find("div", class_="leHcX")
            if not listings:
                break
            else:
                results.append(listings.text.strip())
        except Exception as e:
            print(f"Error constructing URL for page {i}: {e}")
            continue

    return results

print(scrape_data(3))