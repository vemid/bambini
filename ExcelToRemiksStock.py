from datetime import datetime
import requests
import json
from dotenv import load_dotenv
import os
import pandas as pd
import argparse
import sys

load_dotenv()


class ExcelToRemiksStock:
    def __init__(self):
        # Remiks API kredencijali - isti kao u Informix skripti
        self.remiks_api_key = os.getenv('remiks_api_key')
        self.remiks_username = os.getenv('remiks_username')
        self.remiks_password = os.getenv('remiks_password')
        self.remiks_url_login = "https://portal.platforma.services/api/rest/login_check"
        self.remiks_url_stock = os.getenv('remiks_url_stock')

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

    def calculate_prices(self, retail_price, special_price=None):
        """Računa cene na osnovu retail cene - slično Informix logici"""
        try:
            retail = float(retail_price) if retail_price else 0
            special = float(special_price) if special_price and pd.notna(special_price) else retail

            # Informix logika:
            # net_retail_price = get_maxcena * 1.2
            # sale_price = get_cena (special ili retail)
            # invoice_price = sale_price / 1.2 * 0.85

            net_retail_price = round(retail , 0)
            sale_price = special if special > 0 else retail
            invoice_price = round(sale_price / 1.2 * 0.8, 3)

            return net_retail_price, sale_price, invoice_price
        except:
            return 0, 0, 0

    def group_stock_by_sku(self, df):
        """Grupira stock podatke po SKU - isto kao Informix fetch_stock_data"""
        stock_data = {}

        for _, row in df.iterrows():
            sku = str(self.safe_get_value(row, 'SKU', '')).strip()
            if not sku:
                continue

            size = str(self.safe_get_value(row, 'SIZE', '')).strip()
            qty = int(self.safe_get_value(row, 'QTY', 0) or 0)
            warehouse_raw = str(self.safe_get_value(row, 'WAREHOUSE', 'Bambini doo'))

            # Formatira warehouse ime slično Informix logici: 'sif_obj_mp-NAZ_OBJ_MP'
            # Mapira Excel warehouse na standardni format
            warehouse_mapping = {
                'Bambini doo': '01-GLAVNI MAGACIN',
                'GLAVNI MAGACIN': '01-GLAVNI MAGACIN',
                'MAGACIN 1': '01-GLAVNI MAGACIN',
                'MAGACIN 2': '02-SPOREDNI MAGACIN',
                'MAGACIN 3': '03-OUTLET MAGACIN',
                'Bambini-10-GLAVNI MAGACIN': 'Bambini-10-GLAVNI MAGACIN',
            }

            warehouse = warehouse_mapping.get(warehouse_raw, 'Bambini-10-GLAVNI MAGACIN ')

            # Grupira po strukturi: stock_data[sku][size][warehouse] = qty
            if sku not in stock_data:
                stock_data[sku] = {}
            if size not in stock_data[sku]:
                stock_data[sku][size] = {}

            stock_data[sku][size][warehouse] = qty

        return stock_data

    def prepare_remiks_stock_data(self, excel_file_path):
        """Priprema podatke za stock sync - slično prepare_data() iz Informix skripte"""
        global product_type
        df = self.read_excel_file(excel_file_path)
        if df is None:
            return []

        # Grupiše stock podatke
        stock_data = self.group_stock_by_sku(df)

        # Kreira proizvode sa cenama (jedan proizvod po SKU)
        products_with_prices = {}

        for _, row in df.iterrows():
            sku = str(self.safe_get_value(row, 'SKU', '')).strip()
            if not sku or sku in products_with_prices:
                continue

            retail_price = self.safe_get_value(row, 'RETAIL_PRICE', 0)
            special_price = self.safe_get_value(row, 'SPECIAL_PRICE', None)

            net_retail_price, sale_price, invoice_price = self.calculate_prices(retail_price, special_price)

            products_with_prices[sku] = {
                'retail_price': float(retail_price) if retail_price else 0,
                'special_price': float(special_price) if special_price and pd.notna(special_price) else None,
                'net_retail_price': net_retail_price,
                'sale_price': sale_price,
                'invoice_price': invoice_price
            }

        # Kreira finalni products_array - slično Informix strukturi
        products_array = []

        for sku in stock_data.keys():
            if sku not in products_with_prices:
                # Ako nema podatke o cenama, koristi default vrednosti
                net_retail_price, sale_price, invoice_price = 0, 0, 0
            else:
                price_data = products_with_prices[sku]
                net_retail_price = price_data['net_retail_price']
                sale_price = price_data['sale_price']
                invoice_price = price_data['invoice_price']

                # Dobija tip proizvoda iz Excel-a ili postavlja default
                product_type = 'simple'  # Default
                if sku in products_with_prices:
                    # Traži tip u originalnim podacima
                    for _, row in df.iterrows():
                        if str(self.safe_get_value(row, 'SKU', '')).strip() == sku:
                            type_value = str(self.safe_get_value(row, 'TYPE', 'simple')).lower()
                            if type_value in ['configurable', 'configurabile']:
                                product_type = 'configurable'
                            else:
                                product_type = 'simple'
                            break

            # Struktura ista kao u Informix skripti
            product_info = {
                'sku': sku,
                'stock': stock_data[sku],
                'type': product_type,  # Uvek configurable kao u Informix
                'net_retail_price': net_retail_price,
                'sale_price': sale_price,
                # 'sale_price_start_date': datetime.now().strftime('%Y-%m-%d'),  # Danas
                # 'sale_price_end_date': datetime.now().strftime('%Y-%m-%d'),  # Danas
                'invoice_price': invoice_price,
            }

            products_array.append(product_info)

        print(f"Pripremljeno {len(products_array)} proizvoda sa stock podacima")
        return products_array

    def get_jwt_token(self):
        """Dobija JWT token - ista logika kao u Informix skripti"""
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
        """Šalje podatke na remiks servis - ista logika kao u Informix skripti"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        }

        send_data = json.dumps(payload)

        try:
            response = requests.request("POST", self.remiks_url_stock, headers=headers, data=send_data)
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
        """Loguje greške u fajl - ista logika kao u Informix skripti"""
        if response_json and response_json.get('errors', []):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            error_log_path = os.getenv('cf_error_log', 'remiks_stock_errors.log')
            with open(error_log_path, 'a') as log_file:
                for error in response_json['errors']:
                    log_file.write(f"{timestamp}: {error}\n")

    def save_json_payload(self, payload):
        """Čuva JSON payload u fajl - ista logika kao u Informix skripti"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(script_dir, f'payload_excel_stock_{timestamp}.json')

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)

            print(f"JSON payload sačuvan u {filename}")
        except Exception as e:
            print(f"Greška pri čuvanju JSON payload-a: {e}")

    def run_stock_sync(self, excel_file_path=None):
        """Glavna funkcija za pokretanje stock sinhronizacije iz Excel fajla"""
        print("Pokretanje Excel -> Remiks Stock sinhronizacije...")

        if excel_file_path is None:
            excel_file_path = self.select_excel_file()
            if not excel_file_path:
                return

        # Proverava da li fajl postoji
        if not os.path.exists(excel_file_path):
            print(f"Excel fajl nije pronađen: {excel_file_path}")
            return

        # Priprema podatke
        payload = self.prepare_remiks_stock_data(excel_file_path)

        if not payload:
            print("Nema proizvoda za stock sinhronizaciju")
            return

        print(f"Pripremljeno {len(payload)} proizvoda za stock sync")

        # Prikazuje primer proizvoda
        if payload:
            sample = payload[0]
            print(f"\nPrimer pripremljenog stock proizvoda:")
            print(f"SKU: {sample['sku']}")
            print(f"Type: {sample['type']}")
            print(f"Net retail price: {sample['net_retail_price']}")
            print(f"Sale price: {sample['sale_price']}")
            print(f"Invoice price: {sample['invoice_price']}")
            print(f"Stock struktura: {sample['stock']}")

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
                print("Uspešno poslano na remiks stock servis!")
            else:
                print("Remiks stock servis vratio greške:")
                self.log_errors(response)
                for error in response.get('errors', []):
                    print(f"  - {error}")
        else:
            print("Greška pri slanju na remiks stock servis")

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

    def analyze_stock_data(self, excel_file_path=None):
        """Analizira stock podatke iz Excel fajla"""
        print("=== ANALIZA STOCK PODATAKA ===")

        if excel_file_path is None:
            excel_file_path = self.select_excel_file()
            if not excel_file_path:
                return

        df = self.read_excel_file(excel_file_path)
        if df is None:
            return

        print(f"Ukupno redova: {len(df)}")

        # Stock analiza
        stock_data = self.group_stock_by_sku(df)

        print(f"Jedinstvenih SKU sa stock podacima: {len(stock_data)}")

        # Ukupne zalihe
        total_qty = 0
        total_variations = 0

        for sku, sizes in stock_data.items():
            for size, warehouses in sizes.items():
                total_variations += 1
                for warehouse, qty in warehouses.items():
                    total_qty += qty

        print(f"Ukupne zalihe: {total_qty}")
        print(f"Ukupno varijacija (SKU+SIZE): {total_variations}")

        # Magacini analiza
        all_warehouses = set()
        for sku, sizes in stock_data.items():
            for size, warehouses in sizes.items():
                all_warehouses.update(warehouses.keys())

        print(f"Magacini u upotrebi: {list(all_warehouses)}")

        # Primer stock podataka
        print(f"\n=== PRIMER STOCK STRUKTURE ===")
        sample_skus = list(stock_data.keys())[:3]
        for sku in sample_skus:
            print(f"SKU {sku}:")
            for size, warehouses in stock_data[sku].items():
                for warehouse, qty in warehouses.items():
                    print(f"  Veličina {size} u {warehouse}: {qty} kom")


