import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from io import BytesIO
import time
from PIL import Image
import json
import os
from dotenv import load_dotenv

# -------------------------------
# CONFIGURATION & SECURITY
# -------------------------------
# Load environment variables from .env file
load_dotenv()

# 1. URL for Fetching Duplicates (Standard API)
WP_READ_URL = "https://staging.eggsinvest.com/wp-json/wp/v2/property"

# 2. URL for Media Uploads (Standard API)
MEDIA_URL = "https://staging.eggsinvest.com/wp-json/wp/v2/media"

# 3. URL for Creating Posts (CUSTOM ENDPOINT - Option B)
WP_CUSTOM_ENDPOINT = "https://staging.eggsinvest.com/wp-json/eggs/v1/import-property"

# Credentials from .env
USERNAME = os.getenv("WP_USERNAME")
APP_PASSWORD = os.getenv("WP_APP_PASSWORD")

if not APP_PASSWORD:
    print("❌ Error: WP_APP_PASSWORD not found. Please create a .env file.")
    exit()

# CSV files from the scraper
CSV_FILES = {
    "all": "property_listings_all.csv",
    "sale": "scraped_data.csv", 
    "rent": "property_listings_rent.csv"
}

# Choose which CSV to upload
CSV_FILE = CSV_FILES["sale"]  # Change to "sale" or "rent" as needed

MAX_UPLOADS = 50
SLEEP_BETWEEN = 2
MIN_IMAGE_SIZE = 5000
MIN_IMAGE_WIDTH = 200
MIN_IMAGE_HEIGHT = 150

# ACF Field Mapping
ACF_FIELDS = {
    "_ere_property_price": "price", 
    "property_category": "category",
    "_ere_property_address": "address",
    "property_city": "city",
    "_ere_property_bedrooms": "bedrooms",
    "_ere_property_bathrooms": "bathrooms",
    "property_agent": "agent",
    "property_source_url": "link",
    "property_source_site": "source",
    "property_published_date": "published",
    
    # Financial metrics
    "price_numeric": "price_numeric",
    "price_frequency": "price_frequency",
    "estimated_property_value": "estimated_property_value",
    "annual_rental_income": "annual_rental_income",
    "gross_rental_yield": "gross_rental_yield",
    "roi_percentage": "roi_percentage",
    "estimated_monthly_rent": "estimated_monthly_rent",
    "metric_status": "metric_status"
}

# -------------------------------
# LOAD DATA
# -------------------------------
print("📂 Loading data from:", CSV_FILE)
try:
    df = pd.read_csv(CSV_FILE)
except Exception as e:
    print("❌ Failed to read CSV:", e)
    exit()

if df.empty:
    print("⚠ No listings found in CSV.")
    exit()

print(f"✅ Loaded {len(df)} listings from CSV")

expected_cols = [
    "title", "price", "link", "source", "published",
    "category", "image_urls_str", "description", "address", 
    "agent", "bedrooms", "bathrooms", "city",
    "price_numeric", "price_frequency", "estimated_property_value",
    "annual_rental_income", "gross_rental_yield", "roi_percentage",
    "estimated_monthly_rent", "metric_status"
]

for col in expected_cols:
    if col not in df.columns:
        df[col] = ""

for col in expected_cols:
    df[col] = df[col].fillna("N/A").astype(str)

# Remove exact duplicates from dataframe
df = df.drop_duplicates(subset=['link'], keep='first')

# -------------------------------
# FETCH EXISTING POSTS (For Duplicate Check)
# -------------------------------
print("🔍 Checking existing properties (using Standard API)...")
existing_posts = []
page = 1

# We still use the standard API here just to read what's already on the site
while True:
    try:
        r = requests.get(
            WP_READ_URL,
            params={"per_page": 100, "page": page},
            auth=HTTPBasicAuth(USERNAME, APP_PASSWORD),
            timeout=30
        )
        if r.status_code != 200:
            break
        data = r.json()
        if not data:
            break
        existing_posts.extend(data)
        page += 1
    except Exception as e:
        print(f"⚠ Error fetching existing posts: {e}")
        break

existing_titles = {p["title"]["rendered"].strip().lower(): p["id"] for p in existing_posts}
existing_links = {}
for p in existing_posts:
    acf = p.get("acf", {})
    if isinstance(acf, dict):
        source_url = acf.get("property_source_url", "")
        if source_url:
            existing_links[source_url.lower()] = p["id"]

print(f"📦 Found {len(existing_posts)} existing property posts.")

# -------------------------------
# UTILITY FUNCTIONS
# -------------------------------
def validate_image_quality(image_content):
    try:
        img = Image.open(BytesIO(image_content))
        width, height = img.size
        if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
            return False
        return True
    except Exception:
        return True

