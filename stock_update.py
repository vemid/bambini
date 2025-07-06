from datetime import datetime
import requests
import json
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


class StockUpdateScript:
    def __init__(self):
        # Remiks API kredencijali
        self.remiks_api_key = os.getenv('remiks_api_key')
        self.remiks_username = os.getenv('remiks_username')
        self.remiks_password = os.getenv('remiks_password')
        self.remiks_url_login = "https://portal.platforma.services/api/rest/login_check"
        self.remiks_url_stock = os.getenv('remiks_url_stock')

        # Putanje fajlova
        self.excel_file_path = "zalihe/zalihe.xlsx"
        self.project_root = os.path.dirname(os.path.abspath(__file__))

    def read_stock_excel(self):
        """Čita podatke o zalihama iz Excel fajla"""
        try:
            excel_path = os.path.join(self.project_root, self.excel_file_path)

            if not os.path.exists(excel_path):
                print(f"❌ Excel fajl nije pronađen: {excel_path}")
                return None

            # Čita Excel fajl
            df = pd.read_excel(excel_path)

            # Proverava potrebne kolone
            required_columns = ['SKU', 'SIZE', 'WAREHOUSE', 'QTY']
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                print(f"❌ Nedostaju kolone u Excel fajlu: {missing_columns}")
                print(f"Dostupne kolone: {list(df.columns)}")
                return None

            # Čisti podatke
            df = df.dropna(subset=['SKU'])  # Uklanja redove bez SKU
            df['SKU'] = df['SKU'].astype(str).str.strip()
            df['SIZE'] = df['SIZE'].astype(str).str.strip()
            df['WAREHOUSE'] = df['WAREHOUSE'].astype(str).str.strip()
            df['QTY'] = pd.to_numeric(df['QTY'], errors='coerce').fillna(0)

            print(f"✅ Učitano {len(df)} redova zaliha iz Excel fajla")
            return df

        except Exception as e:
            print(f"❌ Greška pri čitanju Excel fajla: {e}")
            return None

    def find_latest_json_product_file(self):
        """Pronalazi najnoviji JSON fajl sa podacima o proizvodima"""
        try:
            json_files = []
            for filename in os.listdir(self.project_root):
                if filename.startswith('payload_wc_to_remiks_') and filename.endswith('.json'):
                    filepath = os.path.join(self.project_root, filename)
                    mtime = os.path.getmtime(filepath)
                    json_files.append((filename, filepath, mtime))

            if not json_files:
                print("❌ Nije pronađen nijedan JSON fajl sa podacima o proizvodima")
                return None

            # Sortira po modification time (najnoviji prvi)
            json_files.sort(key=lambda x: x[2], reverse=True)
            latest_file = json_files[0][1]

            print(f"✅ Najnoviji JSON fajl: {json_files[0][0]}")
            return latest_file

        except Exception as e:
            print(f"❌ Greška pri traženju JSON fajla: {e}")
            return None

    def load_product_data_from_json(self, json_file_path):
        """Učitava podatke o proizvodima iz JSON fajla"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                products_data = json.load(f)

            # Konvertuje u dictionary sa SKU kao ključem
            products_dict = {}
            for product in products_data:
                sku = product.get('sku')
                if sku:
                    products_dict[sku] = product

            print(f"✅ Učitano {len(products_dict)} proizvoda iz JSON fajla")
            return products_dict

        except Exception as e:
            print(f"❌ Greška pri čitanju JSON fajla: {e}")
            return None

    def combine_stock_with_product_data(self, stock_df, products_dict):
        """Kombinuje podatke o zalihama sa podacima o proizvodima"""
        combined_data = []
        missing_products = set()

        # Grupira zalihe po SKU
        for sku, group in stock_df.groupby('SKU'):
            if sku not in products_dict:
                missing_products.add(sku)
                continue

            # Dobija podatke o proizvodu
            product_data = products_dict[sku]

            # Kreira stock strukturu
            stock_data = {}
            for _, row in group.iterrows():
                size = str(row['SIZE'])
                warehouse = str(row['WAREHOUSE'])
                qty = int(row['QTY'])

                if size not in stock_data:
                    stock_data[size] = {}
                stock_data[size][warehouse] = qty

            # Kombinuje sa podacima o proizvodu
            combined_product = {
                'sku': sku,
                'stock': stock_data,
                'type': product_data.get('type', 'configurable'),
                'net_retail_price': product_data.get('net_retail_price', 0),
                'sale_price': product_data.get('sale_price', 0),
                'invoice_price': product_data.get('invoice_price', 0)
            }

            combined_data.append(combined_product)

        if missing_products:
            print(f"⚠️  Proizvodi nisu pronađeni u JSON fajlu: {missing_products}")

        print(f"✅ Kombinovano {len(combined_data)} proizvoda sa podacima o zalihama")
        return combined_data

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

    def send_stock_to_remiks(self, payload, token):
        """Šalje podatke o zalihama na remiks servis"""
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
                print(f"❌ Greška pri slanju na remiks: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print("Error:", e)
            return None

    def log_errors(self, response_json):
        """Loguje greške u fajl"""
        if response_json and response_json.get('errors', []):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            error_log_path = os.getenv('error_log', 'remiks_stock_errors.log')
            with open(error_log_path, 'a', encoding='utf-8') as log_file:
                for error in response_json['errors']:
                    log_file.write(f"{timestamp}: {error}\n")

    def save_json_payload(self, payload):
        """Čuva JSON payload u fajl"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(self.project_root, f'payload_stock_update_{timestamp}.json')

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)

            print(f"✅ JSON payload sačuvan u {filename}")
            return filename
        except Exception as e:
            print(f"❌ Greška pri čuvanju JSON payload-a: {e}")
            return None

    def format_stock_for_excel_report(self, stock_data):
        """Formatira stock podatke za Excel izvештај"""
        if not stock_data:
            return ""

        formatted_parts = []
        for size, warehouses in stock_data.items():
            for warehouse, qty in warehouses.items():
                formatted_parts.append(f"{size}@{warehouse}:{qty}")

        return ";".join(formatted_parts)

    def create_excel_report(self, combined_data):
        """Kreira Excel izvештај o ažuriranim zalihama"""
        try:
            # Priprema podatke za Excel
            excel_data = []
            for product in combined_data:
                excel_row = {
                    'SKU': product['sku'],
                    'Type': product['type'],
                    'Net_Retail_Price': product['net_retail_price'],
                    'Sale_Price': product['sale_price'],
                    'Invoice_Price': product['invoice_price'],
                    'Stock_Summary': self.format_stock_for_excel_report(product['stock'])
                }
                excel_data.append(excel_row)

            # Kreiranje DataFrame
            df = pd.DataFrame(excel_data)

            # Generiše ime Excel fajla
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            excel_filename = os.path.join(self.project_root, f'stock_update_report_{timestamp}.xlsx')

            # Eksportuje u Excel
            with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Stock_Update', index=False)

                # Auto-adjust kolona width
                worksheet = writer.sheets['Stock_Update']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter

                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass

                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

            print(f"✅ Excel izvešataj kreiran: {excel_filename}")
            return excel_filename

        except Exception as e:
            print(f"❌ Greška pri kreiranju Excel izveštaja: {e}")
            return None

    def run_stock_update(self):
        """Glavna funkcija za pokretanje stock update-a"""
        print("🔄 POKRETANJE STOCK UPDATE SINHRONIZACIJE")
        print("=" * 50)

        # 1. Čita Excel fajl sa zalihama
        stock_df = self.read_stock_excel()
        if stock_df is None:
            return

        # 2. Pronalazi najnoviji JSON fajl
        json_file_path = self.find_latest_json_product_file()
        if json_file_path is None:
            return

        # 3. Učitava podatke o proizvodima
        products_dict = self.load_product_data_from_json(json_file_path)
        if products_dict is None:
            return

        # 4. Kombinuje podatke
        combined_data = self.combine_stock_with_product_data(stock_df, products_dict)
        if not combined_data:
            print("❌ Nema podataka za slanje")
            return

        # 5. Čuva JSON payload
        json_filename = self.save_json_payload(combined_data)

        # 6. Kreira Excel izveštaj
        excel_filename = self.create_excel_report(combined_data)

        # 7. Dobija JWT token
        jwt_token = self.get_jwt_token()
        if not jwt_token:
            print("❌ Nije moguće dobiti JWT token")
            return

        # 8. Šalje podatke na remiks
        print(f"📤 Slanje {len(combined_data)} proizvoda na remiks servis...")
        response = self.send_request_to_remiks(combined_data, jwt_token)

        if response:
            if not response.get('errors', []):
                print("✅ Uspešno poslano na remiks servis!")
            else:
                print("❌ Remiks servis vratio greške:")
                self.log_errors(response)
                for error in response.get('errors', []):
                    print(f"  - {error}")
        else:
            print("❌ Greška pri slanju na remiks servis")

        print("\n📋 SUMMARY:")
        print(f"  - Učitano zaliha iz Excel: {len(stock_df)} redova")
        print(f"  - Poslano proizvoda: {len(combined_data)}")
        print(f"  - JSON saved: {json_filename}")
        print(f"  - Excel report: {excel_filename}")

    def send_request_to_remiks(self, payload, token):
        """Wrapper za send_stock_to_remiks"""
        return self.send_stock_to_remiks(payload, token)


