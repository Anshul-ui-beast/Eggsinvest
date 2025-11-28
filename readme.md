# 🏠 EggsInvest - UK Property Investment Aggregator

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/streamlit-latest-FF4B4B.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Aggregate, analyze, and upload UK property listings from 40+ websites to WordPress with enriched data, images, and investment metrics.**

EggsInvest is an intelligent property aggregation platform that scrapes listings from major UK property portals (Rightmove, Zoopla, Nestoria, OnTheMarket, etc.) and automatically posts them to WordPress with comprehensive descriptions, multiple images, and financial investment metrics.

---

## 📋 Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Running the Scraper](#running-the-scraper)
  - [Uploading to WordPress](#uploading-to-wordpress)
- [Supported Websites](#supported-websites)
- [Output Format](#output-format)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## ✨ Features

### 🔍 **Intelligent Web Scraping**
- Scrapes **40+ UK property websites** simultaneously
- Dual-mode scraping: requests + Selenium for dynamic sites
- Multi-threaded concurrent processing for speed
- Smart fallback mechanisms for resilience

### 📸 **Multi-Image Extraction**
- Extracts **up to 5 high-quality images** per property
- Intelligent gallery/carousel detection
- Automatic lazy-loading attribute handling (data-src, data-lazy-src)
- Responsive image (srcset) support
- Image validation (dimensions, file size, MIME type)
- Automatic logo/icon/avatar filtering

### 📝 **Rich Property Data**
- Comprehensive property descriptions formatted as paragraphs
- Property address and location extraction
- Agent/publisher information
- Bedroom and bathroom count detection
- Price extraction with frequency (PCM, PW, etc.)
- Automatic "For Sale" vs "For Rent" categorization

### 💰 **Investment Metrics Support**
- Gross rental yield calculation display
- ROI percentage tracking
- Estimated property value
- Annual rental income projections
- Estimated monthly rent
- Financial metrics formatting for WordPress display

### 📊 **WordPress Integration**
- Batch upload to WordPress REST API
- ACF (Advanced Custom Fields) field population
- Automatic featured image assignment
- Property image gallery HTML generation
- Duplicate detection by title and source URL
- Comprehensive HTML content formatting

### 🎨 **Streamlit Dashboard**
- Real-time progress monitoring
- Live statistics (images per property, success rates)
- Configurable settings (threads, fetch limits, headless mode)
- Separate dataframes for all/sale/rent listings
- CSV export functionality

---

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/Anshul-ui-beast/Eggsinvest.git
cd Eggsinvest
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env with your WordPress credentials
```

### 5. Run Scraper
```bash
streamlit run scraperv12.py
```

### 6. Upload to WordPress
```bash
python upload_to_wordpress.py
```

---

## 🏗️ Architecture

### System Overview
```
┌─────────────────────────────────────────────────────────────────┐
│                    UK Property Websites (40+)                   │
│  Rightmove │ Zoopla │ Nestoria │ Gumtree │ OpenRent │ etc...   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Web Scraper    │
                    │  (scraperv12.py)│
                    │                 │
                    │ • Requests lib  │
                    │ • Selenium      │
                    │ • BeautifulSoup │
                    └────────┬────────┘
                             │
              ┌──────────────▼──────────────┐
              │      CSV Output Files       │
              │ • property_listings_all.csv │
              │ • property_listings_sale.csv│
              │ • property_listings_rent.csv│
              └──────────────┬──────────────┘
                             │
                 ┌───────────▼───────────┐
                 │ WordPress Uploader    │
                 │(upload_to_wordpress.py)
                 │                       │
                 │ • Image upload        │
                 │ • ACF field mapping   │
                 │ • HTML formatting     │
                 │ • Duplicate detection │
                 └───────────┬───────────┘
                             │
                    ┌────────▼────────┐
                    │ WordPress CMS   │
                    │ • Properties    │
                    │ • Media Gallery │
                    │ • Custom Fields │
                    └─────────────────┘
```

### Data Flow
1. **Scraper** identifies properties on search pages
2. **Detail Extractor** fetches each property's full page
3. **Image Extractor** downloads multiple high-quality images
4. **Data Processor** cleans and formats information
5. **CSV Exporter** saves structured data
6. **WordPress Uploader** posts to your website
7. **Duplicate Detector** prevents re-uploads

---

## 📦 Installation

### Requirements
- **Python**: 3.8 or higher
- **Chrome/Chromium**: Required for Selenium (auto-installed via webdriver-manager)
- **WordPress**: 5.0+ with REST API enabled
- **ACF Plugin**: Advanced Custom Fields Pro/Free

### Step-by-Step

1. **Clone the repository**
```bash
git clone https://github.com/Anshul-ui-beast/Eggsinvest.git
cd Eggsinvest
```

2. **Create virtual environment**
```bash
python -m venv venv

# Activate on macOS/Linux:
source venv/bin/activate

# Activate on Windows:
venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. **Verify installations**
```bash
python -c "import streamlit; print(f'Streamlit {streamlit.__version__}')"
python -c "import selenium; print('Selenium installed')"
python -c "import pandas; print('Pandas installed')"
```

### Dependencies (requirements.txt)
```
streamlit>=1.28.0
pandas>=1.5.0
requests>=2.31.0
beautifulsoup4>=4.12.0
selenium>=4.10.0
webdriver-manager>=4.0.0
Pillow>=10.0.0
feedparser>=6.0.0
```

---

## ⚙️ Configuration

### Environment Variables (.env)
Create a `.env` file in the project root:

```bash
# WordPress Configuration
WP_URL=https://your-domain.com/wp-json/wp/v2/property
MEDIA_URL=https://your-domain.com/wp-json/wp/v2/media
WP_USERNAME=your_wordpress_username
WP_PASSWORD=your_app_password

# Scraper Settings
HEADLESS=True
REQUEST_TIMEOUT=10
MAX_THREADS=10
SITES_PER_PAGE_LIMIT=60
DESC_AND_IMAGE_FETCH_LIMIT=30
MAX_IMAGES_PER_PROPERTY=5

# Image Validation
MIN_IMAGE_SIZE=5000
MIN_IMAGE_WIDTH=200
MIN_IMAGE_HEIGHT=150

# Upload Settings
MAX_UPLOADS=50
SLEEP_BETWEEN=2
```

### WordPress Setup

1. **Enable REST API** (usually enabled by default)
```
Settings → Permalinks → (choose any except "Plain")
```

2. **Create App Password**
```
Users → Your Profile → Scroll to "App Passwords"
Enter an app name (e.g., "EggsInvest Scraper")
Copy the generated password
```

3. **Create Property Custom Post Type**
```php
// Add to functions.php or use plugin like CPT UI
register_post_type('property', [
    'label' => 'Properties',
    'public' => true,
    'show_in_rest' => true,
    'supports' => ['title', 'editor', 'thumbnail', 'custom-fields']
]);
```

4. **Set up ACF Fields**
Create these ACF fields for the "property" post type:
- `ere_single_property_header_price_location` (Text) - Price
- `property_category` (Select) - For Sale/For Rent
- `_ere_property_address` (Text) - Full address
- `property_city` (Text) - City/Town
- `ere_property_bedrooms` (Number) - Bedroom count
- `ere_property_bathrooms` (Number) - Bathroom count
- `property_agent` (Text) - Agent name
- `property_source_url` (URL) - Original listing link
- `property_source_site` (Text) - Website name
- `gross_rental_yield` (Number) - Yield percentage
- `roi_percentage` (Number) - ROI percentage
- `estimated_property_value` (Number) - Estimated value
- `annual_rental_income` (Number) - Annual income
- `estimated_monthly_rent` (Number) - Monthly rent estimate

---

## 💻 Usage

### Running the Scraper

#### Via Streamlit Dashboard (Recommended)
```bash
streamlit run scraperv12.py
```

This opens an interactive dashboard where you can:
- Adjust thread count (2-15)
- Set details per site (10-50)
- Configure images per property (1-10)
- Toggle headless mode
- View real-time progress with statistics
- Download CSV files

#### Customizing Scraper Behavior
Edit settings in `scraperv12.py`:

```python
HEADLESS = True                    # Run without browser window
REQUEST_TIMEOUT = 10               # Seconds per request
MAX_THREADS = 10                   # Concurrent site processing
SITES_PER_PAGE_LIMIT = 60          # Listings per site
DESC_AND_IMAGE_FETCH_LIMIT = 30    # Details to fetch per site
MAX_IMAGES_PER_PROPERTY = 5        # Images per property
```

#### Output Files
After scraping, three CSV files are generated:
- `property_listings_all.csv` - All properties
- `property_listings_sale.csv` - For sale only
- `property_listings_rent.csv` - For rent only

**CSV Columns**:
```
title, price, link, source, published, category, image_urls_str,
description, address, agent, bedrooms, bathrooms, city
```

### Uploading to WordPress

#### Basic Upload
```bash
python upload_to_wordpress.py
```

The script will:
1. Load data from `property_listings_all.csv` (configurable)
2. Validate WordPress connection
3. Check for duplicates
4. Upload images to media library
5. Create property posts with ACF fields
6. Generate progress report

#### Monitoring Upload
```bash
# Watch the console output for:
# ✅ Successfully uploaded: X properties
# 🖼 Total images uploaded: Y
# ⏭ Skipped (duplicates): Z
# ❌ Failed: W
```

#### Selecting CSV Source
Edit `upload_to_wordpress.py`:

```python
CSV_FILES = {
    "all": "property_listings_all.csv",
    "sale": "property_listings_sale.csv", 
    "rent": "property_listings_rent.csv"
}

CSV_FILE = CSV_FILES["sale"]  # Change as needed
```

#### Setting Upload Limit
```python
MAX_UPLOADS = 50  # Upload maximum 50 properties per run
```

---

## 🌐 Supported Websites

### Major Portals (40+ websites)
The scraper supports aggregation from:

**Major Portals**
- ✅ Rightmove.co.uk
- ✅ Zoopla.co.uk
- ✅ OnTheMarket.com
- ✅ PrimeLocation.com

**Independent Platforms**
- ✅ Boomin.com
- ✅ Nestoria.co.uk
- ✅ Gumtree.com/property
- ✅ OpenRent.co.uk
- ✅ TheHouseShop.com

**Estate Agents**
- ✅ KnightFrank.co.uk
- ✅ Hamptons.co.uk
- ✅ Strutts & Parker
- ✅ Chestertons.co.uk
- ✅ Winkworth.co.uk
- ✅ Your Move
- ✅ Reeds Rains
- ✅ Connells
- ✅ Countrywide
- ✅ Bairstow Eves
- ✅ Belvoir
- ✅ Hunters
- ✅ Yopa
- ✅ PurpleBricks
- ✅ Jackson Stops
- ✅ Dexters
- ✅ Fine & Country
- ✅ Haart
- ✅ McCarthy & Stone

**Commercial/Specialist**
- ✅ JLL.co.uk
- ✅ CBRE.co.uk
- ✅ TheModernHouse.com
- ✅ PropertyPal.com
- ✅ PropertyHeads.com
- ✅ MousePrice.com
- ✅ FindAProperty.com
- ✅ Mashroom.co.uk
- ✅ Carter Jonas
- ✅ MoveHut.co.uk
- ✅ Home.co.uk

**Commercial Property**
- ✅ Rightmove Commercial
- ✅ Zoopla Commercial

---

## 📤 Output Format

### CSV Structure
```csv
title,price,link,source,published,category,image_urls_str,description,address,agent,bedrooms,bathrooms,city
"Beautiful 2-bed flat in Camden","£950,000","https://rightmove.co.uk/...","https://www.rightmove.co.uk/","N/A","For Sale","https://img1.jpg|https://img2.jpg|https://img3.jpg","Spacious period conversion...","42 Camden High Street, London","Foxtons","2","1","London"
```

### WordPress Post Format
Each property creates a WordPress post with:

**Post Title**: Property title/address
**Post Content**: Formatted HTML with:
- Property information table (price, beds, baths, location)
- Financial metrics (if applicable)
- Photo gallery (if multiple images)
- Property description
- Link to original listing

**Featured Image**: First uploaded property image

**ACF Fields**: Custom property data

**Example HTML Output**:
```html
<div class="property-details">
    <h3>📋 Property Information</h3>
    <table>
        <tr><td>Price:</td><td>£950,000</td></tr>
        <tr><td>Category:</td><td>For Sale</td></tr>
        <tr><td>Location:</td><td>London</td></tr>
        <tr><td>Bedrooms:</td><td>2</td></tr>
        <tr><td>Bathrooms:</td><td>1</td></tr>
    </table>
    
    <h3>💰 Investment Metrics</h3>
    <!-- Rental yield, ROI, etc. -->
    
    <div class="property-gallery">
        <!-- Additional images -->
    </div>
    
    <h3>🏠 Property Description</h3>
    <!-- Description paragraphs -->
</div>
```

---

## 🔧 API Reference

### Scraper Functions

#### `extract_listings_from_soup(soup, base_url)`
Extracts basic property listings from search results page.

**Parameters**:
- `soup` (BeautifulSoup): Parsed HTML
- `base_url` (str): Base URL for relative links

**Returns**: List of dict with keys: title, price, link, image_urls, description, address, agent, bedrooms, bathrooms, city

#### `extract_details_from_listing_page(detail_url)`
Fetches comprehensive property data from detail page.

**Parameters**:
- `detail_url` (str): Full URL to property listing

**Returns**: Dict with keys: description, image_urls, address, agent, bedrooms, bathrooms, city

#### `extract_multiple_images(soup, detail_url, max_images=5)`
Extracts multiple high-quality images from property page.

**Parameters**:
- `soup` (BeautifulSoup): Parsed HTML
- `detail_url` (str): Base URL for relative image links
- `max_images` (int): Maximum images to extract (default: 5)

**Returns**: List of image URLs

#### `extract_bedrooms(text)`
Detects bedroom count from text.

**Parameters**:
- `text` (str): Text to search

**Returns**: Bedroom count as string, or "N/A"

#### `extract_bathrooms(text)`
Detects bathroom count from text.

**Parameters**:
- `text` (str): Text to search

**Returns**: Bathroom count as string, or "N/A"

### Uploader Functions

#### `upload_image(image_url, image_index=1)`
Downloads and uploads single image to WordPress media library.

**Parameters**:
- `image_url` (str): Image URL to download
- `image_index` (int): Index for logging (default: 1)

**Returns**: Dict with keys: id, url (media ID and URL), or None if failed

#### `upload_multiple_images(image_urls_str)`
Processes pipe-separated image URLs and uploads all.

**Parameters**:
- `image_urls_str` (str): Pipe-separated URLs (e.g., "url1|url2|url3")

**Returns**: List of uploaded image dicts

#### `build_acf_data(row)`
Maps CSV row to WordPress ACF fields.

**Parameters**:
- `row` (dict): CSV row data

**Returns**: Dict of ACF field names → values

---

## 🐛 Troubleshooting

### Issue: "Chrome/Chromium not found"
**Solution**:
```bash
# webdriver-manager should auto-install, but if it doesn't:
pip install --upgrade webdriver-manager
python -c "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()"
```

### Issue: "Connection timeout"
**Solution**:
```python
# Increase timeout in scraperv12.py:
REQUEST_TIMEOUT = 20  # Increase from 10 to 20 seconds
```

### Issue: "WordPress authentication failed"
**Solution**:
1. Verify app password is correctly copied (no extra spaces)
2. Check WordPress username is correct
3. Ensure REST API is enabled:
   ```
   Settings → Permalinks → (select any structure except Plain)
   ```
4. Test connection manually:
```bash
curl -u "username:password" https://your-site.com/wp-json/wp/v2/property?per_page=1
```

### Issue: "No listings found"
**Possible causes**:
- Website structure changed (selectors outdated)
- Website blocking requests (rate limiting)
- Dynamic content not loading

**Solutions**:
```python
# Increase wait time for Selenium:
time.sleep(10)  # Change from 5 to 10 seconds

# Add Selenium processing to fallback_scrape:
listings = selenium_scrape(site)

# Add custom headers:
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.google.com"
}
```

### Issue: "Images not uploading to WordPress"
**Solution**:
1. Check image size is >= MIN_IMAGE_SIZE (5000 bytes)
2. Verify image dimensions (>= 200x150 pixels)
3. Check WordPress upload limits:
   ```
   Settings → Media → File upload size
   ```
4. Verify media folder permissions:
```bash
chmod -R 755 /path/to/wp-content/uploads/
```

### Issue: "Duplicate detection not working"
**Solution**:
Update the ACF field check in `upload_to_wordpress.py`:
```python
# Ensure acf is dict, not list
if isinstance(acf, dict):
    source_url = acf.get("property_source_url", "")
```

### Issue: "CSV shows 'Pending' for descriptions"
**Solution**:
Increase `DESC_AND_IMAGE_FETCH_LIMIT` in Streamlit sidebar or config:
```python
DESC_AND_IMAGE_FETCH_LIMIT = 50  # Fetch more details
```

---

## 📊 Performance Tips

### For Large-Scale Scraping (500+ properties)

1. **Increase threads** (use cautiously):
```python
MAX_THREADS = 15  # Increase from 10
```

2. **Parallel image uploads**:
```python
with ThreadPoolExecutor(max_workers=4) as ex:
    # Process multiple images concurrently
```

3. **Use database instead of CSV**:
```python
import sqlite3
db = sqlite3.connect('properties.db')
# Store properties in DB for faster deduplication
```

4. **Run overnight**:
```bash
# Schedule via cron (Linux/Mac)
0 2 * * * /path/to/venv/bin/python /path/to/upload_to_wordpress.py

# Or Task Scheduler (Windows)
# Task: Run upload_to_wordpress.py at 2:00 AM daily
```

### For Faster WordPress Uploads

1. **Reduce MAX_UPLOADS per batch**:
```python
MAX_UPLOADS = 25  # Process in smaller batches
```

2. **Increase SLEEP_BETWEEN** if hitting rate limits:
```python
SLEEP_BETWEEN = 5  # Add delay between uploads
```

3. **Disable featured image for all but primary**:
```python
# Comment out: post_data["featured_media"] = featured_media_id
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. **Fork the repository**
```bash
git clone https://github.com/YOUR-USERNAME/Eggsinvest.git
cd Eggsinvest
```

2. **Create a feature branch**
```bash
git checkout -b feature/amazing-feature
```

3. **Make your changes** and add tests

4. **Commit with clear messages**
```bash
git commit -m "Add support for new website XYZ"
```

5. **Push to branch**
```bash
git push origin feature/amazing-feature
```

6. **Open a Pull Request** with description of changes

### Areas for Contribution
- Add support for new property websites
- Improve image extraction algorithms
- Add financial calculation features
- Write unit tests
- Improve documentation
- Add support for other CMS platforms (Drupal, etc.)

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

- **Respect robots.txt**: Always check website terms of service before scraping
- **Rate limiting**: This tool implements delays to avoid overloading servers
- **Terms of Service**: Some websites prohibit scraping. Use responsibly
- **Data accuracy**: Financial metrics are estimates and should be verified independently
- **Legal compliance**: Ensure compliance with UK data protection laws (GDPR, etc.)

---

## 📞 Support & Contact

- **Issues**: Report bugs on [GitHub Issues](https://github.com/Anshul-ui-beast/Eggsinvest/issues)
- **Discussions**: Join conversations on [GitHub Discussions](https://github.com/Anshul-ui-beast/Eggsinvest/discussions)
- **Email**: [Your email if available]

---

## 🙏 Acknowledgments

Built with:
- [Streamlit](https://streamlit.io/) - Dashboard interface
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing
- [Selenium](https://selenium.dev/) - Dynamic content rendering
- [Pandas](https://pandas.pydata.org/) - Data processing
- [Requests](https://requests.readthedocs.io/) - HTTP library

---

## 📈 Roadmap

- [ ] Database backend (SQLite/PostgreSQL)
- [ ] API for third-party integrations
- [ ] Mobile app for monitoring uploads
- [ ] Real-time property alerts
- [ ] Machine learning for property valuations
- [ ] Support for international properties
- [ ] Advanced filtering and search
- [ ] Automated scheduled scraping

---

**Made with ❤️ for UK property investors**