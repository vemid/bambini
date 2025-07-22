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
        """Čita Excel fajl i vraća DataFrame - koristi samo sheet UPISATI"""
        try:
            # Eksplicitno čita sheet "UPISATI"
            df = pd.read_excel(excel_file_path, sheet_name="UPISATI")
            print(f"Učitano {len(df)} redova iz sheet-a 'UPISATI'")
            print(f"Kolone: {list(df.columns)}")
            return df
        except Exception as e:
            print(f"Greška pri čitanju Excel fajla (sheet UPISATI): {e}")
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

    def is_predefined_category_code(self, category_value):
        """Proverava da li je kategorija već definisana numerička šifra"""
        try:
            # Konvertuje u string i čisti whitespace
            category_str = str(category_value).strip()

            # Proverava da li je numerička vrednost (šifra)
            if category_str.isdigit() and len(category_str) == 4:
                # Proverava da li je u validnom opsegu šifara
                code = int(category_str)
                if (1000 <= code <= 1999) or (2000 <= code <= 2999) or (3000 <= code <= 3999):
                    print(f"Debug - prepoznata predefinisana šifra kategorije: {category_str}")
                    return True
            return False
        except:
            return False

    def get_category_code(self, category_value, product_name):
        """Dobija kod kategorije - prvo proverava da li je već definisan, zatim mapira"""

        # Prvo proverava da li je već numerička šifra
        if self.is_predefined_category_code(category_value):
            category_code = str(category_value).strip()

            # Izvlači pol iz šifre
            first_digit = int(category_code[0])
            if first_digit == 1:
                gender = 'M'
            elif first_digit == 2:
                gender = 'F'
            elif first_digit == 3:
                gender = 'U'
            else:
                gender = 'U'  # Default

            # Pokušava da mapira šifru na naziv kategorije
            category_name = self.map_code_to_category_name(category_code)

            print(f"Debug - koristi predefinisanu šifru: {category_code}, pol: {gender}, naziv: {category_name}")
            return category_code, gender, category_name

        # Ako nije predefinisana šifra, koristi postojeću logiku
        else:
            gender = self.map_gender_from_category(category_value)
            product_category = self.map_product_category(category_value, product_name)
            category_code = self.map_category_to_code(product_category, gender)

            print(
                f"Debug - mapirana kategorija: {category_value} -> {category_code}, pol: {gender}, naziv: {product_category}")
            return category_code, gender, product_category

    def map_code_to_category_name(self, category_code):
        """Mapira numeričku šifru nazad u naziv kategorije"""
        code_mapping = {
            # Muške kategorije (1xxx)
            '1001': 'TRENERKE',
            '1002': 'DUKSEVI',
            '1003': 'MAJICE',
            '1004': 'ŠORCEVI',
            '1005': 'PANTALONE',
            '1006': 'JAKNE',
            '1007': 'SETOVI',
            '1099': 'OSTALO',

            # Ženske kategorije (2xxx)
            '2001': 'TRENERKE',
            '2002': 'DUKSEVI',
            '2003': 'MAJICE',
            '2004': 'ŠORCEVI',
            '2005': 'PANTALONE',
            '2006': 'JAKNE',
            '2007': 'SETOVI',
            '2099': 'TORBE',

            # Unisex kategorije (3xxx)
            '3001': 'TRENERKE',
            '3002': 'DUKSEVI',
            '3003': 'MAJICE',
            '3004': 'ŠORCEVI',
            '3005': 'PANTALONE',
            '3006': 'JAKNE',
            '3007': 'SETOVI',
            '3099': 'OSTALO'
        }

        return code_mapping.get(category_code, 'OSTALO')
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
                'TORBE': '2099'
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
            'Jack & Jones Junior',
            'REEBOK',
            'MESSI',
            'CAVALLI Class'
        ]

        for brand in brand_patterns:
            if brand in name_upper:
                print(f"Debug - brend iz naziva: {brand}")
                return brand

        print(f"Debug - brend nije pronađen, koristi se GENERIC")
        return 'GENERIC'

    def safe_get_value(self, row, column_name, default_value=''):
        """Sigurno dohvata vrednost iz reda, vraća default ako kolona ne postoji"""
        try:
            if column_name in row.index:
                value = row.get(column_name, default_value)
                return value if pd.notna(value) else default_value
            else:
                return default_value
        except:
            return default_value

    def parse_packing_time(self, packing_time, packing_time_type):
        """Parsira vreme pakovanja u standardni format"""
        try:
            time_value = float(packing_time) if packing_time and pd.notna(packing_time) else 2
            time_type = str(packing_time_type).lower() if packing_time_type and pd.notna(packing_time_type) else 'dan'

            # Standardizuje tip vremena
            if time_type in ['dan', 'day', 'dani', 'days']:
                return f"{int(time_value)} dan{'a' if time_value > 1 else ''}"
            elif time_type in ['sat', 'hour', 'sati', 'hours']:
                return f"{int(time_value)} sat{'a' if time_value > 1 else ''}"
            elif time_type in ['mesec', 'month', 'meseci', 'months']:
                return f"{int(time_value)} mesec{'a' if time_value > 1 else ''}"
            else:
                return f"{int(time_value)} dan{'a' if time_value > 1 else ''}"
        except:
            return "2 dana"

    def group_products_by_sku(self, df):
        """Grupira proizvode po SKU i priprema strukturu za Remiks"""
        products_dict = {}

        for _, row in df.iterrows():
            sku = str(self.safe_get_value(row, 'SKU', '')).strip()
            if not sku:
                continue

            size = str(self.safe_get_value(row, 'SIZE', '')).strip()
            qty = int(self.safe_get_value(row, 'QTY', 0) or 0)

            if sku not in products_dict:
                # Kreiranje novog proizvoda
                category = str(self.safe_get_value(row, 'CATEGORY', ''))
                product_name = str(self.safe_get_value(row, 'NAME', ''))

                # NOVA LOGIKA - prvo proverava da li je kategorija već šifra
                category_code, gender, product_category = self.get_category_code(category, product_name)

                brand = self.extract_brand_from_name(self.safe_get_value(row, 'BRAND'), product_name)

                # Procesuira slike
                images_str = str(self.safe_get_value(row, 'IMAGES', ''))
                images = [img.strip() for img in images_str.split(',') if img.strip()]
                while len(images) < 4:
                    images.append('')

                # Dobija sve dostupne kolone
                ean = str(self.safe_get_value(row, 'EAN', ''))
                variation_type = str(self.safe_get_value(row, 'VARIATION', 'SIZE'))
                retail_price = float(self.safe_get_value(row, 'RETAIL_PRICE', 0) or 0)
                special_price = float(self.safe_get_value(row, 'SPECIAL_PRICE', 0) or retail_price)
                vat_symbol = str(self.safe_get_value(row, 'VAT_SYMBOL', 'Đ'))
                vat = float(self.safe_get_value(row, 'VAT', 20))
                weight = float(self.safe_get_value(row, 'WEIGHT', 0.2))

                # Novo - dodajemo packing time info
                packing_time = self.safe_get_value(row, 'PACKING_TIME', 2)
                packing_time_type = self.safe_get_value(row, 'PACKING_TIME_TYPE', 'Dan')
                packing_time_formatted = self.parse_packing_time(packing_time, packing_time_type)

                # Novo - dodajemo nove kolone
                unit_of_measure = str(self.safe_get_value(row, 'Jedinica mere', 'Kom'))
                importer_name = str(self.safe_get_value(row, 'Poslovno ime uvoznika', ''))
                manufacturer_name = str(self.safe_get_value(row, 'Poslovno ime proizvođača', ''))
                country_of_origin = str(self.safe_get_value(row, 'Zemlja proizvodnje', ''))

                # Opis može biti iz DESCRIPTION ili Opis kolone
                description = str(self.safe_get_value(row, 'DESCRIPTION', ''))
                if not description:
                    description = str(self.safe_get_value(row, 'Opis', ''))

                products_dict[sku] = {
                    'sku': sku,
                    'ean': ean,  # NOVO
                    'gender': gender,
                    'product_name': product_name.replace('š', 's').replace('ž', 'z').replace('č', 'c').replace('ć',
                                                                                                               'c'),
                    'stock': {},
                    'type': 'configurable' if str(
                        self.safe_get_value(row, 'TYPE', '')).lower() == 'configurabile' else 'simple',
                    'variation_type': variation_type,  # NOVO
                    'net_retail_price': retail_price,
                    'active': 1,
                    'brand': brand,
                    'category_code': category_code,
                    'product_category_name': product_category,
                    'product_variation': variation_type.lower() if variation_type else 'size',
                    'product_variations': [],
                    'sale_price': special_price,
                    'invoice_price': special_price * 0.8333 * 0.8,
                    'weight': str(weight),
                    'vat': str(vat),
                    'vat_symbol': vat_symbol,
                    'season': 'UNIVERZALNO',
                    'images': images[:4],
                    'description': description,
                    'product_descritption': description,

                    # NOVE KOLONE
                    'packing_time': str(packing_time),
                    'packing_time_type': str(packing_time_type),
                    'packing_time_formatted': packing_time_formatted,
                    'unit_of_measure': unit_of_measure,
                    'importer_name': importer_name,
                    'manufacturer_name': manufacturer_name,
                    'country_of_origin': country_of_origin,

                    # Dodatne info kolone
                    'original_category': str(category),  # Čuva originalnu kategoriju
                    'has_special_price': special_price > 0 and special_price != retail_price,
                    'price_discount_percent': round(((retail_price - special_price) / retail_price * 100),
                                                    2) if special_price > 0 and special_price != retail_price else 0,
                }

            # Dodavanje veličina i zaliha
            if size and size not in products_dict[sku]['product_variations']:
                products_dict[sku]['product_variations'].append(size)

            if size:
                warehouse_name = str(self.safe_get_value(row, 'WAREHOUSE', 'Bambini-10-GLAVNI MAGACIN'))
                if size not in products_dict[sku]['stock']:
                    products_dict[sku]['stock'][size] = {}
                products_dict[sku]['stock'][size][warehouse_name] = qty

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
            print(f"EAN: {sample.get('ean', 'N/A')}")
            print(f"Naziv: {sample['product_name'][:50]}...")
            print(f"Brend: {sample['brand']}")
            print(f"Originalna kategorija: {sample.get('original_category', 'N/A')}")
            print(f"Mapirana kategorija: {sample['product_category_name']} ({sample['category_code']})")
            print(f"Pol: {sample['gender']}")
            print(f"Veličine: {sample['product_variations']}")
            print(f"Stock: {sample['stock']}")
            print(f"Vreme pakovanja: {sample.get('packing_time_formatted', 'N/A')}")
            print(f"Zemlja proizvodnje: {sample.get('country_of_origin', 'N/A')}")
            print(f"Uvoznik: {sample.get('importer_name', 'N/A')}")

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

        # Analizira dostupne kolone
        available_columns = list(df.columns)
        print(f"Dostupne kolone: {available_columns}")

        # Broj jedinstvenih SKU
        unique_skus = df['SKU'].nunique()
        print(f"Jedinstvenih SKU: {unique_skus}")

        # Broj jedinstvenih brendova
        if 'BRAND' in df.columns:
            unique_brands = df['BRAND'].nunique()
            print(f"Jedinstvenih brendova: {unique_brands}")

        # Broj jedinstvenih kategorija
        if 'CATEGORY' in df.columns:
            unique_categories = df['CATEGORY'].nunique()
            print(f"Jedinstvenih kategorija: {unique_categories}")

        # Statistike o veličinama
        if 'SIZE' in df.columns:
            unique_sizes = df['SIZE'].nunique()
            print(f"Jedinstvenih veličina: {unique_sizes}")

        # Ukupne zalihe
        if 'QTY' in df.columns:
            total_qty = df['QTY'].sum()
            print(f"Ukupne zalihe: {total_qty}")

        # Analiza novih kolona
        print(f"\n=== ANALIZA DODATNIH KOLONA ===")

        # EAN kolona
        if 'EAN' in df.columns:
            ean_coverage = df['EAN'].notna().sum()
            print(f"EAN kodovi popunjeni: {ean_coverage}/{len(df)} ({(ean_coverage / len(df) * 100):.1f}%)")

        # Zemlja proizvodnje
        if 'Zemlja proizvodnje' in df.columns:
            country_coverage = df['Zemlja proizvodnje'].notna().sum()
            unique_countries = df['Zemlja proizvodnje'].nunique()
            print(
                f"Zemlja proizvodnje popunjena: {country_coverage}/{len(df)} ({(country_coverage / len(df) * 100):.1f}%)")
            print(f"Broj različitih zemalja: {unique_countries}")
            if unique_countries > 0:
                print(f"Zemlje: {list(df['Zemlja proizvodnje'].dropna().unique())}")

        # Uvoznik
        if 'Poslovno ime uvoznika' in df.columns:
            importer_coverage = df['Poslovno ime uvoznika'].notna().sum()
            unique_importers = df['Poslovno ime uvoznika'].nunique()
            print(f"Uvoznik popunjen: {importer_coverage}/{len(df)} ({(importer_coverage / len(df) * 100):.1f}%)")
            print(f"Broj različitih uvoznika: {unique_importers}")

        # Vreme pakovanja
        if 'PACKING_TIME' in df.columns:
            packing_coverage = df['PACKING_TIME'].notna().sum()
            avg_packing_time = df['PACKING_TIME'].mean()
            print(
                f"Vreme pakovanja popunjeno: {packing_coverage}/{len(df)} ({(packing_coverage / len(df) * 100):.1f}%)")
            print(f"Prosečno vreme pakovanja: {avg_packing_time:.1f}")

        # Jedinica mere
        if 'Jedinica mere' in df.columns:
            unit_coverage = df['Jedinica mere'].notna().sum()
            unique_units = df['Jedinica mere'].nunique()
            print(f"Jedinica mere popunjena: {unit_coverage}/{len(df)} ({(unit_coverage / len(df) * 100):.1f}%)")
            if unique_units > 0:
                print(f"Jedinice mere: {list(df['Jedinica mere'].dropna().unique())}")

        print(f"\n=== ANALIZA KATEGORIJA ===")

        if 'CATEGORY' in df.columns:
            print(f"\nPrimeri kategorija iz Excel-a:")

            # Grupiše kategorije po tipu
            predefined_codes = []
            text_categories = []

            unique_categories = df['CATEGORY'].dropna().unique()

            for cat in unique_categories[:10]:  # Prikazuje prvih 10
                if self.is_predefined_category_code(cat):
                    predefined_codes.append(str(cat))
                else:
                    text_categories.append(str(cat))

            print(f"Predefinisane šifre kategorija ({len(predefined_codes)}):")
            for code in predefined_codes:
                category_name = self.map_code_to_category_name(code)
                print(f"  • {code} → {category_name}")

            print(f"\nTekstovne kategorije koje treba mapirati ({len(text_categories)}):")
            for cat in text_categories:
                # Test mapiranja
                test_code, test_gender, test_name = self.get_category_code(cat, "test product")
                print(f"  • '{cat}' → {test_code} ({test_name}, {test_gender})")

        print(f"\n=== PRIMER PROIZVODA SA KATEGORIJAMA ===")
        for sku in df['SKU'].unique()[:3]:
            sku_data = df[df['SKU'] == sku]
            category = sku_data['CATEGORY'].iloc[0] if 'CATEGORY' in df.columns else 'N/A'
            name = sku_data['NAME'].iloc[0] if 'NAME' in df.columns else 'N/A'

            # Testira mapiranje kategorije
            if category != 'N/A':
                mapped_code, mapped_gender, mapped_name = self.get_category_code(category, name)
                print(f"  {sku}: '{category}' → {mapped_code} ({mapped_name}, {mapped_gender})")
            else:
                print(f"  {sku}: Nema kategoriju")

    def compare_with_original_implementation(self, excel_file_path=None):
        """Poredi originalne i nove kolone"""
        print("=== POREĐENJE SA ORIGINALNOM IMPLEMENTACIJOM ===")

        if excel_file_path is None:
            excel_file_path = self.select_excel_file()
            if not excel_file_path:
                return

        df = self.read_excel_file(excel_file_path)
        if df is None:
            return

        # Kolone koje je originalna skripta koristila
        original_columns = [
            'SKU', 'SIZE', 'QTY', 'CATEGORY', 'NAME', 'TYPE',
            'RETAIL_PRICE', 'SPECIAL_PRICE', 'BRAND', 'IMAGES',
            'DESCRIPTION', 'WAREHOUSE', 'WEIGHT', 'VAT', 'VAT_SYMBOL'
        ]

        # Nove kolone koje dodajemo
        new_columns = [
            'EAN', 'VARIATION', 'PACKING_TIME', 'PACKING_TIME_TYPE',
            'Jedinica mere', 'Poslovno ime uvoznika', 'Poslovno ime proizvođača',
            'Zemlja proizvodnje', 'Opis'
        ]

        available_columns = list(df.columns)

        print(f"\nKOLONE KOJE JE ORIGINALNA SKRIPTA KORISTILA:")
        for col in original_columns:
            status = "✓" if col in available_columns else "✗"
            print(f"  {status} {col}")

        print(f"\nNOVE KOLONE KOJE DODAJEMO:")
        for col in new_columns:
            status = "✓" if col in available_columns else "✗"
            coverage = ""
            if col in available_columns:
                filled = df[col].notna().sum()
                total = len(df)
                coverage = f" ({filled}/{total} = {filled / total * 100:.1f}% popunjeno)"
            print(f"  {status} {col}{coverage}")

        print(f"\nKOLONE KOJE POSTOJE ALI SE NE KORISTE:")
        unused_columns = [col for col in available_columns if col not in original_columns and col not in new_columns]
        for col in unused_columns:
            print(f"  • {col}")

        # Generiše primer JSON-a sa svim podacima
        if len(df) > 0:
            print(f"\n=== PRIMER KOMPLETNOG JSON OBJEKTA ===")
            products_array = self.group_products_by_sku(df.head(1))  # Samo prvi proizvod
            if products_array:
                sample_product = products_array[0]
                print(json.dumps(sample_product, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # Kreiranje argument parser-a
    parser = argparse.ArgumentParser(description='Excel to Remiks Sync Script - Improved Version')
    parser.add_argument('--file', '-f', type=str, help='Putanja do Excel fajla')
    parser.add_argument('--sync', '-s', action='store_true', help='Pokreni sinhronizaciju direktno')
    parser.add_argument('--analyze', '-a', action='store_true', help='Analiziraj Excel fajl')
    parser.add_argument('--compare', '-c', action='store_true', help='Poredi sa originalnom implementacijom')

    args = parser.parse_args()

    # Kreiranje sync objekta
    sync = ExcelToRemiks()

    # Ako su prosledeni argumenti
    if args.file or args.sync or args.analyze or args.compare:
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
        elif args.compare:
            print(f"Poređenje implementacije za fajl: {excel_file}")
            sync.compare_with_original_implementation(excel_file)
        else:
            # Ako je samo specificiran fajl bez akcije, pokreni sync
            print(f"Pokretanje sinhronizacije sa fajlom: {excel_file}")
            sync.run_sync(excel_file)
    else:
        # Interaktivni meni ako nema argumenata
        print("=== EXCEL TO REMIKS SYNC - IMPROVED VERSION ===")
        print("1. Analiziraj Excel fajl")
        print("2. Pokreni sinhronizaciju iz Excel fajla")
        print("3. Poredi sa originalnom implementacijom")
        print("4. Exit")

        choice = input("\nIzaberite opciju (1-4): ").strip()

        if choice == "1":
            # Analiza Excel fajla - automatski traži u podaci folderu
            sync.analyze_excel_file()

        elif choice == "2":
            # Sinhronizacija iz Excel fajla - automatski traži u podaci folderu
            sync.run_sync()

        elif choice == "3":
            # Poređenje implementacija
            sync.compare_with_original_implementation()

        elif choice == "4":
            print("Izlaz...")

        else:
            print("Nevalidna opcija. Izlaz...")