def upload_image(image_url, image_index=1):
    """Uploads image to standard WP Media library"""
    if not image_url or image_url.lower() == "n/a":
        return None
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "image/*"
        }
        
        img_response = requests.get(image_url, headers=headers, timeout=30, stream=True)

        if img_response.status_code != 200:
            return None

        image_content = img_response.content
        if len(image_content) < MIN_IMAGE_SIZE:
            pass # Small file warning

        if not validate_image_quality(image_content):
            return None

        mime_type = img_response.headers.get("Content-Type", "image/jpeg")
        file_name = image_url.split("/")[-1].split("?")[0] or f"property-image-{image_index}.jpg"
        
        # Extension fix
        if "webp" in mime_type and not file_name.endswith(".webp"): file_name += ".webp"
        elif "jpeg" in mime_type and not file_name.endswith(".jpg"): file_name += ".jpg"
        elif "png" in mime_type and not file_name.endswith(".png"): file_name += ".png"

        files = {'file': (file_name, BytesIO(image_content), mime_type)}

        # POST to Standard Media Endpoint
        response = requests.post(
            MEDIA_URL,
            files=files,
            auth=HTTPBasicAuth(USERNAME, APP_PASSWORD),
            timeout=30
        )

        if response.status_code == 201:
            media_json = response.json()
            return {"id": media_json.get("id"), "url": media_json.get("source_url")}
        return None

    except Exception as e:
        print(f"      ❌ Image Error: {e}")
        return None

def upload_multiple_images(image_urls_str):
    if not image_urls_str or image_urls_str.lower() == "n/a":
        return []
    image_urls = [url.strip() for url in image_urls_str.split('|') if url.strip()]
    uploaded = []
    for idx, url in enumerate(image_urls, 1):
        res = upload_image(url, idx)
        if res: uploaded.append(res)
        time.sleep(0.5)
    return uploaded

def build_image_gallery_html(images):
    if len(images) <= 1: return ""
    gallery_html = '<div class="property-gallery" style="margin: 20px 0;"><h3>📸 Gallery</h3><div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px;">'
    for img in images[1:]:
        gallery_html += f'<div style="border: 1px solid #ddd;"><img src="{img["url"]}" style="width: 100%; height: 200px; object-fit: cover;" /></div>'
    gallery_html += '</div></div>'
    return gallery_html

def clean_value(value):
    if not value or str(value).strip().upper() == "N/A": return ""
    return str(value).strip()

def format_financial_value(value):
    if not value or str(value).strip().upper() == "N/A": return ""
    try:
        clean = str(value).replace("%", "").strip()
        return f"£{float(clean):,.2f}"
    except: return str(value)

def build_acf_data(row):
    acf_data = {}
    for acf_field, csv_col in ACF_FIELDS.items():
        val = row.get(csv_col, "")
        clean_val = clean_value(val)
        
        # Try to convert numbers for ACF Number fields
        if csv_col in ["price_numeric", "estimated_property_value", "gross_rental_yield", "roi_percentage"]:
            if clean_val:
                try:
                    clean_val = float(clean_val.replace("%", "").strip())
                except: pass
        
        acf_data[acf_field] = clean_val
    return acf_data

def build_html_content(row, uploaded_images):
    # (Simplified version of your HTML builder for brevity, full logic remains same)
    price = clean_value(row.get("price", ""))
    desc = clean_value(row.get("description", ""))
    if "\n\n" in desc: desc = "".join([f"<p>{p}</p>" for p in desc.split("\n\n")])
    else: desc = f"<p>{desc}</p>"
    
    gallery = build_image_gallery_html(uploaded_images)
    
    return f"""
    <div class="property-details">
        <h3>Property Info</h3>
        <p><strong>Price:</strong> {price}</p>
        <p><strong>Description:</strong></p>
        {desc}
        {gallery}
    </div>
    """

# -------------------------------
# MAIN UPLOAD LOOP
# -------------------------------
success, skipped, failed = 0, 0, 0

print("\n" + "="*70)
print("🚀 STARTING UPLOAD VIA CUSTOM ENDPOINT (Option B)")
print("="*70 + "\n")

for idx, row in df.head(MAX_UPLOADS).iterrows():
    title = clean_value(row.get("title", ""))
    link = clean_value(row.get("link", ""))
    
    print(f"[{idx + 1}] {title[:60]}...")

    if not title or not link:
        skipped += 1
        continue

    # Duplicate Check
    if title.lower() in existing_titles or link.lower() in existing_links:
        print(f"  ⏭ Already exists, skipping")
        skipped += 1
        continue

    # 1. Upload Images (Standard API)
    image_urls_str = clean_value(row.get("image_urls_str", ""))
    uploaded_images = []
    if image_urls_str:
        uploaded_images = upload_multiple_images(image_urls_str)
        print(f"  🖼 Uploaded {len(uploaded_images)} images")

    featured_media_id = uploaded_images[0]["id"] if uploaded_images else None

    # 2. Prepare Data
    content_html = build_html_content(row, uploaded_images)
    acf_data = build_acf_data(row)

    # Payload for CUSTOM ENDPOINT
    post_payload = {
        "title": title,
        "content": content_html,
        "featured_media": featured_media_id,
        "acf": acf_data # PHP will handle update_field()
    }

    # 3. Send to Custom Endpoint
    try:
        r = requests.post(
            WP_CUSTOM_ENDPOINT, 
            json=post_payload, 
            auth=HTTPBasicAuth(USERNAME, APP_PASSWORD),
            timeout=30
        )
        
        if r.status_code == 200:
            # Custom endpoints usually return 200 on success
            res_json = r.json()
            print(f"  ✅ SUCCESS! (ID: {res_json.get('id')})")
            success += 1
        else:
            print(f"  ❌ Failed ({r.status_code}): {r.text[:200]}")
            failed += 1
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        failed += 1

    time.sleep(SLEEP_BETWEEN)

print("\n" + "="*70)
print(f"🏁 DONE: {success} Success | {skipped} Skipped | {failed} Failed")
print("="*70)