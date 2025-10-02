import json
import pandas as pd
from bs4 import BeautifulSoup
import requests
from datetime import datetime
import re
from selenium.common.exceptions import NoSuchElementException
import zendriver as zd
import asyncio
import os
from random import randint
import csv

root_url = "https://www.autovit.ro"
base_url = f"{root_url}/autoturisme"

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

file_path = os.path.join("data", "Autovit", "scraped", f"car_data_autovit_{timestamp}.csv")

async def scrape_data(n, file_path):
    fieldnames = ["title", "hp_displacement_desc", "price_str", "mileage", "fuel_type", "year"]

    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    #results = []
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        browser = await zd.start(
            sandbox=False,
            browser_args=[
            '--window-size=1920,1080',
            '--max_old_space_size=4096',  # Limit V8 heap to 4GB  
            '--memory-pressure-off',       # Disable memory pressure notifications  
            '--disable-background-timer-throttling',  
            '--disable-renderer-backgrounding',  
            '--disable-backgrounding-occluded-windows']
            )
        try:
            for i in range(1, n):
                url = f"{base_url}?page={i}"
                page = await browser.get(url)
                
                await page.wait_for_ready_state("complete")
                await asyncio.sleep(randint(2, 6))
                try:
                    consent = await page.find("Accept", best_match=True)
                    await consent.click()
                    print("Consent popup closed")
                except Exception as e:
                    #print(f"No consent popup found or error: {e}")
                    pass

                #page = await browser.get(url)
                await asyncio.sleep(randint(2, 5))
                await page.scroll_down(randint(50, 70), speed=randint(2000, 4000))
    
                try:  
                    listings = await page.select("div[data-testid='search-results']", timeout=15)  
                    car_cards = await listings.query_selector_all("article")  
                    print(f"Found {len(car_cards)} car cards")  
                except asyncio.TimeoutError:  
                    print("No listings found")  
                    continue 

                html = await page.evaluate('document.documentElement.outerHTML')
                
                if i == 1:  # Only save for first page
                    with open("debug_after_consent.html", "w", encoding="utf-8") as f:
                        f.write(html)
                
                await asyncio.sleep(randint(2, 5))  
                
                soup = BeautifulSoup(html, "html.parser")

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
                            #"mileage_fuel_year": listing.find_all("dd", attrs={"data-parameter": re.compile(r"^(mileage|fuel_type|year)$")})
                            "mileage": listing.find("dd", attrs={"data-parameter": "mileage"}).text.strip() if listing.find("dd", attrs={"data-parameter": "mileage"}) else None,
                            "fuel_type": listing.find("dd", attrs={"data-parameter": "fuel_type"}).text.strip() if listing.find("dd", attrs={"data-parameter": "fuel_type"}) else None,
                            "year": listing.find("dd", attrs={"data-parameter": "year"}).text.strip() if listing.find("dd", attrs={"data-parameter": "year"}) else None,
                        }
                        writer.writerow(data)
                        f.flush()
                        #results.append(data)
                    except NoSuchElementException as te:
                        print(f"NoSuchElementException (likely blocked) on page {i}: {te}")
                        continue
                    except AttributeError as ae:
                        print(f"AttributeError on page {i}: {ae}")
                        continue
                    except Exception as e:
                        print(f"Unknown error on page {i}: {e}")
                        continue
                
                await page.evaluate('window.stop()')  
                await page.evaluate('document.body.innerHTML = ""')  
                if i % 10 == 0:  # Every 10 pages, force garbage collection  
                    await page.evaluate('window.gc && window.gc()')
                # await page.close()
                await asyncio.sleep(randint(2, 3))  # wait between pages
        finally:
            await browser.stop()

    #return results


def clean_data(df_raw):
    cleaned = []

    with open(r"data\Autovit\autovit_brands.json", "r", encoding="utf-8") as f:
        brands_dict = json.load(f)
    brand_list = list(brands_dict.keys())

    # Escape regex special characters in brand names
    brand_pattern = "|".join(re.escape(b) for b in brand_list)
    for _, row in df_raw.iterrows():
        try:
            title = row["title"]

            # --- Brand & model ---
            brand_match = re.search(rf"\b({brand_pattern})\b", title)
            if not brand_match:
                continue
            listing_brand = brand_match.group(1)

            remaining_title = title[brand_match.end():].strip()
            models_sorted = sorted(brands_dict[listing_brand], key=len, reverse=True)
            model_pattern = "|".join(re.escape(m) for m in models_sorted)
            model_match = re.search(rf"\b({model_pattern})\b", remaining_title)
            listing_model = model_match.group(1) if model_match else None

            # --- Mileage, fuel, year ---
            if row["mileage"] and row["fuel_type"] and row["year"]:
                #mileage_str = row["mileage_fuel_year"][0].text.strip()
                mileage_str = row["mileage"].replace(" ", "").replace("km", "").strip()
                mileage = int(mileage_str)
                fuel = row["fuel_type"].strip()
                year = int(row["year"])
            else:
                mileage, fuel, year = None, None, None

            # --- Price ---
            price = None
            try:
                price = float(row["price_str"].replace(" ", "").replace(",", "."))
            except Exception:
                pass

            # --- Engine details ---
            displacement, power, desc = None, None, None
            try:
                details = [d.strip() for d in row["hp_displacement_desc"].split("•")]
                if len(details) == 3:
                    displacement_str, power_str, desc = details
                    displacement = int(displacement_str.split(" cm3")[0])
                    power = int(power_str.split(" CP")[0])
            except Exception:
                pass

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
            print(f"Error cleaning row {row.to_dict()}: {e}")
            continue

    return pd.DataFrame(cleaned)

async def main():
    file_path = os.path.join("data", "Autovit", "scraped", "raw", f"car_data_autovit_raw_{timestamp}.csv")
    await scrape_data(1000, file_path)
    #print(raw_data)
    df_raw = pd.read_csv(file_path)
    df = clean_data(df_raw)
    df.to_csv(file_path.replace("raw", "final").replace("car_data_autovit_raw", "car_data_autovit_cleaned"), index=False)
    #df.to_csv(file_path, index=False)
    
    print(df.head())
    print(df.dtypes)
    print(df.isnull().sum())
    print(df.describe())
    print(df.shape)

if __name__ == "__main__":
    asyncio.run(main())
