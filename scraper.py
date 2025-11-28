import re
import time
import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import feedparser
except Exception:
    feedparser = None

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ------------------------------- SETTINGS -------------------------------
HEADLESS = True
REQUEST_TIMEOUT = 10
MAX_THREADS = 10
SITES_PER_PAGE_LIMIT = 60
DESC_AND_IMAGE_FETCH_LIMIT = 30
MAX_IMAGES_PER_PROPERTY = 5  # Number of images to fetch per property

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ------------------------------- WEBSITE LIST -------------------------------
AGENT_SITES = [
    "https://www.rightmove.co.uk/",
    "https://www.zoopla.co.uk/",
    "https://www.onthemarket.com/",
    "https://www.primelocation.com/",
    "https://www.boomin.com/",
    "https://www.nestoria.co.uk/",
    "https://www.gumtree.com/property-to-rent/",
    "https://www.openrent.co.uk/",
    "https://www.thehouseshop.com/",
    "https://www.knightfrank.co.uk/",
    "https://www.hamptons.co.uk/",
    "https://www.struttandparker.com/",
    "https://www.chestertons.co.uk/",
    "https://www.winkworth.co.uk/",
    "https://www.your-move.co.uk/",
    "https://www.reedsrains.co.uk/",
    "https://www.connells.co.uk/",
    "https://www.countrywide.co.uk/",
    "https://www.bairstoweves.co.uk/",
    "https://www.belvoir.co.uk/",
    "https://www.hunters.com/",
    "https://www.yopa.co.uk/",
    "https://www.purplebricks.co.uk/",
    "https://www.jackson-stops.co.uk/",
    "https://www.dexters.co.uk/",
    "https://www.jll.co.uk/",
    "https://www.cbre.co.uk/",
    "https://www.fineandcountry.com/",
    "https://www.haart.co.uk/",
    "https://www.mccarthyandstone.co.uk/",
    "https://www.themodernhouse.com/",
    "https://www.propertypal.com/",
    "https://www.propertyheads.com/",
    "https://www.mouseprice.com/",
    "https://www.findaproperty.com/",
    "https://www.mashroom.co.uk/",
    "https://www.carterjonas.co.uk/",
    "https://www.movehut.co.uk/",
    "https://www.home.co.uk/",
    "https://www.rightmove.co.uk/commercial-property.html/",
    "https://www.zoopla.co.uk/for-sale/commercial-property/",
    "https://thenegotiator.co.uk/",
]

# ------------------------------- FILTERS -------------------------------
NEWS_KEYWORDS = {
    "news", "blog", "press", "article", "insight", "update", "story",
    "advice", "guide", "report", "market", "event", "tips", "announcement"
}

DYNAMIC_DOMAINS = {
    "rightmove.co.uk", "zoopla.co.uk", "onthemarket.com",
    "primelocation.com", "purplebricks.co.uk",
}

# ------------------------------- HELPERS -------------------------------
def is_listing(title, link):
    text = f"{title} {link}".lower()
    if any(k in text for k in NEWS_KEYWORDS):
        return False
    if not any(k in text for k in ["for sale", "to rent", "flat", "house", "£", "property", "apartment", "studio"]):
        return False
    return True

def categorize_listing(title, link):
    text = f"{title} {link}".lower()
    if any(k in text for k in ["for sale", "buy", "sale"]):
        return "For Sale"
    if any(k in text for k in ["to rent", "for rent", "letting", "lease"]):
        return "For Rent"
    return "Unknown"

