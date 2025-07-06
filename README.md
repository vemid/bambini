# Excel to Remiks Sync

Python skripta za sinhronizaciju proizvoda iz Excel fajlova sa Remiks servisom. Skripta čita lokalne Excel fajlove i šalje podatke na Remiks API koristeći istu strukturu kao WooCommerce integracijski servis.

## 📋 Sadržaj

- [Instalacija](#instalacija)
- [Konfiguracija](#konfiguracija)
- [Korišćenje](#korišćenje)
- [Struktura Excel fajla](#struktura-excel-fajla)
- [Mapiranje kategorija](#mapiranje-kategorija)
- [Primeri pokretanja](#primeri-pokretanja)
- [Struktura projekta](#struktura-projekta)
- [API dokumentacija](#api-dokumentacija)

## 🚀 Instalacija

### Potrebni Python paketi:
```bash
pip install pandas openpyxl requests python-dotenv
```

### Kloniranje projekta:
```bash
git clone <repo_url>
cd excel-to-remiks-sync
```

## ⚙️ Konfiguracija

Kreirajte `.env` fajl u root direktorijumu sa sledećim kredencijalima:

```env
# Remiks API kredencijali
remiks_api_key=your_api_key_here
remiks_username=your_username_here
remiks_password=your_password_here
remiks_url_login=https://api.remiks.com/login
remiks_url_product=https://api.remiks.com/products

# Log fajl (opciono)
error_log=remiks_errors.log
```

## 📖 Korišćenje

### Command Line opcije:

#### 1. Direktno slanje podataka (default fajl `podaci/podaci.xlsx`):
```bash
python excel_to_remiks.py --sync
# ili kratko:
python excel_to_remiks.py -s
```

#### 2. Specificiran fajl + sinhronizacija:
```bash
python excel_to_remiks.py --file podaci/moj_fajl.xlsx --sync
# ili kratko:
python excel_to_remiks.py -f podaci/moj_fajl.xlsx -s
```

#### 3. Analiza Excel fajla:
```bash
python excel_to_remiks.py --analyze
# ili sa specificiranim fajlom:
python excel_to_remiks.py -f podaci/moj_fajl.xlsx -a
```

#### 4. Interaktivni meni:
```bash
python excel_to_remiks.py
```

### Argumenti:
- `--file, -f`: Putanja do Excel fajla
- `--sync, -s`: Pokreni sinhronizaciju
- `--analyze, -a`: Analiziraj Excel fajl
- `--help, -h`: Prikaži help

## 📊 Struktura Excel fajla

Excel fajl mora imati sledeće kolone:

| Kolona | Opis | Obavezno |
|--------|------|----------|
| `SKU` | Jedinstveni kod proizvoda | ✅ |
| `TYPE` | Tip proizvoda (Configurabile/Simple) | ✅ |
| `VARIATION` | Tip varijacije (SIZE) | ✅ |
| `SIZE` | Veličina proizvoda | ✅ |
| `EAN` | EAN kod | ✅ |
| `NAME` | Naziv proizvoda | ✅ |
| `DESCRIPTION` | Opis proizvoda | ❌ |
| `RETAIL_PRICE` | Maloprodajna cena | ✅ |
| `SPECIAL_PRICE` | Akcijska cena | ❌ |
| `VAT_SYMBOL` | VAT simbol (Đ) | ✅ |
| `VAT` | VAT procenat (20) | ✅ |
| `BRAND` | Brend proizvoda | ✅ |
| `CATEGORY` | Kategorija proizvoda | ✅ |
| `IMAGES` | URL slike (razdvojeni zarezom) | ❌ |
| `WAREHOUSE` | Naziv magacina | ✅ |
| `QTY` | Količina na stanju | ✅ |
| `WEIGHT` | Težina proizvoda | ❌ |

### Primer Excel strukture:
```
SKU         | TYPE          | SIZE | NAME                    | QTY | CATEGORY        
12249970X   | Configurabile | 128  | Bermude za dečake       | 2   | Dečiji šorcevi  
12249970X   | Configurabile | 140  | Bermude za dečake       | 3   | Dečiji šorcevi  
12249970X   | Configurabile | 152  | Bermude za dečake       | 1   | Dečiji šorcevi  
```

## 🗂️ Mapiranje kategorija

Skripta automatski mapira kategorije u numeričke kodove:

### Muške kategorije (1xxx):
- `TRENERKE` → `1001`
- `DUKSEVI` → `1002` 
- `MAJICE` → `1003`
- `ŠORCEVI` → `1004`
- `PANTALONE` → `1005`
- `JAKNE` → `1006`
- `SETOVI` → `1007`
- `OSTALO` → `1099`

### Ženske kategorije (2xxx):
- `TRENERKE` → `2001`
- `DUKSEVI` → `2002`
- `MAJICE` → `2003`
- `ŠORCEVI` → `2004`
- `PANTALONE` → `2005`
- `JAKNE` → `2006`
- `SETOVI` → `2007`
- `OSTALO` → `2099`

### Unisex kategorije (3xxx):
- `TRENERKE` → `3001`
- `DUKSEVI` → `3002`
- `MAJICE` → `3003`
- `ŠORCEVI` → `3004`
- `PANTALONE` → `3005`
- `JAKNE` → `3006`
- `SETOVI` → `3007`
- `OSTALO` → `3099`

**Pol se automatski određuje na osnovu kategorije:**
- Muško: "dečaci", "decaci", "dečiji", "boys"
- Žensko: "devojčice", "devojcice", "girls"
- Unisex: sve ostalo

## 📁 Struktura projekta

```
projekt/
├── excel_to_remiks.py              # Glavna skripta
├── woocommerce_to_remiks.py        # WooCommerce skripta (postojeća)
├── .env                            # API kredencijali
├── README.md                       # Dokumentacija
├── requirements.txt                # Python dependencies
└── podaci/                         # Folder sa Excel fajlovima
    ├── podaci.xlsx                 # Default Excel fajl
    └── drugi_fajlovi.xlsx          # Dodatni fajlovi
```

## 🎯 Primeri pokretanja

### Osnovni workflow:

1. **Analiziraj Excel fajl:**
```bash
python excel_to_remiks.py -a
```

2. **Pokreni sinhronizaciju:**
```bash
python excel_to_remiks.py -s
```

3. **Custom fajl:**
```bash
python excel_to_remiks.py -f podaci/specijalni_proizvodi.xlsx -s
```

### Batch obrada:
```bash
# Analiziraj sve fajlove u podaci folderu
for file in podaci/*.xlsx; do
    python excel_to_remiks.py -f "$file" -a
done

# Sinhronizuj sve fajlove
for file in podaci/*.xlsx; do
    python excel_to_remiks.py -f "$file" -s
done
```

## 📋 Logovanje i debug

### Generirani fajlovi:
- `payload_excel_to_remiks_YYYYMMDD_HHMMSS.json` - JSON payload koji se šalje
- `remiks_errors.log` - Log grešaka
- `woocommerce_products_YYYYMMDD_HHMMSS.xlsx` - Excel export (WooCommerce skripta)

### Debug informacije:
Skripta prikazuje debug informacije za:
- Mapiranje kategorija
- Pronađene brendove
- Struktura zaliha po veličinama
- Broj obrađenih proizvoda

## 🔧 API dokumentacija

### JSON struktura koja se šalje na Remiks:

```json
{
  "sku": "12249970X",
  "gender": "M",
  "product_name": "Bermude za decake JPSTLOGO, teget",
  "stock": {
    "128": {"Bambini doo": 2},
    "140": {"Bambini doo": 3},
    "152": {"Bambini doo": 1}
  },
  "type": "configurable",
  "net_retail_price": 2890.0,
  "active": 1,
  "brand": "JACK & JONES",
  "category_code": "1004",
  "product_category_name": "ŠORCEVI",
  "product_variation": "size",
  "product_variations": ["128", "140", "152"],
  "sale_price": 2601.0,
  "invoice_price": 1959.67,
  "weight": "1",
  "vat": "20",
  "vat symbol": "Đ",
  "season": "UNIVERZALNO",
  "images": ["url1", "url2", "url3", ""],
  "description": "Opis proizvoda..."
}
```

## ⚠️ Važne napomene

1. **SKU grupiranje**: Proizvodi sa istim SKU se automatski grupišu po veličinama
2. **Obavezna polja**: SKU, NAME, SIZE, QTY su obavezna
3. **Charset handling**: Skripta automatski konvertuje srpska slova (š→s, ž→z, č→c, ć→c)
4. **Warehouse mapiranje**: Koristi se naziv iz WAREHOUSE kolone ili default "10-GLAVNI MAGACIN"
5. **Slike**: Razdvojene zarezom, automatski se dopunjavaju do 4 slike

## 🐛 Troubleshooting

### Česte greške:

1. **"Excel fajl nije pronađen"**
   - Proverite putanju do fajla
   - Proverite da li postoji `podaci` folder

2. **"Nije moguće dobiti JWT token"**
   - Proverite kredencijale u `.env` fajlu
   - Proverite internet konekciju

3. **"Pandas nije instaliran"**
   ```bash
   pip install pandas openpyxl
   ```

4. **"Nema proizvoda za sinhronizaciju"**
   - Proverite da li Excel ima podatke
   - Proverite da li SKU kolona nije prazna

### Debug mode:
Dodajte debug ispise u skriptu za detaljniju analizu problema.

## 📞 Podrška

Za dodatne informacije ili probleme, kontaktirajte razvojni tim.

---

**Verzija:** 1.0  
**Datum:** 2025  
**Autor:** Bambini Development Team