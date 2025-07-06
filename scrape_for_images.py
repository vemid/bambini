import requests
from bs4 import BeautifulSoup
import json
import csv
import os
import time
import re
from urllib.parse import urljoin, urlparse
from pathlib import Path


class BambiniScraper:
    def __init__(self, base_url="https://www.bambini.rs", delay=2):
        self.base_url = base_url
        self.delay = delay  # Pauza između zahteva u sekundama
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.products = []

    def get_page(self, url):
        """Dobija sadržaj stranice sa error handling-om"""
        try:
            print(f"Fetching: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.delay)  # Poštovanje servera
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def extract_product_links(self, html):
        """Izvlači linkove do proizvoda sa stranice"""
        soup = BeautifulSoup(html, 'html.parser')
        product_links = []

        # Traži linkove do proizvoda - možda treba prilagoditi selektor
        product_elements = soup.find_all('a', href=re.compile(r'/proizvod/'))

        for element in product_elements:
            href = element.get('href')
            if href:
                full_url = urljoin(self.base_url, href)
                product_links.append(full_url)

        return list(set(product_links))  # Uklanja duplikate

    def extract_product_details(self, product_url):
        """Izvlači detalje proizvoda sa stranice proizvoda"""
        html = self.get_page(product_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        product = {
            'url': product_url,
            'title': '',
            'sku': '',
            'price': '',
            'description': '',
            'images': [],
            'categories': []
        }

        # Naslov proizvoda
        title_elem = soup.find(['h1', 'h2'], class_=re.compile(r'product|title'))
        if not title_elem:
            title_elem = soup.find('h1')
        if title_elem:
            product['title'] = title_elem.get_text(strip=True)

        # SKU - može biti u različitim mestima
        sku_patterns = [
            soup.find(text=re.compile(r'SKU|šifra|kod', re.I)),
            soup.find('span', class_=re.compile(r'sku|code')),
            soup.find('meta', {'property': 'product:retailer_item_id'})
        ]

        for pattern in sku_patterns:
            if pattern:
                if hasattr(pattern, 'get'):
                    sku = pattern.get('content', '')
                else:
                    sku_text = str(pattern)
                    sku_match = re.search(r'[A-Z0-9-]+', sku_text)
                    sku = sku_match.group() if sku_match else ''
                if sku:
                    product['sku'] = sku
                    break

        # Cena
        price_elem = soup.find(['span', 'div'], class_=re.compile(r'price|cena'))
        if not price_elem:
            price_elem = soup.find(text=re.compile(r'\d+[.,]\d+.*RSD'))
        if price_elem:
            product['price'] = price_elem.get_text(strip=True) if hasattr(price_elem, 'get_text') else str(
                price_elem).strip()

        # Slike proizvoda
        img_elements = soup.find_all('img')
        for img in img_elements:
            src = img.get('src') or img.get('data-src')
            if src and any(keyword in src.lower() for keyword in ['product', 'upload', 'wp-content']):
                full_img_url = urljoin(self.base_url, src)
                product['images'].append(full_img_url)

        # Opis
        desc_elem = soup.find(['div', 'p'], class_=re.compile(r'description|content'))
        if desc_elem:
            product['description'] = desc_elem.get_text(strip=True)

        return product

    def get_all_products_from_page(self, page_url):
        """Dobija sve proizvode sa jedne stranice kataloga"""
        html = self.get_page(page_url)
        if not html:
            return []

        product_links = self.extract_product_links(html)
        products = []

        for link in product_links:
            product = self.extract_product_details(link)
            if product:
                products.append(product)
                print(f"Scraped: {product['title'][:50]}...")

        return products

    def find_pagination_urls(self, html):
        """Pronalazi stranice za paginaciju"""
        soup = BeautifulSoup(html, 'html.parser')
        pagination_urls = []

        # Traži pagination linkove
        pagination_elements = soup.find_all('a', href=re.compile(r'page|strana'))
        for elem in pagination_elements:
            href = elem.get('href')
            if href:
                pagination_urls.append(urljoin(self.base_url, href))

        return pagination_urls

    def scrape_all_products(self, start_url="/prodavnica/"):
        """Glavna funkcija za scraping svih proizvoda"""
        full_start_url = urljoin(self.base_url, start_url)

        # Počinje sa prvom stranicom
        html = self.get_page(full_start_url)
        if not html:
            print("Nije moguće dobiti početnu stranicu")
            return

        # Dobija proizvode sa prve stranice
        self.products.extend(self.get_all_products_from_page(full_start_url))

        # Pronalazi dodatne stranice
        pagination_urls = self.find_pagination_urls(html)

        for page_url in pagination_urls:
            if page_url not in [full_start_url]:  # Izbegava duplikate
                products_from_page = self.get_all_products_from_page(page_url)
                self.products.extend(products_from_page)

    def download_images(self, download_folder="downloaded_images"):
        """Download-uje sve slike proizvoda"""
        Path(download_folder).mkdir(exist_ok=True)

        for product in self.products:
            if not product['images']:
                continue

            # Kreira folder za proizvod
            safe_name = re.sub(r'[^\w\s-]', '', product['title']).strip()[:50]
            product_folder = Path(download_folder) / safe_name
            product_folder.mkdir(exist_ok=True)

            for i, img_url in enumerate(product['images']):
                try:
                    response = self.session.get(img_url, timeout=10)
                    response.raise_for_status()

                    # Određuje ekstenziju
                    parsed_url = urlparse(img_url)
                    ext = Path(parsed_url.path).suffix or '.jpg'

                    # Čuva sliku
                    filename = product_folder / f"image_{i + 1}{ext}"
                    with open(filename, 'wb') as f:
                        f.write(response.content)

                    print(f"Downloaded: {filename}")
                    time.sleep(0.5)  # Kratka pauza između download-a

                except Exception as e:
                    print(f"Error downloading {img_url}: {e}")

    def save_to_csv(self, filename="bambini_products.csv"):
        """Čuva podatke u CSV fajl"""
        if not self.products:
            print("Nema podataka za čuvanje")
            return

        fieldnames = ['title', 'sku', 'price', 'url', 'description', 'images', 'categories']

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for product in self.products:
                # Konvertuje liste u stringove
                product_copy = product.copy()
                product_copy['images'] = '; '.join(product['images'])
                product_copy['categories'] = '; '.join(product['categories'])
                writer.writerow(product_copy)

        print(f"Podaci sačuvani u {filename}")

    def save_to_json(self, filename="bambini_products.json"):
        """Čuva podatke u JSON fajl"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.products, f, ensure_ascii=False, indent=2)
        print(f"Podaci sačuvani u {filename}")


# Kako se koristi:
if __name__ == "__main__":
    # Kreira scraper sa 2 sekunde pauze između zahteva
    scraper = BambiniScraper(delay=2)

    print("Početak scraping-a...")
    scraper.scrape_all_products()

    print(f"Ukupno proizvoda: {len(scraper.products)}")

    # Čuva podatke
    scraper.save_to_csv()
    scraper.save_to_json()

    # Download-uje slike (opciono - može potrajati dugo)
    choice = input("Da li želite da download-ujete slike? (y/n): ")
    if choice.lower() == 'y':
        scraper.download_images()

    print("Scraping završen!")