if __name__ == "__main__":
    # Kreiranje argument parser-a
    parser = argparse.ArgumentParser(description='Excel to Remiks Stock Sync Script')
    parser.add_argument('--file', '-f', type=str, help='Putanja do Excel fajla')
    parser.add_argument('--sync', '-s', action='store_true', help='Pokreni stock sinhronizaciju direktno')
    parser.add_argument('--analyze', '-a', action='store_true', help='Analiziraj stock podatke')

    args = parser.parse_args()

    # Kreiranje sync objekta
    sync = ExcelToRemiksStock()

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
            print(f"Pokretanje stock sinhronizacije sa fajlom: {excel_file}")
            sync.run_stock_sync(excel_file)
        elif args.analyze:
            print(f"Analiza stock podataka: {excel_file}")
            sync.analyze_stock_data(excel_file)
        else:
            # Ako je samo specificiran fajl bez akcije, pokreni sync
            print(f"Pokretanje stock sinhronizacije sa fajlom: {excel_file}")
            sync.run_stock_sync(excel_file)
    else:
        # Interaktivni meni ako nema argumenata
        print("=== EXCEL TO REMIKS STOCK SYNC ===")
        print("1. Analiziraj stock podatke")
        print("2. Pokreni stock sinhronizaciju iz Excel fajla")
        print("3. Exit")

        choice = input("\nIzaberite opciju (1-3): ").strip()

        if choice == "1":
            # Analiza stock podataka
            sync.analyze_stock_data()

        elif choice == "2":
            # Stock sinhronizacija iz Excel fajla
            sync.run_stock_sync()

        elif choice == "3":
            print("Izlaz...")

        else:
            print("Nevalidna opcija. Izlaz...")