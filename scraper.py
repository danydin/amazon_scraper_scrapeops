from dotenv import load_dotenv
import requests
import json, csv
from dataclasses import dataclass, field, fields, asdict
from bs4 import BeautifulSoup
import logging, os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
API_KEY_SECRET = os.getenv('API_KEY')

API_KEY = API_KEY_SECRET

@dataclass
class ProductData:
    name: str = ""
    title: str = ""
    url: str = ""
    is_ad: bool = False
    pricing_unit: str = ""
    price: float = None
    real_price: float = None
    rating: float = None

    def __post_init__(self):
        self.check_string_fields()
    
    def check_string_fields(self):
        for field in fields(self):
            #check string fields
            if isinstance(getattr(self, field.name), str):
                # if empty set default text
                if getattr(self, field.name) == "":
                    setattr(self, field.name, f"No {field.name}")
                    continue
                # Strip any trailing spaces, etc
                value = getattr(self, field.name)
                setattr(self, field.name, value.strip())

class DataPipeline:
    def __init__(self, csv_filename="", storage_queue_limit=50):
        self.names_seen = []
        self.storage_queue = []
        self.storage_queue_limit = storage_queue_limit
        self.csv_filename = csv_filename
        self.csv_file_open = False

    def save_to_csv(self):
        self.csv_file_open = True
        data_to_save = []
        data_to_save.extend(self.storage_queue)
        self.storage_queue.clear()
        if not data_to_save:
            return
        
        keys = [field.name for field in fields(data_to_save[0])]
        file_exists = os.path.isfile(self.csv_filename) and  os.path.getsize(self.csv_filename) > 0

        with open(self.csv_filename, mode="a", newline="", encoding="utf-8") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=keys)

            if not file_exists:
                writer.writeheader()


def search_products(product_name: str, page_number=1, retries=3):
    tries = 0
    success = False

    while tries < retries and not success:
        try:
            print("test")
            url = f"https://amazon.com/s?k={product_name}&page={page_number}"
            resp = requests.get(url)

            if resp.status_code == 200:
                logger.info("Successfully fetched page")

                soup = BeautifulSoup(resp.text, "html.parser")

                divs = soup.find_all("div")

                last_title = ""

                for div in divs:
                    parsable = True if div is not None else False
                    h2 = div.find("h2")
                    if h2 and h2.text.strip() and h2.text.strip() != last_title and parsable:
                        title = h2.text.strip()
                        a = h2.find("a")
                        product_url = a.get("href") if a else ""
                        ad_status = False
                        if "sspa" in product_url:
                            ad_status = True
                        asin = div.get("data-asin")
                        symbol_element = div.find("span", class_="a-price-symbol")
                        symbol_presence = symbol_element.text if symbol_element else None
                        if symbol_presence is not None:
                            pricing_unit = symbol_presence
                            prices = div.find_all("span",class_="a-offscreen")

                            rating_element = div.find("span", class_="a-icon-alt")
                            rating_present = rating_element.text[0:3] if rating_element else "0.0"
                            rating = float(rating_present)

                            price_present = prices[0].text.replace(pricing_unit, "").replace(",","")
                            price = float(prices[1].text.replace(pricing_unit,"").replace(",",""))

                            real_price = float(prices[1].text.replace(pricing_unit,"").replace(",",""))

                        if symbol_presence and rating_present and price_present:
                            product = {
                                "name": asin,
                                "title": title,
                                "url": product_url,
                                "is_ad": ad_status,
                                "pricing_unit": pricing_unit,
                                "price": price,
                                "real_price": real_price,
                                "rating": rating
                            }

                            print(product)

                        last_title = title
                        
                    else:
                        continue 
                success = True 
            
            else:
                raise Exception(f"Failed to fetch the page, {resp.status_code}, tries left: {retries - tries}")

        except Exception as e:
            logger.warning(f"Failed to fetch page, {e}")
            tries += 1

    if not success:
        logger.warning(f"Failed to scrape page, retries exceeded {retries}")

    print(f"Exited scrape_products for: {product_name}")

if __name__ == "__main__":
    PRODUCTS = ["phone"]
    MAX_RETRIES = 2

    for product in PRODUCTS:
        search_products(product, retries=MAX_RETRIES)