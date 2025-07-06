from datetime import datetime
import requests
import json
from dotenv import load_dotenv
import os
from requests.auth import HTTPBasicAuth
import pandas as pd
import argparse
import sys

load_dotenv()


class ExcelToRemiks:
    def __init__(self):
        # Remiks API kredencijali
        self.remiks_api_key = os.getenv('remiks_api_key')
        self.remiks_username = os.getenv('remiks_username')
        self.remiks_password = os.getenv('remiks_password')
        self.remiks_url_login = os.getenv('remiks_url_login')
        self.remiks_url_product = os.getenv('remiks_url_product')

    def read_excel_file(self, excel_file_path):
        """Čita Excel fajl i vraća DataFrame"""
        try:
            # Pokušava sa prvim sheet-om
            df = pd.read_excel(excel_file_path, sheet_name=0)
            print(f"Učitano {len(df)} redova iz Excel fajla")
            print(f"Kolone: {list(df.columns)}")
            return df
        except Exception as e:
            print(f"Greška pri čitanju Excel fajla: {e}")
            return None

    def map_gender_from_category(self, category):
        """Mapira pol na osnovu kategorije"""
        category_lower = category.lower() if category else ""

        print(f"Debug - kategorija za mapiranje pola: {category}")

        if any(term in category_lower for term in ['dečaci', 'decaci', 'dečiji', 'deciji', 'boys']):
            return 'M'  # Muško
        elif any(term in category_lower for term in ['devojčice', 'devojcice', 'devojčice', 'girls']):
            return 'F'  # Žensko
        elif any(term in category_lower for term in ['unisex', 'baby', 'bebe', 'novorođenče']):
            return 'U'  # Unisex
        else:
            return 'U'  # Default unisex

    def map_product_category(self, category, product_name):
        """Mapira kategoriju na osnovu kategorije iz Excel-a i naziva proizvoda"""
        category_lower = category.lower() if category else ""
        product_name_lower = product_name.lower() if product_name else ""

        print(f"Debug - kategorija: {category}, naziv: {product_name}")

        # Mapiranje na osnovu kategorije iz Excel-a (prioritet)
        if any(term in category_lower for term in ['šorc', 'sorc', 'bermude', 'shorts']):
            return 'ŠORCEVI'
        elif any(term in category_lower for term in ['majica', 't-shirt', 'tshirt']):
            return 'MAJICE'
        elif any(term in category_lower for term in ['duks', 'hoodie', 'džemper', 'dzemper']):
            return 'DUKSEVI'
        elif any(term in category_lower for term in ['pantalone', 'pants', 'farmerke']):
            return 'PANTALONE'
        elif any(term in category_lower for term in ['jakna', 'jacket']):
            return 'JAKNE'
        elif any(term in category_lower for term in ['trenerk', 'komplet', 'set']):
            return 'TRENERKE'
        elif any(term in category_lower for term in ['set', 'komplet']):
            return 'SETOVI'

        # Ako nije pronađeno u kategoriji, traži u nazivu proizvoda
        elif any(term in product_name_lower for term in ['šorc', 'sorc', 'shorts', 'bermude']):
            return 'ŠORCEVI'
        elif any(term in product_name_lower for term in ['majica', 't-shirt', 'tshirt']):
            return 'MAJICE'
        elif any(term in product_name_lower for term in ['duks', 'hoodie', 'džemper', 'dzemper']):
            return 'DUKSEVI'
        elif any(term in product_name_lower for term in ['pantalone', 'pants', 'farmerke']):
            return 'PANTALONE'
        elif any(term in product_name_lower for term in ['jakna', 'jacket']):
            return 'JAKNE'
        elif any(term in product_name_lower for term in ['trenerk', 'komplet']):
            return 'TRENERKE'
        elif any(term in product_name_lower for term in ['set', 'komplet']):
            return 'SETOVI'

        print(f"Debug - kategorija nije prepoznata, koristi se OSTALO")
        return 'OSTALO'  # Default kategorija

    def map_category_to_code(self, category_name, gender):
        """Mapira kategoriju i pol u numerički kod - ista logika kao u originalnoj skripti"""
        category_mapping = {
            # Muške kategorije (1xxx)
            'M': {
                'TRENERKE': '1001',
                'DUKSEVI': '1002',
                'MAJICE': '1003',
                'ŠORCEVI': '1004',
                'PANTALONE': '1005',
                'JAKNE': '1006',
                'SETOVI': '1007',
                'OSTALO': '1099'
            },
            # Ženske kategorije (2xxx)
            'F': {
                'TRENERKE': '2001',
                'DUKSEVI': '2002',
                'MAJICE': '2003',
                'ŠORCEVI': '2004',
                'PANTALONE': '2005',
                'JAKNE': '2006',
                'SETOVI': '2007',
                'OSTALO': '2099'
            },
            # Unisex kategorije (3xxx)
            'U': {
                'TRENERKE': '3001',
                'DUKSEVI': '3002',
                'MAJICE': '3003',
                'ŠORCEVI': '3004',
                'PANTALONE': '3005',
                'JAKNE': '3006',
                'SETOVI': '3007',
                'OSTALO': '3099'
            }
        }

        code = category_mapping.get(gender, {}).get(category_name, '9999')
        print(f"Debug - mapiranje kategorije: {category_name} + {gender} -> {code}")
        return code

    def extract_brand_from_name(self, brand_column, product_name):
        """Izvlači brend iz kolone BRAND ili naziva proizvoda"""
        if brand_column and str(brand_column).strip():
            brand = str(brand_column).strip().upper()
            print(f"Debug - brend iz kolone: {brand}")
            return brand

        # Ako nema brenda u koloni, pokušava iz naziva
        name_upper = product_name.upper() if product_name else ""

        brand_patterns = [
            'JACK & JONES',
            'REEBOK',
            'MESSI',
            'VINGINO'
        ]

        for brand in brand_patterns:
            if brand in name_upper:
                print(f"Debug - brend iz naziva: {brand}")
                return brand

        print(f"Debug - brend nije pronađen, koristi se GENERIC")
        return 'GENERIC'

    def group_products_by_sku(self, df):
        """Grupira proizvode po SKU i priprema strukturu za Remiks"""
        products_dict = {}

        for _, row in df.iterrows():
            sku = str(row.get('SKU', '')).strip()
            if not sku:
                continue

            size = str(row.get('SIZE', '')).strip()
            qty = int(row.get('QTY', 0) or 0)

            if sku not in products_dict:
                # Kreiranje novog proizvoda
                category = str(row.get('CATEGORY', ''))
                product_name = str(row.get('NAME', ''))

                gender = self.map_gender_from_category(category)
                product_category = self.map_product_category(category, product_name)
                category_code = self.map_category_to_code(product_category, gender)
                brand = self.extract_brand_from_name(row.get('BRAND'), product_name)

                # Procesuira slike
                images_str = str(row.get('IMAGES', ''))
                images = [img.strip() for img in images_str.split(',') if img.strip()]
                while len(images) < 4:
                    images.append('')

                products_dict[sku] = {
                    'sku': sku,
                    'gender': gender,
                    'product_name': product_name.replace('š', 's').replace('ž', 'z').replace('č', 'c').replace('ć',
                                                                                                               'c'),
                    'stock': {},
                    'type': 'configurable' if str(row.get('TYPE', '')).lower() == 'configurabile' else 'simple',
                    'net_retail_price': float(row.get('RETAIL_PRICE', 0) or 0),
                    'active': 1,  # Assume all products are active
                    'brand': brand,
                    'category_code': category_code,
                    'product_category_name': product_category,
                    'product_variation': 'size' if size else 'none',
                    'product_variations': [],
                    'sale_price': float(row.get('SPECIAL_PRICE', 0) or row.get('RETAIL_PRICE', 0) or 0),
                    'invoice_price': float(row.get('RETAIL_PRICE', 0) or 0) * 0.8333 * 0.82,
                    'weight': str(row.get('WEIGHT', 0.2)),
                    'vat': str(row.get('VAT', 20)),
                    'vat symbol': str(row.get('VAT_SYMBOL', 'Đ')),
                    'season': 'UNIVERZALNO',  # Default season
                    'images': images[:4],
                    'description': str(row.get('DESCRIPTION', '')),
                }

            # Dodavanje veličina i zaliha
            if size and size not in products_dict[sku]['product_variations']:
                products_dict[sku]['product_variations'].append(size)

            if size:
                warehouse_name = str(row.get('WAREHOUSE', '10-GLAVNI MAGACIN'))
                products_dict[sku]['stock'][size] = {warehouse_name: qty}

        return list(products_dict.values())

    def prepare_remiks_data(self, excel_file_path):
        """Priprema podatke iz Excel fajla za slanje na Remiks"""
        df = self.read_excel_file(excel_file_path)
        if df is None:
            return [], []

        # Grupira proizvode po SKU
        products_array = self.group_products_by_sku(df)
        product_skus = [product['sku'] for product in products_array]

        print(f"Pripremljeno {len(products_array)} proizvoda za slanje")

        return products_array, product_skus

    def get_jwt_token(self):
        """Dobija JWT token od remiks servisa - ista logika kao originalna skripta"""
        payload = json.dumps({
            "username": self.remiks_username,
            "password": self.remiks_password
        })
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'ApiKey {self.remiks_api_key}',
        }

        try:
            response = requests.request("GET", self.remiks_url_login, headers=headers, data=payload)
            if response.status_code == 200:
                data = response.json()
                token = data.get('token')
                return token
            else:
                print("Failed to get JWT token:", response.text)
                return None
        except Exception as e:
            print("Error:", e)
            return None

    def send_request_to_remiks(self, payload, token):
        """Šalje podatke na remiks servis - ista logika kao originalna skripta"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        }

        send_data = json.dumps(payload)

        try:
            response = requests.request("POST", self.remiks_url_product, headers=headers, data=send_data)
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                print(f"Greška pri slanju na remiks: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print("Error:", e)
            return None

    def log_errors(self, response_json):
        """Loguje greške u fajl - ista logika kao originalna skripta"""
        if response_json and response_json.get('errors', []):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            error_log_path = os.getenv('error_log', 'remiks_errors.log')
            with open(error_log_path, 'a') as log_file:
                for error in response_json['errors']:
                    log_file.write(f"{timestamp}: {error}\n")

    def save_json_payload(self, payload):
        """Čuva JSON payload u fajl - ista logika kao originalna skripta"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(script_dir, f'payload_excel_to_remiks_{timestamp}.json')

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)

            print(f"JSON payload sačuvan u {filename}")
        except Exception as e:
            print(f"Greška pri čuvanju JSON payload-a: {e}")

    def run_sync(self, excel_file_path=None):
        """Glavna funkcija za pokretanje sinhronizacije iz Excel fajla"""
        print("Pokretanje Excel -> Remiks sinhronizacije...")

        if excel_file_path is None:
            excel_file_path = self.select_excel_file()
            if not excel_file_path:
                return

        # Proverava da li fajl postoji
        if not os.path.exists(excel_file_path):
            print(f"Excel fajl nije pronađen: {excel_file_path}")
            return

        # Priprema podatke
        payload, product_skus = self.prepare_remiks_data(excel_file_path)

        if not payload:
            print("Nema proizvoda za sinhronizaciju")
            return

        print(f"Pripremljeno {len(payload)} proizvoda za slanje")

        # Prikazuje primer proizvoda
        if payload:
            sample = payload[0]
            print(f"\nPrimer pripremljenog proizvoda:")
            print(f"SKU: {sample['sku']}")
            print(f"Naziv: {sample['product_name'][:50]}...")
            print(f"Brend: {sample['brand']}")
            print(f"Kategorija: {sample['product_category_name']} ({sample['category_code']})")
            print(f"Veličine: {sample['product_variations']}")
            print(f"Stock: {sample['stock']}")

        # Čuva payload
        self.save_json_payload(payload)

        # Dobija JWT token
        jwt_token = self.get_jwt_token()
        if not jwt_token:
            print("Nije moguće dobiti JWT token")
            return

        # Šalje podatke na remiks
        response = self.send_request_to_remiks(payload, jwt_token)

        if response:
            if not response.get('errors', []):
                print("Uspešno poslano na remiks servis!")
            else:
                print("Remiks servis vratio greške:")
                self.log_errors(response)
                for error in response.get('errors', []):
                    print(f"  - {error}")
        else:
            print("Greška pri slanju na remiks servis")

    def find_excel_files_in_data_folder(self):
        """Pronalazi sve Excel fajlove u 'podaci' folderu"""
        data_folder = os.path.join(os.getcwd(), 'podaci')
        excel_files = []

        if os.path.exists(data_folder):
            for file in os.listdir(data_folder):
                if file.endswith(('.xlsx', '.xls')):
                    excel_files.append(os.path.join(data_folder, file))

        return excel_files

    def select_excel_file(self):
        """Omogućava korisniku da bira Excel fajl"""
        # Prvo traži u podaci folderu
        excel_files = self.find_excel_files_in_data_folder()

        if excel_files:
            print("\nPronadeni Excel fajlovi u 'podaci' folderu:")
            for i, file in enumerate(excel_files, 1):
                filename = os.path.basename(file)
                print(f"{i}. {filename}")

            print(f"{len(excel_files) + 1}. Unesite custom putanju")

            try:
                choice = int(input(f"\nIzaberite fajl (1-{len(excel_files) + 1}): "))
                if 1 <= choice <= len(excel_files):
                    return excel_files[choice - 1]
                elif choice == len(excel_files) + 1:
                    return input("Unesite putanju do Excel fajla: ").strip()
                else:
                    print("Nevalidan izbor")
                    return None
            except ValueError:
                print("Nevalidan unos")
                return None
        else:
            print("Nema Excel fajlova u 'podaci' folderu")
            return input("Unesite putanju do Excel fajla: ").strip()

    def analyze_excel_file(self, excel_file_path=None):
        """Analizira Excel fajl i prikazuje statistike"""
        print("=== ANALIZA EXCEL FAJLA ===")

        if excel_file_path is None:
            excel_file_path = self.select_excel_file()
            if not excel_file_path:
                return

        df = self.read_excel_file(excel_file_path)
        if df is None:
            return

        print(f"Ukupno redova: {len(df)}")
        print(f"Ukupno kolona: {len(df.columns)}")

        # Broj jedinstvenih SKU
        unique_skus = df['SKU'].nunique()
        print(f"Jedinstvenih SKU: {unique_skus}")

        # Broj jedinstvenih brendova
        unique_brands = df['BRAND'].nunique()
        print(f"Jedinstvenih brendova: {unique_brands}")

        # Broj jedinstvenih kategorija
        unique_categories = df['CATEGORY'].nunique()
        print(f"Jedinstvenih kategorija: {unique_categories}")

        # Statistike o veličinama
        unique_sizes = df['SIZE'].nunique()
        print(f"Jedinstvenih veličina: {unique_sizes}")

        # Ukupne zalihe
        total_qty = df['QTY'].sum()
        print(f"Ukupne zalihe: {total_qty}")

        # Prikaz prvih nekoliko proizvoda
        print(f"\nPrvih 5 SKU:")
        for sku in df['SKU'].unique()[:5]:
            sku_data = df[df['SKU'] == sku]
            sizes = list(sku_data['SIZE'].values)
            qtys = list(sku_data['QTY'].values)
            print(f"  {sku}: veličine {sizes}, zalihe {qtys}")