def create_sample_excel():
    """Kreira primer Excel fajla za testiranje"""
    sample_data = [
        {'SKU': 'TEST001', 'SIZE': '6', 'WAREHOUSE': '10-GLAVNI MAGACIN', 'QTY': 5},
        {'SKU': 'TEST001', 'SIZE': '8', 'WAREHOUSE': '10-GLAVNI MAGACIN', 'QTY': 3},
        {'SKU': 'TEST001', 'SIZE': '10', 'WAREHOUSE': '10-GLAVNI MAGACIN', 'QTY': 0},
        {'SKU': 'TEST002', 'SIZE': 'S', 'WAREHOUSE': '10-GLAVNI MAGACIN', 'QTY': 8},
        {'SKU': 'TEST002', 'SIZE': 'M', 'WAREHOUSE': '10-GLAVNI MAGACIN', 'QTY': 12},
        {'SKU': 'TEST002', 'SIZE': 'L', 'WAREHOUSE': '10-GLAVNI MAGACIN', 'QTY': 4},
    ]

    df = pd.DataFrame(sample_data)

    # Kreira direktorijum ako ne postoji
    os.makedirs('zalihe', exist_ok=True)

    # Čuva Excel fajl
    df.to_excel('zalihe/zalihe.xlsx', index=False)
    print("✅ Kreiran primer Excel fajla: zalihe/zalihe.xlsx")


if __name__ == "__main__":
    print("STOCK UPDATE SCRIPT")
    print("=" * 30)
    print("1. Pokreni stock update")
    print("2. Kreiraj primer Excel fajla")
    print("3. Exit")

    choice = input("\nIzaberite opciju (1-3): ").strip()

    if choice == "1":
        # Stock update
        updater = StockUpdateScript()
        updater.run_stock_update()

    elif choice == "2":
        # Kreiranje primer fajla
        try:
            create_sample_excel()
        except Exception as e:
            print(f"❌ Greška pri kreiranju primer fajla: {e}")

    elif choice == "3":
        print("Izlaz...")

    else:
        print("❌ Nevalidna opcija")