def extract_bedrooms(text):
    """Extract bedroom count from text"""
    patterns = [
        r'(\d+)\s*(?:bed|bedroom|bed-?room)s?(?:\s|,|$)',
        r'(\d+)\s*br\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return match.group(1)
    return "N/A"

def extract_bathrooms(text):
    """Extract bathroom count from text"""
    patterns = [
        r'(\d+)\s*(?:bath|bathroom|bath-?room)s?(?:\s|,|$)',
        r'(\d+)\s*ba\b',
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return match.group(1)
    return "N/A"

def extract_city_from_text(text):
    """Try to extract city/town from text"""
    common_locations = [
        "London", "Manchester", "Birmingham", "Leeds", "Glasgow",
        "Bristol", "Edinburgh", "Liverpool", "Newcastle", "Sheffield",
        "Cambridge", "Oxford", "York", "Bath", "Brighton", "Canterbury",
        "Windsor", "Kew", "Surrey", "Sussex", "Kent", "Essex"
    ]
    for location in common_locations:
        if location.lower() in text.lower():
            return location
    return "N/A"

def clean_description_text(text):
    """Clean and format description text into proper paragraphs"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common non-descriptive prefixes
    text = re.sub(r'^(Property details|Description|About|Details)[\s:]+', '', text, flags=re.IGNORECASE)
    
    # Split into sentences (approximately)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Group sentences into paragraphs (every 3-4 sentences)
    paragraphs = []
    current_para = []
    
    for i, sentence in enumerate(sentences):
        if sentence.strip():
            current_para.append(sentence.strip())
            
            # Create paragraph break every 3-4 sentences
            if len(current_para) >= 3 and (i % 4 == 0 or i == len(sentences) - 1):
                paragraphs.append(' '.join(current_para))
                current_para = []
    
    # Add remaining sentences
    if current_para:
        paragraphs.append(' '.join(current_para))
    
    # Join paragraphs with proper spacing
    final_text = '\n\n'.join(paragraphs)
    
    return final_text if final_text else "No description available"

def extract_comprehensive_description(soup, detail_url):
    """
    Extract comprehensive property description from multiple sources.
    Priority: Main description > Summary > Key features > All text blocks
    """
    description_text = ""
    
    # Strategy 1: Look for main description section
    description_patterns = [
        ("Main Description", lambda s: s.find(
            ["div", "section", "article"],
            class_=lambda x: x and any(k in x.lower() for k in [
                "description", "property-description", "property-detail",
                "details", "summary", "about", "property-text"
            ])
        )),
        ("Meta Description", lambda s: s.find("meta", attrs={"name": "description"})),
        ("OG Description", lambda s: s.find("meta", attrs={"property": "og:description"})),
    ]
    
    for strategy_name, pattern_func in description_patterns:
        tag = pattern_func(soup)
        if tag:
            if tag.name == "meta":
                text = tag.get("content", "")
            else:
                text = tag.get_text(" ", strip=True)
            
            if len(text) > 50:
                description_text = text
                break
    
    # Strategy 2: If no main description, collect key features and highlights
    if not description_text or len(description_text) < 50:
        features = []
        
        # Look for bullet points, lists
        for ul in soup.find_all(["ul", "ol"]):
            if any(k in str(ul.get("class", [])).lower() for k in ["feature", "highlight", "specification", "spec"]):
                for li in ul.find_all("li", limit=10):
                    text = li.get_text(strip=True)
                    if text:
                        features.append(text)
        
        if features:
            description_text = "Key Features: " + "; ".join(features)
    
    # Strategy 3: If still no description, gather all meaningful paragraphs
    if not description_text or len(description_text) < 50:
        paragraphs = soup.find_all("p")
        text_blocks = []
        
        for p in paragraphs:
            text = p.get_text(" ", strip=True)
            # Filter out navigation text, very short text, and obvious non-descriptive elements
            if len(text) > 80 and not any(k in text.lower() for k in [
                "click here", "read more", "contact", "cookie", "javascript", "search"
            ]):
                text_blocks.append(text)
        
        if text_blocks:
            description_text = " ".join(text_blocks)
    
    # Clean and format the description
    if description_text:
        # Limit to reasonable length
        description_text = description_text[:5000]
        description_text = clean_description_text(description_text)
    else:
        description_text = "No description available"
    
    return description_text

# ------------------------------- IMAGE EXTRACTION (MULTIPLE) -------------------------------
def extract_image_url_from_tag(img_tag, base_url):
    """Extract best quality image URL from an img tag"""
    if not img_tag:
        return None
    
    possible_attrs = [
        'data-src', 'data-lazy-src', 'data-original', 'data-lazy',
        'data-full-url', 'data-large-src', 'srcset', 'src'
    ]
    
    for attr in possible_attrs:
        if img_tag.get(attr):
            url = img_tag[attr]
            
            # Handle srcset
            if attr == 'srcset':
                srcset_parts = url.split(',')
                url = srcset_parts[-1].strip().split()[0]
            
            full_url = urljoin(base_url, url)
            
            # Skip placeholders
            if any(x in full_url.lower() for x in ['loading', 'placeholder', 'blank', '1x1', 'pixel']):
                continue
            
            if full_url.startswith('data:'):
                continue
            
            return full_url
    
    return None

def extract_multiple_images(soup, detail_url, max_images=5):
    """Extract multiple high-quality images from property listing"""
    images = []
    seen_urls = set()
    
    # Strategy 1: Find gallery/carousel containers
    gallery_containers = soup.find_all(
        ["div", "section", "ul"],
        class_=lambda x: x and any(k in x.lower() for k in [
            "gallery", "carousel", "slider", "photos", "images",
            "property-images", "image-gallery", "photo-gallery"
        ])
    )
    
    # Extract images from galleries
    for container in gallery_containers:
        img_tags = container.find_all("img", limit=max_images * 2)
        for img_tag in img_tags:
            if len(images) >= max_images:
                break
            
            img_url = extract_image_url_from_tag(img_tag, detail_url)
            if img_url and img_url not in seen_urls:
                # Skip logos, icons, etc.
                if any(skip in img_url.lower() for skip in ["logo", "icon", "avatar", "agent"]):
                    continue
                images.append(img_url)
                seen_urls.add(img_url)
    
    # Strategy 2: If not enough images, find all property-related images
    if len(images) < max_images:
        all_property_imgs = soup.find_all(
            "img",
            class_=lambda x: x and any(k in x.lower() for k in [
                "property", "photo", "image", "picture"
            ])
        )
        
        for img_tag in all_property_imgs:
            if len(images) >= max_images:
                break
            
            img_url = extract_image_url_from_tag(img_tag, detail_url)
            if img_url and img_url not in seen_urls:
                if any(skip in img_url.lower() for skip in ["logo", "icon", "avatar", "agent"]):
                    continue
                images.append(img_url)
                seen_urls.add(img_url)
    
    # Strategy 3: If still not enough, get any decent sized images
    if len(images) < max_images:
        all_imgs = soup.find_all("img", src=True)
        for img_tag in all_imgs:
            if len(images) >= max_images:
                break
            
            img_url = extract_image_url_from_tag(img_tag, detail_url)
            if img_url and img_url not in seen_urls:
                if any(skip in img_url.lower() for skip in ["logo", "icon", "avatar", "agent", "banner"]):
                    continue
                images.append(img_url)
                seen_urls.add(img_url)
    
    return images

# ------------------------------- DETAIL PAGE SCRAPER -------------------------------
def extract_details_from_listing_page(detail_url):
    """
    Fetch comprehensive property description, MULTIPLE images, address, agent, bedrooms, bathrooms, and city
    from the actual listing detail page.
    """
    result = {
        "description": "No description available",
        "image_urls": [],  # Now a list of URLs
        "address": "N/A",
        "agent": "N/A",
        "bedrooms": "N/A",
        "bathrooms": "N/A",
        "city": "N/A"
    }
    
    try:
        resp = requests.get(detail_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")

        # ===== EXTRACT COMPREHENSIVE DESCRIPTION =====
        result["description"] = extract_comprehensive_description(soup, detail_url)

        # ===== EXTRACT ADDRESS =====
        address_patterns = [
            lambda s: s.find(["h1", "h2"], class_=lambda x: x and any(k in x.lower() for k in ["address", "title", "heading"])),
            lambda s: s.find("span", class_=lambda x: x and "address" in x.lower()),
            lambda s: s.find("div", class_=lambda x: x and "address" in x.lower()),
        ]
        
        for pattern in address_patterns:
            address_tag = pattern(soup)
            if address_tag:
                result["address"] = address_tag.get_text(strip=True)
                break

        # ===== EXTRACT AGENT/PUBLISHER =====
        agent_patterns = [
            lambda s: s.find("div", class_=lambda x: x and any(k in x.lower() for k in ["agent", "agency", "seller", "publisher"])),
            lambda s: s.find("p", class_=lambda x: x and "agent" in x.lower()),
            lambda s: s.find("span", class_=lambda x: x and "agent" in x.lower()),
        ]
        
        for pattern in agent_patterns:
            agent_tag = pattern(soup)
            if agent_tag:
                result["agent"] = agent_tag.get_text(strip=True)[:150]
                break

        # ===== EXTRACT BEDROOM & BATHROOM COUNT =====
        full_text = soup.get_text(" ", strip=True)
        result["bedrooms"] = extract_bedrooms(full_text)
        result["bathrooms"] = extract_bathrooms(full_text)

        # ===== EXTRACT CITY/TOWN =====
        if result["address"] != "N/A":
            result["city"] = extract_city_from_text(result["address"])
        if result["city"] == "N/A":
            result["city"] = extract_city_from_text(full_text)

        # ===== EXTRACT MULTIPLE HIGH-RES IMAGES =====
        result["image_urls"] = extract_multiple_images(soup, detail_url, MAX_IMAGES_PER_PROPERTY)

    except Exception as e:
        print(f"    ⚠ Error fetching details from {detail_url}: {e}")
    
    return result

# ------------------------------- SEARCH PAGE SCRAPER -------------------------------
def extract_listings_from_soup(soup, base_url):
    """Extract basic listing info from search results page"""
    listings = []
    containers = soup.find_all(
        ["article", "div", "li"],
        class_=lambda x: x and any(k in x.lower() for k in ["property", "listing", "result", "card", "search-result"])
    )
    if not containers:
        containers = soup.find_all(["div", "li", "article"])

    for c in containers:
        text = c.get_text(" ", strip=True)
        if "£" not in text:
            continue

        a = c.find("a", href=True)
        if not a:
            continue
        link = urljoin(base_url, a["href"])
        title = a.get_text(strip=True) or "Property Listing"

        if not is_listing(title, link):
            continue

        price_match = re.search(r"£\s?[\d,]+(?:\s?(?:pcm|pw|per month|per week))?", text)
        price = price_match.group(0) if price_match else "N/A"

        listings.append({
            "title": title,
            "price": price,
            "link": link,
            "image_urls": [],  # Will be filled with multiple images
            "description": "Pending",
            "address": "N/A",
            "agent": "N/A",
            "bedrooms": "N/A",
            "bathrooms": "N/A",
            "city": "N/A"
        })
        
        if len(listings) >= SITES_PER_PAGE_LIMIT:
            break
    
    return listings

# ------------------------------- SCRAPE HELPERS -------------------------------
def fallback_scrape(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")
        return extract_listings_from_soup(soup, url)
    except Exception:
        return []

def make_driver():
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1400,900")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(25)
    return driver

def selenium_scrape(url):
    try:
        driver = make_driver()
        driver.get(url)
        time.sleep(5)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()
        return extract_listings_from_soup(soup, url)
    except Exception as e:
        print(f"Selenium error: {e}")
        return []

# ------------------------------- PROCESSOR -------------------------------
def process_site(site):
    domain = urlparse(site).netloc.replace("www.", "")
    print(f"\n🔍 Processing: {site}")
    
    listings = fallback_scrape(site)
    if not listings and domain in DYNAMIC_DOMAINS:
        print(f"  ⚙ Using Selenium for {domain}...")
        listings = selenium_scrape(site)

    print(f"  📋 Found {len(listings)} listings on search page")

    print(f"  🔎 Fetching details (limit: {DESC_AND_IMAGE_FETCH_LIMIT})...")
    
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(extract_details_from_listing_page, item["link"]): item 
            for item in listings[:DESC_AND_IMAGE_FETCH_LIMIT]
        }
        
        for fut in as_completed(futures):
            item = futures[fut]
            try:
                details = fut.result()
                item["description"] = details["description"]
                item["image_urls"] = details["image_urls"]
                item["address"] = details["address"]
                item["agent"] = details["agent"]
                item["bedrooms"] = details["bedrooms"]
                item["bathrooms"] = details["bathrooms"]
                item["city"] = details["city"]
                
                img_count = len(details["image_urls"])
                desc_len = len(details["description"]) if details["description"] else 0
                if img_count > 0:
                    print(f"    ✅ {item['title'][:35]} - {img_count} images, {desc_len} chars, {details['bedrooms']}bd {details['bathrooms']}ba")
                else:
                    print(f"    ⚠ {item['title'][:35]} - No images, {desc_len} chars")
            except Exception as e:
                print(f"    ❌ Error: {e}")

    for i in listings[DESC_AND_IMAGE_FETCH_LIMIT:]:
        i["description"] = "Not fetched (limit reached)"

    for i in listings:
        i["source"] = site
        i["published"] = "N/A"
        i["category"] = categorize_listing(i["title"], i["link"])

    return listings

# ------------------------------- STREAMLIT UI -------------------------------
st.set_page_config(page_title="UK Property Dashboard (Enhanced Descriptions)", layout="wide", page_icon="🏠")
st.title("🏠 UK Property Dashboard — v12 (Enhanced Descriptions & Multiple Images)")
st.caption("Now extracting comprehensive descriptions formatted as paragraphs + up to 5 high-quality images per property!")

st.sidebar.subheader("Settings")
HEADLESS = st.sidebar.checkbox("Run Selenium headless", value=True)
max_threads = st.sidebar.slider("Max concurrent sites", 2, 15, MAX_THREADS)
DESC_AND_IMAGE_FETCH_LIMIT = st.sidebar.slider("Details per site", 10, 50, 30)
MAX_IMAGES_PER_PROPERTY = st.sidebar.slider("Images per property", 1, 10, 5)

data = []

with ThreadPoolExecutor(max_workers=max_threads) as executor:
    futures = {executor.submit(process_site, site): site for site in AGENT_SITES}
    for fut in as_completed(futures):
        site = futures[fut]
        try:
            rows = fut.result()
            if rows:
                total_images = sum(len(r.get('image_urls', [])) for r in rows)
                st.success(f"✅ {site} — {len(rows)} listings ({total_images} total images)")
                data.extend(rows)
            else:
                st.warning(f"⚠ {site} — no listings found")
        except Exception as e:
            st.error(f"❌ {site} — error: {e}")

if data:
    df = pd.DataFrame(data)
    
    # Convert image_urls list to pipe-separated string for CSV compatibility
    df['image_urls_str'] = df['image_urls'].apply(lambda x: '|'.join(x) if isinstance(x, list) else '')
    
    total = len(df)
    with_images = sum(1 for urls in df['image_urls'] if isinstance(urls, list) and len(urls) > 0)
    total_images = sum(len(urls) for urls in df['image_urls'] if isinstance(urls, list))
    avg_images = total_images / with_images if with_images > 0 else 0
    
    st.info(f"📊 Stats: {with_images}/{total} properties have images | {total_images} total images | {avg_images:.1f} avg per property")
    
    # Display dataframe with string version of image URLs
    display_df = df.drop('image_urls', axis=1)
    
    st.subheader("📋 All Listings")
    st.dataframe(display_df, use_container_width=True)

    st.subheader("🏠 For Sale Listings")
    st.dataframe(display_df[display_df["category"] == "For Sale"], use_container_width=True)

    st.subheader("🏡 For Rent Listings")
    st.dataframe(display_df[display_df["category"] == "For Rent"], use_container_width=True)

    # Save with pipe-separated image URLs
    display_df.to_csv("property_listings_all.csv", index=False)
    display_df[display_df["category"] == "For Sale"].to_csv("property_listings_sale.csv", index=False)
    display_df[display_df["category"] == "For Rent"].to_csv("property_listings_rent.csv", index=False)

    st.success(f"💾 Saved CSVs with comprehensive descriptions and multiple images per property (pipe-separated)!")
else:
    st.info("No property data retrieved yet.")