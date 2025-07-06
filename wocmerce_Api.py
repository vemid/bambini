import requests
import json
import csv
from requests.auth import HTTPBasicAuth
import time


class WooCommerceExtractor:
    def __init__(self, site_url, consumer_key, consumer_secret):
        self.site_url = site_url.rstrip('/')
        self.api_url = f"{self.site_url}/wp-json/wc/v3"
        self.auth = HTTPBasicAuth(consumer_key, consumer_secret)
        self.products = []

    def get_products(self, per_page=100):
        """Dobija sve proizvode preko API-ja"""
        page = 1

        while True:
            print(f"Dobijam stranicu {page}...")

            url = f"{self.api_url}/products"
            params = {
                'per_page': per_page,
                'page': page,
                'status': 'publish'
            }

            try:
                response = requests.get(url, auth=self.auth, params=params)
                response.raise_for_status()

                products = response.json()

                if not products:
                    break

                for product in products:
                    product_data = self.extract_product_data(product)
                    self.products.append(product_data)
                    print(f"Processed: {product_data['name'][:50]}...")

                page += 1
                time.sleep(0.5)  # Kratka pauza

            except requests.RequestException as e:
                print(f"Error: {e}")
                break

        print(f"Ukupno proizvoda: {len(self.products)}")

    def extract_product_data(self, product):
        """Izvlači potrebne podatke iz proizvoda"""
        # Glavna slika
        main_image = ""
        if product.get('images') and len(product['images']) > 0:
            main_image = product['images'][0]['src']

        # Sve slike
        all_images = []
        for img in product.get('images', []):
            all_images.append(img['src'])

        # Varijante proizvoda (ako postoje)
        variations = []
        if product.get('type') == 'variable':
            variations = self.get_product_variations(product['id'])

        return {
            'id': product['id'],
            'name': product['name'],
            'sku': product['sku'],
            'type': product['type'],
            'status': product['status'],
            'price': product['price'],
            'regular_price': product['regular_price'],
            'sale_price': product['sale_price'],
            'stock_quantity': product['stock_quantity'],
            'main_image': main_image,
            'all_images': '; '.join(all_images),
            'categories': '; '.join([cat['name'] for cat in product.get('categories', [])]),
            'tags': '; '.join([tag['name'] for tag in product.get('tags', [])]),
            'description': product.get('description', ''),
            'short_description': product.get('short_description', ''),
            'permalink': product['permalink'],
            'variations': variations
        }

    def get_product_variations(self, product_id):
        """Dobija varijante proizvoda"""
        url = f"{self.api_url}/products/{product_id}/variations"

        try:
            response = requests.get(url, auth=self.auth)
            response.raise_for_status()
            variations = response.json()

            variation_data = []
            for var in variations:
                variation_data.append({
                    'id': var['id'],
                    'sku': var['sku'],
                    'price': var['price'],
                    'attributes': var['attributes'],
                    'image': var['image']['src'] if var.get('image') else ''
                })

            return variation_data

        except requests.RequestException as e:
            print(f"Error getting variations for product {product_id}: {e}")
            return []

    def save_to_csv(self, filename="woocommerce_products.csv"):
        """Čuva podatke u CSV"""
        if not self.products:
            print("Nema podataka za čuvanje")
            return

        fieldnames = [
            'id', 'name', 'sku', 'type', 'status', 'price', 'regular_price',
            'sale_price', 'stock_quantity', 'main_image', 'all_images',
            'categories', 'tags', 'description', 'short_description', 'permalink'
        ]

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for product in self.products:
                # Uklanja varijante iz osnovnog CSV-ja
                product_copy = {k: v for k, v in product.items() if k != 'variations'}
                writer.writerow(product_copy)

        print(f"Osnovni podaci sačuvani u {filename}")

        # Poseban CSV za varijante
        self.save_variations_to_csv()

    def save_variations_to_csv(self, filename="woocommerce_variations.csv"):
        """Čuva varijante u poseban CSV"""
        all_variations = []

        for product in self.products:
            if product['variations']:
                for variation in product['variations']:
                    variation['parent_id'] = product['id']
                    variation['parent_name'] = product['name']
                    variation['parent_sku'] = product['sku']
                    all_variations.append(variation)

        if not all_variations:
            return

        fieldnames = [
            'parent_id', 'parent_name', 'parent_sku', 'id', 'sku',
            'price', 'attributes', 'image'
        ]

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for variation in all_variations:
                # Konvertuje attributes u string
                if isinstance(variation['attributes'], list):
                    variation['attributes'] = '; '.join([
                        f"{attr['name']}: {attr['option']}"
                        for attr in variation['attributes']
                    ])
                writer.writerow(variation)

        print(f"Varijante sačuvane u {filename}")

    def save_to_json(self, filename="woocommerce_products.json"):
        """Čuva sve podatke u JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.products, f, ensure_ascii=False, indent=2)
        print(f"JSON podaci sačuvani u {filename}")

    def download_images(self, download_folder="product_images"):
        """Download-uje sve slike"""
        import os
        from urllib.parse import urlparse

        os.makedirs(download_folder, exist_ok=True)

        for product in self.products:
            if not product['all_images']:
                continue

            # Kreira folder za proizvod
            safe_name = "".join(c for c in product['name'] if c.isalnum() or c in (' ', '-', '_')).rstrip()[:50]
            product_folder = os.path.join(download_folder, f"{product['id']}_{safe_name}")
            os.makedirs(product_folder, exist_ok=True)

            images = product['all_images'].split('; ')
            for i, img_url in enumerate(images):
                if not img_url:
                    continue

                try:
                    response = requests.get(img_url, timeout=10)
                    response.raise_for_status()

                    # Određuje ekstenziju
                    parsed_url = urlparse(img_url)
                    ext = os.path.splitext(parsed_url.path)[1] or '.jpg'

                    filename = os.path.join(product_folder, f"image_{i + 1}{ext}")
                    with open(filename, 'wb') as f:
                        f.write(response.content)

                    print(f"Downloaded: {filename}")
                    time.sleep(0.3)

                except Exception as e:
                    print(f"Error downloading {img_url}: {e}")


# Kako se koristi:
if __name__ == "__main__":
    # **KONFIGURISANJE**
    SITE_URL = "https://www.bambini.rs"  # Vaš sajt
    CONSUMER_KEY = "ck_01ea7b877c98f1bc1c1e112cc245fbf0551d5b1d"  # Iz WooCommerce Settings
    CONSUMER_SECRET = "cs_b6fd943cb7ee49f87b8983056eda419783570b22"  # Iz WooCommerce Settings

    # Kreiranje extractor-a
    extractor = WooCommerceExtractor(SITE_URL, CONSUMER_KEY, CONSUMER_SECRET)

    # Dobijanje svih proizvoda
    print("Dobijam proizvode iz WooCommerce...")
    extractor.get_products(per_page=50)  # 50 proizvoda po stranici

    # Čuvanje podataka
    extractor.save_to_csv()
    extractor.save_to_json()

    # Download slika (opciono)
    choice = input("Da li želite da download-ujete slike? (y/n): ")
    if choice.lower() == 'y':
        extractor.download_images()

    print("Gotovo!")