if __name__ == "__main__":
    # Kreiranje argument parser-a
    parser = argparse.ArgumentParser(description='Excel to Remiks Sync Script')
    parser.add_argument('--file', '-f', type=str, help='Putanja do Excel fajla')
    parser.add_argument('--sync', '-s', action='store_true', help='Pokreni sinhronizaciju direktno')
    parser.add_argument('--analyze', '-a', action='store_true', help='Analiziraj Excel fajl')

    args = parser.parse_args()

    # Kreiranje sync objekta
    sync = ExcelToRemiks()

    # Ako su prosledeni argumenti
    if args.file or args.sync or args.analyze:
        excel_file = args.file

        # Ako nije specificiran fajl, pokušava sa default putanjom
        if not excel_file:
            default_path = os.path.join('podaci', 'podaci.xlsx')
            if os.path.exists(default_path):
                excel_file = default_path
                print(f"Koristi se default fajl: {excel_file}")
            else:
                print(f"Default fajl {default_path} nije pronađen")
                sys.exit(1)

        # Proverava da li fajl postoji
        if not os.path.exists(excel_file):
            print(f"Fajl nije pronađen: {excel_file}")
            sys.exit(1)

        if args.sync:
            print(f"Pokretanje sinhronizacije sa fajlom: {excel_file}")
            sync.run_sync(excel_file)
        elif args.analyze:
            print(f"Analiza fajla: {excel_file}")
            sync.analyze_excel_file(excel_file)
        else:
            # Ako je samo specificiran fajl bez akcije, pokreni sync
            print(f"Pokretanje sinhronizacije sa fajlom: {excel_file}")
            sync.run_sync(excel_file)
    else:
        # Interaktivni meni ako nema argumenata
        print("=== EXCEL TO REMIKS SYNC ===")
        print("1. Analiziraj Excel fajl")
        print("2. Pokreni sinhronizaciju iz Excel fajla")
        print("3. Exit")

        choice = input("\nIzaberite opciju (1-3): ").strip()

        if choice == "1":
            # Analiza Excel fajla - automatski traži u podaci folderu
            sync.analyze_excel_file()

        elif choice == "2":
            # Sinhronizacija iz Excel fajla - automatski traži u podaci folderu
            sync.run_sync()

        elif choice == "3":
            print("Izlaz...")

        else:
            print("Nevalidna opcija. Izlaz...")