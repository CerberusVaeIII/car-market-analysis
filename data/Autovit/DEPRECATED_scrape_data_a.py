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
import undetected_chromedriver as uc
import os

options = Options() 
#options.add_argument("--headless") # run Chrome in background options.add_argument("--no-sandbox") 
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--no-sandbox")
service = Service(ChromeDriverManager().install()) 
driver = webdriver.Chrome(service=service, options=options)

root_url = "https://www.autovit.ro"
base_url = f"{root_url}/autoturisme"

file_path = "data/Autovit/scraped/car_data_autovit_progress.csv"


def scrape_data(n):
    results = []
    for i in range(1, n):
        try:
            url = f"{base_url}?page={i}"
            driver.get(url)
            wait = WebDriverWait(driver, 10)

            try:
                consent_btn = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept')]"))
                )
                consent_btn.click()
                print("Consent popup closed")
            except:
                print("No consent popup found")
            soup = BeautifulSoup(driver.page_source, "html.parser")

            listings = soup.find("div", attrs={"data-testid": "search-results"})
            if not listings:
                continue

            car_cards = listings.find_all("article")
            #print(car_cards)

            for listing in car_cards:
                try:
                    data = {
                        "title": listing.find("h2").text.strip(),
                        "hp_displacement_desc": listing.find("p", string=re.compile("CP")).text.strip(),
                        "price_str": listing.find("h3").text.strip(),
                        "mileage_fuel_year": listing.find_all("dd", attrs={"data-parameter": re.compile(r"^(mileage|fuel_type|year)$")})
                    }
                    results.append(data)
                except AttributeError:
                    continue
            
            if not os.path.exists(file_path):
                pd.DataFrame(clean_data(results)).to_csv(file_path, index=False)
            else:
                # Append without headers
                pd.DataFrame(clean_data(results)).to_csv(file_path, mode='a', header=False, index=False)
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

def clean_data(raw_data):
    cleaned = []
    for item in raw_data:
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

            # mileage, fuel, year
            print(item["mileage_fuel_year"])
            if len(item["mileage_fuel_year"]) == 3:
                mileage_str = item["mileage_fuel_year"][0].text.strip()
                fuel = item["mileage_fuel_year"][1].text.strip()
                year = int(item["mileage_fuel_year"][2].text.strip())
                mileage = int(mileage_str.split(" km")[0].replace(" ", ""))
            else:
                mileage, fuel, year = None, None, None

            # price
            price = float(item["price_str"].replace(" ", "").replace(",", "."))

            # engine details
            details = [d.strip() for d in item["hp_displacement_desc"].split("•")]
            if len(details) == 3:
                displacement_str, power_str, desc = details
                displacement = int(displacement_str.split(" cm3")[0])
                power = int(power_str.split(" CP")[0])
            else:
                displacement, power, desc = None, None, None

            cleaned.append({
                "brand": listing_brand,
                "model": listing_model,
                "full_title": title,
                "engine_displacement_cm3": displacement,
                "power_hp": power,
                "ad_description": desc,
                "price_eur": price,
                "mileage_km": mileage,
                "fuel_type": fuel,
                "production_year": year
            })
        except Exception as e:
            print(f"Error cleaning item {item}: {e}")
            continue
    return cleaned
df = pd.DataFrame(clean_data(scrape_data(2)))
df.to_csv(r"data\Autovit\car_data_autovit1111.csv")

driver.quit()

print(df.head())
print(df.dtypes)
print(df.isnull().sum())
print(df.describe())
print(df.shape)