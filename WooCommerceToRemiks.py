from datetime import datetime
import requests
import json
from dotenv import load_dotenv
import os
from requests.auth import HTTPBasicAuth
import pandas as pd
load_dotenv()


class WooCommerceToRemiks:
    def __init__(self):
        # WooCommerce API kredencijali
        self.wc_site_url = os.getenv('WC_SITE_URL', 'https://www.bambini.rs')
        self.wc_consumer_key = os.getenv('WC_CONSUMER_KEY')
        self.wc_consumer_secret = os.getenv('WC_CONSUMER_SECRET')
        self.wc_api_url = f"{self.wc_site_url.rstrip('/')}/wp-json/wc/v3"
        self.wc_auth = HTTPBasicAuth(self.wc_consumer_key, self.wc_consumer_secret)

        # Remiks API kredencijali
        self.remiks_api_key = os.getenv('remiks_api_key')
        self.remiks_username = os.getenv('remiks_username')
        self.remiks_password = os.getenv('remiks_password')
        self.remiks_url_login = os.getenv('remiks_url_login')
        self.remiks_url_product = os.getenv('remiks_url_product')

    def fetch_woocommerce_products(self):
        """Dobija sve proizvode iz WooCommerce-a"""
        all_products = []
        page = 1
        per_page = 100

        while True:
            print(f"Dobijam WooCommerce proizvode - stranica {page}...")

            url = f"{self.wc_api_url}/products"
            params = {
                'per_page': per_page,
                'page': page,
                'status': 'publish'
            }

            try:
                response = requests.get(url, auth=self.wc_auth, params=params)
                response.raise_for_status()

                products = response.json()

                if not products:
                    break

                all_products.extend(products)
                page += 1

            except requests.RequestException as e:
                print(f"Greška pri dobijanju proizvoda: {e}")
                break

        print(f"Ukupno dobijeno {len(all_products)} proizvoda iz WooCommerce-a")
        return all_products

    def fetch_product_variations(self, product_id):
        """Dobija varijante proizvoda"""
        url = f"{self.wc_api_url}/products/{product_id}/variations"

        try:
            response = requests.get(url, auth=self.wc_auth)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Greška pri dobijanju varijanti za proizvod {product_id}: {e}")
            return []

    def map_gender_from_categories(self, categories):
        """Mapira pol na osnovu kategorija - precizno za srpski"""
        # Kombinuje sve kategorije u jedan string
        all_categories = '; '.join([cat['name'] for cat in categories])
        category_text = all_categories.lower()

        print(f"Debug - kategorije: {all_categories}")

        if 'dečaci' in category_text or 'decaci' in category_text:
            return 'M'  # Muško
        elif 'devojčice' in category_text or 'devojcice' in category_text:
            return 'F'  # Žensko
        elif any(term in category_text for term in ['unisex', 'baby', 'bebe', 'novorođenče', 'novorodenche']):
            return 'U'  # Unisex
        else:
            return 'U'  # Default unisex

    def extract_brand_from_name(self, product_name):
        """Izvlači brend iz naziva proizvoda - precizno za bambini.rs"""
        name_upper = product_name.upper()

        print(f"Debug - naziv proizvoda: {product_name}")

        # Lista brendova sa tačnim formatom
        brand_patterns = [
            'JACK & JONES',
            'REEBOK',
            'MESSI',
            'VINGINO'
        ]

        # Traži brendove u redosledu (duži prvi)
        for brand in brand_patterns:
            if brand in name_upper:
                print(f"Debug - pronađen brend: {brand}")
                return brand

        print(f"Debug - brend nije pronađen, koristi se GENERIC")
        return 'GENERIC'  # Default brend

    def map_product_category(self, product_name, categories):
        """Mapira kategoriju na osnovu naziva proizvoda i kategorija"""
        product_name_lower = product_name.lower()
        all_categories = '; '.join([cat['name'] for cat in categories])
        categories_lower = all_categories.lower()

        print(f"Debug - kategorije za mapiranje: {all_categories}")
        print(f"Debug - naziv za mapiranje: {product_name}")

        # Mapiranje na osnovu naziva proizvoda (prioritet)
        if any(term in product_name_lower for term in ['set', 'komplet']):
            return 'SETOVI'
        elif any(term in product_name_lower for term in ['duks', 'hoodie', 'džemper', 'dzemper']):
            return 'DUKSEVI'
        elif any(term in product_name_lower for term in ['majica', 't-shirt', 'tshirt']):
            return 'MAJICE'
        elif any(term in product_name_lower for term in ['šorc', 'sorc', 'shorts', 'bermude']):
            return 'ŠORCEVI'
        elif any(term in product_name_lower for term in ['pantalone', 'pants', 'farmerke']):
            return 'PANTALONE'
        elif any(term in product_name_lower for term in ['jakna', 'jacket']):
            return 'JAKNE'
        elif any(term in product_name_lower for term in ['trenerk', 'komplet']):
            return 'TRENERKE'

        # Ako nije pronađeno u nazivu, traži u kategorijama
        if any(term in categories_lower for term in ['setovi', 'kompleti']):
            return 'SETOVI'
        elif any(term in categories_lower for term in ['duksevi', 'džemperi', 'dzemper']):
            return 'DUKSEVI'
        elif 'majice' in categories_lower:
            return 'MAJICE'
        elif any(term in categories_lower for term in ['šorcevi', 'sorcevi', 'bermude']):
            return 'ŠORCEVI'
        elif 'pantalone' in categories_lower:
            return 'PANTALONE'
        elif 'jakne' in categories_lower:
            return 'JAKNE'
        elif any(term in categories_lower for term in ['trenerke', 'kompleti']):
            return 'TRENERKE'

        print(f"Debug - kategorija nije prepoznata, koristi se OSTALO")
        return 'OSTALO'  # Default kategorija

    def map_category_to_code(self, category_name, gender):
        """Mapira kategoriju i pol u numerički kod"""
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

    def extract_size_from_variation_attributes(self, variation):
        """Izvlači veličinu iz atributa varijacije - format 'Veličina: 6' -> '6'"""
        for attribute in variation.get('attributes', []):
            attr_name = attribute.get('name', '').lower()
            attr_option = attribute.get('option', '')

            # Proverava da li je atribut veličina
            if any(size_term in attr_name for size_term in ['veličina', 'velicina', 'size']):
                # Čisti veličinu - uklanja sve što nije broj/slovo
                size_clean = attr_option.strip()
                print(f"Debug - pronađena veličina: '{attr_option}' -> '{size_clean}'")
                return size_clean

        return None

    def get_product_sizes_from_variations(self, variations):
        """Dobija sve veličine iz varijanti proizvoda"""
        sizes = []

        for variation in variations:
            size = self.extract_size_from_variation_attributes(variation)
            if size and size not in sizes:
                sizes.append(size)

        print(f"Debug - sve pronađene veličine: {sizes}")
        return sizes

    def get_stock_data_from_variations(self, variations):
        """Dobija podatke o stanju zaliha iz varijanti"""
        stock_data = {}

        for variation in variations:
            # Dobija veličinu pomoću nove funkcije
            size = self.extract_size_from_variation_attributes(variation)

            if size:
                stock_qty = variation.get('stock_quantity', 0) or 0
                # Simulira magacin (možete prilagoditi prema vašim potrebama)
                stock_data[size] = {
                    '10-GLAVNI MAGACIN': stock_qty
                }
                print(f"Debug - stock za veličinu {size}: {stock_qty}")

        return stock_data

    def extract_season_from_categories_or_tags(self, categories, tags):
        """Izvlači sezonu iz kategorija ili tagova"""
        all_terms = [cat['name'].lower() for cat in categories] + [tag['name'].lower() for tag in tags]

        if any('leto' in term or 'summer' in term or 'spring' in term or 'proleće' in term for term in all_terms):
            return 'LETO 2025'
        elif any('zima' in term or 'winter' in term or 'jesen' in term or 'autumn' in term for term in all_terms):
            return 'ZIMA 2025'
        else:
            return 'UNIVERZALNO'

    def prepare_remiks_data(self):
        """Priprema podatke za slanje na remiks servis"""
        wc_products = self.fetch_woocommerce_products()
        products_array = []
        product_skus = []

        for wc_product in wc_products:
            # Proverava da li proizvod ima SKU
            sku = wc_product.get('sku')
            if not sku:
                print(f"Proizvod {wc_product['name']} nema SKU - preskače se")
                continue

            product_skus.append(sku)

            # Dobija varijante ako je varijabilni proizvod
            variations = []
            product_sizes = []
            stock_data = {}

            if wc_product.get('type') == 'variable':
                variations = self.fetch_product_variations(wc_product['id'])
                product_sizes = self.get_product_sizes_from_variations(variations)
                stock_data = self.get_stock_data_from_variations(variations)
            else:
                # Jednostavan proizvod - pokušava da pronađe veličinu u atributima
                for attribute in wc_product.get('attributes', []):
                    if 'size' in attribute.get('name', '').lower():
                        product_sizes = attribute.get('options', [])
                        break

                # Stock za jednostavan proizvod
                if product_sizes:
                    stock_qty = wc_product.get('stock_quantity', 0) or 0
                    for size in product_sizes:
                        stock_data[size] = {'10-GLAVNI MAGACIN': stock_qty}

            # Mapira podatke
            categories = wc_product.get('categories', [])
            tags = wc_product.get('tags', [])

            # Mapiranje pomoću novih funkcija
            gender = self.map_gender_from_categories(categories)
            brand = self.extract_brand_from_name(wc_product['name'])
            product_category = self.map_product_category(wc_product['name'], categories)
            category_code = self.map_category_to_code(product_category, gender)

            # Dobija slike
            images = []
            for img in wc_product.get('images', []):
                images.append(img['src'])

            # Dodaje placeholder slike ako nema dovoljno
            while len(images) < 4:
                images.append('')

            # Formira finalni objekat
            product_info = {
                'sku': sku,
                'gender': gender,
                'product_name': wc_product['name'].replace('š', 's').replace('ž', 'z').replace('č', 'c').replace('ć',
                                                                                                                 'c'),
                'stock': stock_data,
                'type': 'configurable' if wc_product.get('type') == 'variable' else 'simple',
                'net_retail_price': float(wc_product.get('regular_price', 0) or wc_product.get('price', 0) or 0),
                'active': 1 if wc_product.get('status') == 'publish' else 0,
                'brand': brand,
                'category_code': category_code,
                'product_category_name': product_category,  # Dodano za debug
                'product_variation': 'size' if product_sizes else 'none',
                'product_variations': product_sizes,
                'sale_price': float(wc_product.get('sale_price', 0) or wc_product.get('price', 0) or 0),
                'invoice_price': float(wc_product.get('price', 0) or 0) * 0.8333 * 0.82,  # Kao u originalnom kodu
                'weight': "0.2",
                'vat': "20",
                'vat symbol': "Đ",
                'season': self.extract_season_from_categories_or_tags(categories, tags),
                'images': images[:4],
                'description':wc_product.get('description', ''),
            }

            # Dodaje EAN kodove ako su dostupni u meta podacima (opciono)
            # product_info['ean_variations'] = {}  # Implementirati ako je potrebno

            products_array.append(product_info)
            print(f"Obrađen proizvod: {product_info['product_name'][:50]}...")

        return products_array, product_skus

    def get_jwt_token(self):
        """Dobija JWT token od remiks servisa"""
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
        """Šalje podatke na remiks servis"""
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
        """Loguje greške u fajl"""
        if response_json and response_json.get('errors', []):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            error_log_path = os.getenv('error_log', 'remiks_errors.log')
            with open(error_log_path, 'a') as log_file:
                for error in response_json['errors']:
                    log_file.write(f"{timestamp}: {error}\n")

    def save_json_payload(self, payload):
        """Čuva JSON payload u fajl"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(script_dir, f'payload_wc_to_remiks_{timestamp}.json')

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)

            print(f"JSON payload sačuvan u {filename}")
        except Exception as e:
            print(f"Greška pri čuvanju JSON payload-a: {e}")

    def update_woocommerce_sync_status(self, product_skus):
        """Označava proizvode kao sinhronizovane (opciono - dodaje meta podatak)"""
        print(f"Označavam {len(product_skus)} proizvoda kao sinhronizovanih...")

        # Ovo je opciono - možete dodati custom meta field u WooCommerce
        # koji označava da je proizvod sinhronizovan sa remiks servisom

        for sku in product_skus:
            try:
                # Prvo dobija proizvod po SKU
                url = f"{self.wc_api_url}/products"
                params = {'sku': sku}

                response = requests.get(url, auth=self.wc_auth, params=params)
                if response.status_code == 200:
                    products = response.json()
                    if products:
                        product_id = products[0]['id']

                        # Ažurira meta podatak
                        update_url = f"{self.wc_api_url}/products/{product_id}"
                        update_data = {
                            'meta_data': [
                                {
                                    'key': 'remiks_synced',
                                    'value': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                }
                            ]
                        }

                        requests.put(update_url, auth=self.wc_auth, json=update_data)
            except Exception as e:
                print(f"Greška pri ažuriranju sync status za SKU {sku}: {e}")

    def run_sync(self):
        """Glavna funkcija za pokretanje sinhronizacije"""
        print("Pokretanje WooCommerce -> Remiks sinhronizacije...")

        # Priprema podatke
        payload, product_skus = self.prepare_remiks_data()

        if not payload:
            print("Nema proizvoda za sinhronizaciju")
            return

        print(f"Pripremljeno {len(payload)} proizvoda za slanje")

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
                # Označava proizvode kao sinhronizovane
                self.update_woocommerce_sync_status(product_skus)
            else:
                print("Remiks servis vratio greške:")
                self.log_errors(response)
                for error in response.get('errors', []):
                    print(f"  - {error}")
        else:
            print("Greška pri slanju na remiks servis")

    def format_stock_for_excel(self, stock_data):
        """Formatira stock podatke u string format: size:qty;size:qty"""
        if not stock_data:
            return ""

        formatted_parts = []
        for size, warehouses in stock_data.items():
            # Uzima količinu iz prvog magacina (obično '10-GLAVNI MAGACIN')
            qty = list(warehouses.values())[0] if warehouses else 0
            formatted_parts.append(f"{size}:{qty}")

        return ";".join(formatted_parts)

    def format_list_for_excel(self, list_data):
        """Formatira listu u string format odvojen sa ';'"""
        if not list_data:
            return ""

        # Filtrira prazne stringove
        filtered_list = [str(item) for item in list_data if str(item).strip()]
        return ";".join(filtered_list)

    def find_latest_json_file(self):
        """Pronalazi najnoviji JSON fajl na osnovu timestampa"""
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Traži sve JSON fajlove sa pattern-om
        json_files = []
        for filename in os.listdir(script_dir):
            if filename.startswith('payload_wc_to_remiks_') and filename.endswith('.json'):
                filepath = os.path.join(script_dir, filename)
                # Dobija modification time
                mtime = os.path.getmtime(filepath)
                json_files.append((filename, filepath, mtime))

        if not json_files:
            return None

        # Sortira po modification time (najnoviji prvi)
        json_files.sort(key=lambda x: x[2], reverse=True)
        latest_file = json_files[0][1]

        print(f"Najnoviji JSON fajl: {json_files[0][0]}")
        return latest_file

    def convert_json_to_excel(self, json_file_path=None):
        """Konvertuje JSON u Excel sa custom formatiranjem"""
        try:
            import pandas as pd
        except ImportError:
            print("Greška: pandas nije instaliran. Instalirajte ga sa: pip install pandas openpyxl")
            return

        # Ako nije specificiran fajl, traži najnoviji
        if not json_file_path:
            json_file_path = self.find_latest_json_file()
            if not json_file_path:
                print("Nije pronađen nijedan JSON fajl")
                return

        # Učitava JSON podatke
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
        except Exception as e:
            print(f"Greška pri čitanju JSON fajla: {e}")
            return

        print(f"Učitano {len(products_data)} proizvoda iz {json_file_path}")

        # Priprema podatke za Excel
        excel_data = []

        for product in products_data:
            # Kopira osnovne podatke
            excel_row = product.copy()

            # Formatira kompleksne kolone
            excel_row['stock'] = self.format_stock_for_excel(product.get('stock', {}))
            excel_row['product_variations'] = self.format_list_for_excel(product.get('product_variations', []))
            excel_row['images'] = self.format_list_for_excel(product.get('images', []))

            excel_data.append(excel_row)

        # Kreiranje DataFrame
        df = pd.DataFrame(excel_data)

        # Definiše redosled kolona (opciono)
        preferred_columns = [
            'sku', 'product_name', 'brand', 'gender', 'type', 'active',
            'net_retail_price', 'sale_price', 'invoice_price',
            'category_code', 'product_category_name',
            'product_variation', 'product_variations', 'stock',
            'weight', 'vat', 'vat symbol', 'season', 'images','description'
        ]

        # Reorganizuje kolone (zadržava sve kolone, prioritet ima preferred_columns)
        available_columns = [col for col in preferred_columns if col in df.columns]
        other_columns = [col for col in df.columns if col not in preferred_columns]
        final_columns = available_columns + other_columns

        df = df[final_columns]

        # Generiše ime Excel fajla
        script_dir = os.path.dirname(os.path.abspath(__file__))
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_filename = os.path.join(script_dir, f'woocommerce_products_{timestamp}.xlsx')

        # Eksportuje u Excel
        with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Products', index=False)

            # Dobija worksheet za formatiranje
            worksheet = writer.sheets['Products']

            # Auto-adjust kolona width
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter

                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass

                # Ograničava maksimalnu širinu
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        print(f"Excel fajl kreiran: {excel_filename}")
        print(f"Broj proizvoda: {len(excel_data)}")
        print(f"Broj kolona: {len(df.columns)}")

        # Prikazuje primer formatiranih podataka
        if excel_data:
            sample_product = excel_data[0]
            print(f"\nPrimer formatiranih podataka:")
            print(f"SKU: {sample_product.get('sku')}")
            print(f"Stock: {sample_product.get('stock')}")
            print(f"Variations: {sample_product.get('product_variations')}")
            print(f"Images: {sample_product.get('images', '')[:100]}...")

        return excel_filename

    def run_excel_conversion(self):
        """Pokreće konverziju najnovijeg JSON-a u Excel"""
        print("=== KONVERZIJA JSON -> EXCEL ===")
        excel_file = self.convert_json_to_excel()
        if excel_file:
            print(f"✅ Uspešno kreiran Excel fajl: {excel_file}")
        else:
            print("❌ Greška pri kreiranju Excel fajla")


if __name__ == "__main__":
    # Kreiranje sync objekta
    sync = WooCommerceToRemiks()

    # Menu opcija
    print("=== WOOCOMMERCE TO REMIKS SYNC ===")
    print("1. Pokreni punu sinhronizaciju (WooCommerce -> Remiks)")
    print("2. Konvertuj poslednji JSON u Excel")
    print("3. Pokreni sinhronizaciju + kreiraj Excel")
    print("4. Exit")

    choice = input("\nIzaberite opciju (1-4): ").strip()

    if choice == "1":
        # Samo sinhronizacija
        sync.run_sync()

    elif choice == "2":
        # Samo Excel konverzija
        sync.run_excel_conversion()

    elif choice == "3":
        # Puna sinhronizacija + Excel
        print("Pokretanje pune sinhronizacije...")
        sync.run_sync()
        print("\nKreiranje Excel fajla...")
        sync.run_excel_conversion()

    elif choice == "4":
        print("Izlaz...")

    else:
        print("Nevalidna opcija. Pokretanje osnovne sinhronizacije...")
        sync.run_sync()