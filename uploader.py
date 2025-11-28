import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from io import BytesIO
import time
from PIL import Image
import json

# -------------------------------
# CONFIGURATION
# -------------------------------
WP_URL = "https://staging.eggsinvest.com/wp-json/wp/v2/property"
MEDIA_URL = "https://staging.eggsinvest.com/wp-json/wp/v2/media"
USERNAME = "ANSHULGUPTA"
APP_PASSWORD = "m1UI cMhA KskC zQal MmyP qyMC"

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

# ACF Field Mapping (customize these to match your ACF field names)
ACF_FIELDS = {
    "ere_single_property_header_price_location": "price", 
    "property_category": "category",
    "_ere_property_address": "address",
    "property_city": "city",
    "ere_property_bedrooms": "bedrooms",
    "ere_property_bathrooms": "bathrooms",
    "property_agent": "agent",
    "property_source_url": "link",
    "property_source_site": "source",
    "property_published_date": "published",
    
    # Financial metrics from scraper
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

# Ensure expected columns exist
expected_cols = [
    "title", "price", "link", "source", "published",
    "category", "image_urls_str", "description", "address", 
    "agent", "bedrooms", "bathrooms", "city",
    # Financial metrics
    "price_numeric", "price_frequency", "estimated_property_value",
    "annual_rental_income", "gross_rental_yield", "roi_percentage",
    "estimated_monthly_rent", "metric_status"
]

for col in expected_cols:
    if col not in df.columns:
        df[col] = ""

# Clean up N/A and None values
for col in expected_cols:
    df[col] = df[col].fillna("N/A").astype(str)

# Remove exact duplicates
print(f"📊 Checking for duplicates in CSV...")
df_before = len(df)
df = df.drop_duplicates(subset=['link'], keep='first')
df_after = len(df)
if df_before > df_after:
    print(f"⚠ Removed {df_before - df_after} duplicate rows from CSV")
else:
    print(f"✅ No duplicates found in CSV")

# -------------------------------
# FETCH EXISTING POSTS
# -------------------------------
print("🔍 Fetching existing WordPress properties...")
existing_posts = []
page = 1

while True:
    try:
        r = requests.get(
            WP_URL,
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

# Build lookup dictionaries for duplicate detection
existing_titles = {p["title"]["rendered"].strip().lower(): p["id"] for p in existing_posts}
existing_links = {}
for p in existing_posts:
    # Check ACF fields for source URL
    acf = p.get("acf", {})
    
    # --- FIX ---
    # Check if 'acf' is a dictionary before trying to .get() from it.
    # The API might return an empty list [] instead of an object {}.
    if isinstance(acf, dict):
        source_url = acf.get("property_source_url", "")
        if source_url:
            existing_links[source_url.lower()] = p["id"]
    # --- END FIX ---

print(f"📦 Found {len(existing_posts)} existing property posts.")

# -------------------------------
# IMAGE VALIDATION & UPLOAD
# -------------------------------
def validate_image_quality(image_content):
    """Validate image dimensions and quality"""
    try:
        img = Image.open(BytesIO(image_content))
        width, height = img.size
        
        print(f"      📐 Dimensions: {width}x{height}px")
        
        if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
            print(f"      ⚠ Too small: {width}x{height}px")
            return False
        
        return True
    except Exception as e:
        print(f"      ⚠ Validation error (uploading anyway): {e}")
        return True

def upload_image(image_url, image_index=1):
    """Download and upload a single image to WordPress"""
    if not image_url or image_url.lower() == "n/a":
        return None
    
    print(f"    📥 Image {image_index}: {image_url[:60]}...")
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "image/*",
            "Referer": image_url.split('/')[0] + '//' + image_url.split('/')[2] if len(image_url.split('/')) > 2 else ""
        }
        
        img_response = requests.get(
            image_url, 
            headers=headers, 
            allow_redirects=True, 
            timeout=30,
            stream=True
        )

        if img_response.status_code != 200:
            print(f"      ❌ Download failed ({img_response.status_code})")
            return None

        image_content = img_response.content
        
        if not image_content:
            print(f"      ❌ Empty content")
            return None

        image_size = len(image_content)
        print(f"      💾 Size: {image_size / 1024:.1f} KB")
        
        if image_size < MIN_IMAGE_SIZE:
            print(f"      ⚠ Small file, uploading anyway...")

        if not validate_image_quality(image_content):
            return None

        mime_type = img_response.headers.get("Content-Type", "image/jpeg")
        
        if not mime_type.startswith("image/"):
            print(f"      ❌ Invalid MIME: {mime_type}")
            return None

        file_name = image_url.split("/")[-1].split("?")[0] or f"property-image-{image_index}"
        
        # Normalize file extensions
        if "webp" in mime_type and not file_name.endswith(".webp"):
            file_name = file_name.rsplit(".", 1)[0] + ".webp"
        elif "png" in mime_type and not file_name.endswith(".png"):
            file_name = file_name.rsplit(".", 1)[0] + ".png"
        elif ("jpeg" in mime_type or "jpg" in mime_type) and not (file_name.endswith(".jpg") or file_name.endswith(".jpeg")):
            file_name = file_name.rsplit(".", 1)[0] + ".jpg"

        files = {'file': (file_name, BytesIO(image_content), mime_type)}

        response = requests.post(
            MEDIA_URL,
            files=files,
            auth=HTTPBasicAuth(USERNAME, APP_PASSWORD),
            timeout=30
        )

        if response.status_code == 201:
            media_json = response.json()
            media_id = media_json.get("id")
            media_url = media_json.get("source_url")
            print(f"      ✅ Uploaded (ID: {media_id})")
            return {"id": media_id, "url": media_url}
        else:
            print(f"      ❌ Upload failed ({response.status_code}): {response.text[:100]}")
            return None

    except requests.Timeout:
        print(f"      ⏱ Timeout")
        return None
    except Exception as e:
        print(f"      ❌ Error: {e}")
        return None

def upload_multiple_images(image_urls_str):
    """Parse pipe-separated URLs and upload all images"""
    if not image_urls_str or image_urls_str.lower() == "n/a" or not image_urls_str.strip():
        return []
    
    # Split by pipe separator
    image_urls = [url.strip() for url in image_urls_str.split('|') if url.strip()]
    
    if not image_urls:
        return []
    
    print(f"  🖼 Found {len(image_urls)} images to upload")
    
    uploaded_images = []
    for idx, url in enumerate(image_urls, 1):
        result = upload_image(url, idx)
        if result:
            uploaded_images.append(result)
        time.sleep(0.5)  # Small delay between images
    
    return uploaded_images

def build_image_gallery_html(images):
    """Build HTML gallery for additional images (after featured image)"""
    if len(images) <= 1:
        return ""
    
    gallery_html = '<div class="property-gallery" style="margin: 20px 0;">\n'
    gallery_html += '<h3>📸 Property Gallery</h3>\n'
    gallery_html += '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; margin-top: 15px;">\n'
    
    # Skip first image (it's the featured image)
    for img in images[1:]:
        gallery_html += f'''
        <div style="border: 1px solid #ddd; border-radius: 5px; overflow: hidden;">
            <img src="{img["url"]}" alt="Property Image" style="width: 100%; height: 200px; object-fit: cover;" loading="lazy" />
        </div>\n'''
    
    gallery_html += '</div>\n</div>\n'
    return gallery_html

def format_description_for_display(description):
    """Format description with proper paragraph breaks"""
    if not description or description.lower() in ["n/a", "no description available", "not fetched (limit reached)", "pending"]:
        return "No description available for this property."
    
    description = str(description).strip()
    
    # If description already has paragraph breaks (from enhanced scraper), wrap in paragraph tags
    if "\n\n" in description:
        # Split into paragraphs and wrap each
        paragraphs = description.split("\n\n")
        formatted = ""
        for para in paragraphs:
            para = para.strip()
            if para:
                formatted += f"<p>{para}</p>\n"
        return formatted
    else:
        # Single block - wrap in paragraph tag
        return f"<p>{description}</p>"

def clean_value(value):
    """Clean N/A values and convert to proper format"""
    if not value or str(value).strip().upper() == "N/A":
        return ""
    return str(value).strip()

def format_financial_value(value, is_percentage=False):
    """Format financial values properly"""
    if not value or str(value).strip().upper() == "N/A":
        return ""
    
    try:
        # Remove % sign if present
        clean_val = str(value).replace("%", "").strip()
        num_val = float(clean_val)
        
        if is_percentage:
            return f"{num_val:.2f}%"
        else:
            # Format as currency
            return f"£{num_val:,.2f}"
    except:
        return str(value)

def build_acf_data(row):
    """Build ACF fields data from CSV row"""
    acf_data = {}
    
    for acf_field_name, csv_column in ACF_FIELDS.items():
        value = row.get(csv_column, "")
        
        # Handle special formatting for specific fields
        if csv_column in ["gross_rental_yield", "roi_percentage"]:
            # These might already be formatted with %, extract numeric value
            clean_val = clean_value(value)
            if clean_val:
                try:
                    numeric_val = float(clean_val.replace("%", "").strip())
                    acf_data[acf_field_name] = numeric_val
                except:
                    acf_data[acf_field_name] = clean_val
            else:
                acf_data[acf_field_name] = ""
                
        elif csv_column in ["price_numeric", "estimated_property_value", "annual_rental_income", "estimated_monthly_rent"]:
            # Numeric financial fields
            clean_val = clean_value(value)
            if clean_val:
                try:
                    acf_data[acf_field_name] = float(clean_val)
                except:
                    acf_data[acf_field_name] = clean_val
            else:
                acf_data[acf_field_name] = ""
        else:
            # Regular text fields
            acf_data[acf_field_name] = clean_value(value)
    
    return acf_data

def build_financial_metrics_html(row):
    """Build HTML section for financial metrics"""
    category = row.get("category", "Unknown")
    
    # Extract values
    price = clean_value(row.get("price", "N/A"))
    estimated_value = format_financial_value(row.get("estimated_property_value"))
    annual_rent = format_financial_value(row.get("annual_rental_income"))
    rental_yield = clean_value(row.get("gross_rental_yield", "N/A"))
    roi = clean_value(row.get("roi_percentage", "N/A"))
    monthly_rent = format_financial_value(row.get("estimated_monthly_rent"))
    metric_status = clean_value(row.get("metric_status", "N/A"))
    
    # Don't show section if no meaningful data
    if not any([estimated_value, annual_rent, rental_yield, roi, monthly_rent]):
        return ""
    
    html = '<div class="property-financials" style="background: #f9f9f9; padding: 20px; border-radius: 5px; margin: 20px 0;">\n'
    html += '<h3>💰 Investment Metrics</h3>\n'
    html += '<table style="width:100%; border-collapse: collapse;">\n'
    
    if category == "For Rent":
        html += f'''
        <tr style="border: 1px solid #ddd;">
            <td style="padding: 8px; font-weight: bold; width: 40%;">Monthly Rent:</td>
            <td style="padding: 8px;">{price}</td>
        </tr>
        '''
        if annual_rent:
            html += f'''
            <tr style="border: 1px solid #ddd; background-color: #fff;">
                <td style="padding: 8px; font-weight: bold;">Annual Rental Income:</td>
                <td style="padding: 8px;">{annual_rent}</td>
            </tr>
            '''
        if estimated_value:
            html += f'''
            <tr style="border: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: bold;">Estimated Property Value:</td>
                <td style="padding: 8px;">{estimated_value}</td>
            </tr>
            '''
    else:  # For Sale
        html += f'''
        <tr style="border: 1px solid #ddd;">
            <td style="padding: 8px; font-weight: bold; width: 40%;">Asking Price:</td>
            <td style="padding: 8px;">{price}</td>
        </tr>
        '''
        if monthly_rent:
            html += f'''
            <tr style="border: 1px solid #ddd; background-color: #fff;">
                <td style="padding: 8px; font-weight: bold;">Estimated Monthly Rent:</td>
                <td style="padding: 8px;">{monthly_rent}</td>
            </tr>
            '''
        if annual_rent:
            html += f'''
            <tr style="border: 1px solid #ddd;">
                <td style="padding: 8px; font-weight: bold;">Estimated Annual Income:</td>
                <td style="padding: 8px;">{annual_rent}</td>
            </tr>
            '''
    
    if rental_yield and rental_yield != "N/A":
        html += f'''
        <tr style="border: 1px solid #ddd; background-color: #fff;">
            <td style="padding: 8px; font-weight: bold;">Gross Rental Yield:</td>
            <td style="padding: 8px; color: #28a745; font-weight: bold;">{rental_yield}</td>
        </tr>
        '''
    
    if roi and roi != "N/A":
        html += f'''
        <tr style="border: 1px solid #ddd;">
            <td style="padding: 8px; font-weight: bold;">ROI:</td>
            <td style="padding: 8px; color: #28a745; font-weight: bold;">{roi}</td>
        </tr>
        '''
    
    if metric_status and metric_status != "N/A":
        html += f'''
        <tr style="border: 1px solid #ddd; background-color: #fff;">
            <td style="padding: 8px; font-weight: bold;">Calculation Method:</td>
            <td style="padding: 8px; font-size: 0.9em; color: #666;">{metric_status}</td>
        </tr>
        '''
    
    html += '</table>\n'
    html += '<p style="margin-top: 15px; font-size: 0.85em; color: #666;"><em>💡 Note: Investment metrics are estimates based on market averages and should be verified independently.</em></p>\n'
    html += '</div>\n'
    
    return html

# -------------------------------
# POST LISTINGS TO WORDPRESS
# -------------------------------
success, skipped, failed = 0, 0, 0
total_images_uploaded = 0
total_images_failed = 0

print("\n" + "="*70)
print("🚀 STARTING WORDPRESS UPLOAD WITH ACF FIELDS")
print("="*70 + "\n")

for idx, row in df.head(MAX_UPLOADS).iterrows():
    title = clean_value(row.get("title", ""))
    price = clean_value(row.get("price", ""))
    link = clean_value(row.get("link", ""))
    source = clean_value(row.get("source", ""))
    category = clean_value(row.get("category", "Unknown"))
    image_urls_str = clean_value(row.get("image_urls_str", ""))
    description = clean_value(row.get("description", "No description available"))
    address = clean_value(row.get("address", ""))
    agent = clean_value(row.get("agent", ""))
    bedrooms = clean_value(row.get("bedrooms", ""))
    bathrooms = clean_value(row.get("bathrooms", ""))
    city = clean_value(row.get("city", ""))

    print(f"\n{'='*70}")
    print(f"[{idx + 1}/{min(MAX_UPLOADS, len(df))}] {title[:60]}")
    print(f"{'='*70}")
    
    if not title or not link:
        print("⚠ Missing title or link, skipping...")
        skipped += 1
        continue

    # Skip duplicates
    if title.lower() in existing_titles or link.lower() in existing_links:
        print(f"⏭ Already exists, skipping")
        skipped += 1
        continue

    # Upload all images
    uploaded_images = []
    if image_urls_str:
        uploaded_images = upload_multiple_images(image_urls_str)
        total_images_uploaded += len(uploaded_images)
        
        # Count how many failed
        num_urls = len([u for u in image_urls_str.split('|') if u.strip()])
        total_images_failed += (num_urls - len(uploaded_images))
    else:
        print("  ℹ No images available")

    # Set featured image (first uploaded image)
    featured_media_id = None
    if uploaded_images:
        featured_media_id = uploaded_images[0]["id"]
        print(f"  ⭐ Featured image set (ID: {featured_media_id})")

    # Build image gallery HTML (for images after the first one)
    gallery_html = build_image_gallery_html(uploaded_images)

    # Format description properly
    formatted_description = format_description_for_display(description)
    
    # Build financial metrics HTML
    financial_html = build_financial_metrics_html(row)

    # Build full content HTML
    content_html = f"""
        <div class="property-details">
            <h3>📋 Property Information</h3>
            <table style="width:100%; border-collapse: collapse;">
                <tr style="border: 1px solid #ddd;">
                    <td style="padding: 8px; font-weight: bold; width: 30%;">Price:</td>
                    <td style="padding: 8px;">{price if price else 'Contact for price'}</td>
                </tr>
                <tr style="border: 1px solid #ddd; background-color: #f9f9f9;">
                    <td style="padding: 8px; font-weight: bold;">Category:</td>
                    <td style="padding: 8px;"><span style="background: #007bff; color: white; padding: 3px 10px; border-radius: 3px;">{category}</span></td>
                </tr>
                <tr style="border: 1px solid #ddd;">
                    <td style="padding: 8px; font-weight: bold;">Location:</td>
                    <td style="padding: 8px;">{city if city else 'Not specified'}</td>
                </tr>
                <tr style="border: 1px solid #ddd; background-color: #f9f9f9;">
                    <td style="padding: 8px; font-weight: bold;">Address:</td>
                    <td style="padding: 8px;">{address if address else 'Not available'}</td>
                </tr>
                <tr style="border: 1px solid #ddd;">
                    <td style="padding: 8px; font-weight: bold;">Bedrooms:</td>
                    <td style="padding: 8px;">{bedrooms if bedrooms else 'Not specified'}</td>
                </tr>
                <tr style="border: 1px solid #ddd; background-color: #f9f9f9;">
                    <td style="padding: 8px; font-weight: bold;">Bathrooms:</td>
                    <td style="padding: 8px;">{bathrooms if bathrooms else 'Not specified'}</td>
                </tr>
                <tr style="border: 1px solid #ddd;">
                    <td style="padding: 8px; font-weight: bold;">Agent/Publisher:</td>
                    <td style="padding: 8px;">{agent if agent else 'Not specified'}</td>
                </tr>
            </table>
            
            {financial_html}
            
            {gallery_html}
            
            <hr style="margin: 20px 0;">
            
            <h3>🏠 Property Description</h3>
            {formatted_description}
            
            <hr style="margin: 20px 0;">
            
            <p><strong>🔗 Original Listing:</strong> <a href="{link}" target="_blank" rel="noopener">View on {source.split('//')[1].split('/')[0] if '//' in source else source}</a></p>
        </div>
    """

    # Build ACF data
    acf_data = build_acf_data(row)

    # Prepare post data
    post_data = {
        "title": title,
        "status": "publish",
        "content": content_html,
        "acf": acf_data
    }

    if featured_media_id:
        post_data["featured_media"] = featured_media_id

    try:
        print(f"  📤 Publishing to WordPress with ACF fields...")
        r = requests.post(
            WP_URL, 
            json=post_data, 
            auth=HTTPBasicAuth(USERNAME, APP_PASSWORD),
            timeout=30
        )
        
        if r.status_code == 201:
            prop_id = r.json().get("id")
            print(f"  ✅ SUCCESS! (ID: {prop_id})")
            print(f"     📍 {city if city else 'N/A'} | 🛏 {bedrooms if bedrooms else 'N/A'}bd | 🛁 {bathrooms if bathrooms else 'N/A'}ba | 🖼 {len(uploaded_images)} images")
            print(f"     💰 Yield: {row.get('gross_rental_yield', 'N/A')} | ROI: {row.get('roi_percentage', 'N/A')}")
            success += 1
        elif r.status_code == 400 and "existing" in r.text.lower():
            print(f"  ⚠ Duplicate detected by WordPress")
            skipped += 1
        else:
            print(f"  ❌ Failed ({r.status_code})")
            print(f"     {r.text[:200]}")
            failed += 1
    except Exception as e:
        print(f"  ❌ Error: {e}")
        failed += 1

    time.sleep(SLEEP_BETWEEN)

# -------------------------------
# SUMMARY
# -------------------------------
print("\n" + "="*70)
print("📊 FINAL SUMMARY")
print("="*70)
print(f"✅ Successfully uploaded: {success} properties")
print(f"🖼 Total images uploaded: {total_images_uploaded}")
print(f"⚠ Images failed: {total_images_failed}")
print(f"📊 Average images per property: {total_images_uploaded/success:.1f}" if success > 0 else "📊 No successful uploads")
print(f"⏭ Skipped (duplicates): {skipped}")
print(f"❌ Failed: {failed}")
print("="*70)
print("\n📋 ACF Fields Populated:")
for acf_field in ACF_FIELDS.keys():
    print(f"   ✓ {acf_field}")
print("="*70)
print("🏁 Upload complete!")
print("="*70)