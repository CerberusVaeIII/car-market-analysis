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
import zendriver as zd
import os
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
raw_file_path = os.path.join("data", "Mobile.de", "scraped", "raw", f"car_data_mobilede_raw_{timestamp}.csv")
final_file_path = os.path.join("data", "Mobile.de", "scraped", "final", f"car_data_mobilede_final_{timestamp}.csv")

options = Options()
# options.add_argument("--headless")
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
            print("Listings object found:", listings is not None)
            if not listings:
                break
            
            cars = listings.select("article")
            print("Number of cars found:", len(cars))

            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "leHcX")))
            for car in cars:
                try:
                    title_tag = car.select_one("span.eO87w")
                    price_tag = car.select_one("span.GYhxV")
                    info_tag = car.select_one("div.HaBLt")

                    if not title_tag:
                        print("Title not found")
                    if not price_tag:
                        print("Price not found")
                    if not info_tag:
                        print("Info block not found")

                    if title_tag and price_tag and info_tag:
                        data = {
                            "title": title_tag.text.strip(),
                            "price": price_tag.text.strip(),
                            "year_mileage_power_fuel": "".join(
                                 t for t in info_tag.strings if t.parent.name != "strong"
                            ).strip()
                        }
                        print("Added:", data)
                        results.append(data)
                    else:
                        print("Skipping due to missing data")

                except AttributeError:
                    continue
        except NoSuchElementException as te:
            print(f"NoSuchElementException (likely blocked) on page {i}: {te}")
            break
        except AttributeError as ae:
            print(f"AttributeError on page {i}: {ae}")
            break
        except Exception as e:
            print(f"Unknown error on page {i}: {e}")
            break
        time.sleep(2)

    return results

def clean_data(raw_input):
    cleaned = []
    for item in raw_input:
        try:
            title = item["title"]

            with open(r"Autovit\autovit_brands.json", "r", encoding="utf-8") as f:
                brands_dict = json.load(f)
            brand_list = list(brands_dict.keys())

            # Escape regex special characters in brand names
            brand_pattern = "|".join(re.escape(b) for b in brand_list)
            
            # Search for the brand anywhere in the title
            brand_match = re.search(rf"\b({brand_pattern})\b", title)
            if not brand_match:
                continue

            listing_brand = brand_match.group(1)

            # Remaining string after the brand
            remaining_title = title[brand_match.end():].strip()

            # Sort models by length descending to match longer names first
            models_sorted = sorted(brands_dict[listing_brand], key=len, reverse=True)
            model_pattern = "|".join(re.escape(m) for m in models_sorted)

            # Search for model as whole word in the remaining title
            model_match = re.search(rf"\b({model_pattern})\b", remaining_title)
            listing_model = model_match.group(1) if model_match else None

            if item["year_mileage_power_fuel"].startswith("• "):
                item["year_mileage_power_fuel"] = item["year_mileage_power_fuel"][2:]

            item["year_mileage_power_fuel"] = item["year_mileage_power_fuel"].replace("\xa0", " ")

            try:
                date, mileage_str, power_str, fuel_str = [data.strip() for data in item["year_mileage_power_fuel"].split(" • ") if data.strip()]
                year = int(date.split("/")[1].replace(" ", ""))
                mileage = int(mileage_str.split(" km")[0].replace(",", "").replace(" ", ""))
                power = int(power_str.split("(")[1].split(" hp")[0].replace(" ", ""))
                fuel = fuel_str.replace(" ", "")
            except ValueError:
                year, mileage, power, fuel = None, None, None, None
            price = float(item["price"].replace(" ", "").replace(",", "").replace("€", "").replace("¹", "").strip())
            cleaned.append({
                "brand": listing_brand,
                "model": listing_model,
                "full_title": title,
                "power_hp": power,
                "price_eur": price,
                "mileage_km": mileage,
                "fuel_type": fuel,
                "production_year": year
            })
        except Exception as e:
            print(f"Error cleaning item {item}: {e}")
            continue
    return cleaned

scraped = clean_data(scrape_data(300))

print(scraped)

df = pd.DataFrame(scraped)
df.to_csv(r"data\Mobile.de\car_data_mobilede.csv")