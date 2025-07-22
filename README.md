# scrape_this 🔗

**Extract ALL links from web applications** - A powerful CLI tool built with Python, using Typer for the CLI interface and Scrapling for advanced scraping capabilities with anti-bot detection.

The primary goal of this tool is to comprehensively extract every link found on web applications, with advanced filtering, source detection, and analysis capabilities.

## 🚀 Quick Start

```bash
# Install with pipx (recommended)
pipx install .

# Extract all links from a single page
scrape_this scrape https://example.com --depth 0

# Crawl entire website and extract ALL links
scrape_this scrape https://example.com --depth 3

# Extract only PDF files across a website
scrape_this scrape https://example.com -e "pdf" --links-only
```

## ✨ Key Features

- **🔗 Comprehensive Link Extraction**: Extract ALL links from web applications with a single command
- **📍 Source Detection**: Automatically identify where each link was found (navigation, header, footer, main content, sidebar, etc.)
- **🎯 Smart Filtering**: Filter by internal/external domains, link types, file extensions
- **📊 Multiple Output Formats**: Export to JSON, CSV, HTML, or view as formatted tables
- **🔍 Link Analysis**: Automatically categorize links by type (images, documents, pages, media, etc.)
- **✅ Link Validation**: Check if links are accessible with HTTP status codes (optional)
- **🌐 JavaScript Support**: Render JavaScript-heavy SPAs with headless browser automation
- **🕷️ Recursive Crawling**: Crawl entire websites with depth control and page limits
- **💬 Comment Extraction**: Extract HTML and JavaScript comments for security analysis
- **🎨 Rich Terminal Output**: Beautiful progress indicators and formatted results
- **🔧 Authentication Support**: Custom headers for APIs and authenticated endpoints

## Installation

### Option 1: Using pipx (Recommended)

[pipx](https://pypa.github.io/pipx/) installs the tool in an isolated environment and makes it available globally:

```bash
# Install pipx if you haven't already
python -m pip install --user pipx
python -m pipx ensurepath

# Install scrape_this
pipx install .

# Or install from a git repository
pipx install git+https://github.com/yourusername/scrape_this.git
```

After installation, you can use `scrape_this` directly from anywhere:

```bash
scrape_this scrape https://example.com
scrape_this spider https://example.com --depth 2
scrape_this --help
```

### Option 2: Using pip

```bash
pip install .

# Or install from requirements file for development
pip install -r requirements.txt
```

### Option 3: Development Installation

For development or if you want to modify the code:

```bash
git clone https://github.com/yourusername/scrape_this.git
cd scrape_this
pip install -e .
```

### Verify Installation

```bash
scrape_this version
```

### JavaScript Mode Setup (Optional)

For JavaScript rendering (`--js` flag), you need to install browser dependencies:

```bash
# Install browser dependencies for JavaScript support
scrapling install

# Or install Camoufox manually
pip install camoufox
camoufox fetch
```

If JavaScript mode is not set up, the tool will automatically fall back to regular HTTP fetching with a warning.

## Usage

### 🔗 Link Extraction (Primary Use Case)

```bash
# Extract all links from a webpage
scrape_this links https://example.com

# Get only internal links as JSON
scrape_this links https://example.com --internal-only -f json

# Get only external links and save to CSV
scrape_this links https://example.com --external-only -o external_links.csv

# Get only subdomain links
scrape_this links https://example.com --subdomains-only

# Include subdomains as internal links
scrape_this links https://example.com --include-subdomains --internal-only

# See detailed progress and link breakdown
scrape_this links https://example.com --show-progress

# Filter by file types (images, documents, etc.)
scrape_this links https://example.com --filter images -f json
scrape_this links https://example.com --filter "pdf,doc,docx" -o documents.csv

# Filter by specific file extensions (Scrapy-inspired)
scrape_this links https://example.com --extensions "pdf,zip,exe"
scrape_this links https://example.com -e "docx,pptx,xlsx" -o office_files.csv

# Validate links (check if accessible)
scrape_this links https://example.com --validate --internal-only

# Extract links with JavaScript rendering
scrape_this links https://example.com --js

# Include duplicate links
scrape_this links https://example.com --allow-duplicates
```

### 📍 Link Source Detection

Each extracted link includes a `source` field indicating where it was found on the page:

| Source Type | Description | Common Examples |
|-------------|-------------|-----------------|
| `navigation` | Main navigation menus | Home, About, Products, Services |
| `header` | Page headers and top sections | Login, Register, Account links |
| `footer` | Page footers | Privacy Policy, Terms, Contact |
| `main_content` | Article/content areas | "Read more", inline article links |
| `sidebar` | Sidebar sections | Related articles, categories |
| `breadcrumb` | Breadcrumb navigation | Home > Category > Page |
| `content` | General page content | Any other content links |
| `unknown` | Could not be determined | Dynamically loaded content |

Example output with source detection:
```json
{
  "url": "https://example.com/privacy",
  "text": "Privacy Policy",
  "source": "footer",
  "is_internal": true,
  "link_type": "page"
}

### 🔗 Primary Link Extraction (Default Mode)

```bash
# Extract all links from a single page
scrape_this scrape https://example.com --depth 0

# Crawl entire website and gather ALL links  
scrape_this scrape https://example.com --depth 3 --max-pages 100

# Find all downloadable files across website
scrape_this scrape https://example.com -e "pdf,docx,zip,exe" --links-only

# Get all external links for SEO analysis
scrape_this scrape https://mysite.com --external-only --validate -f csv

# JavaScript-heavy app with full analysis
scrape_this scrape https://spa.example.com --js --include-comments --depth 2
```

### 📄 Content Extraction Mode

```bash
# Extract page content instead of links
scrape_this scrape https://example.com --content-only

# Extract specific elements with CSS selector
scrape_this scrape https://example.com --selector "h1, h2" -f json

# JavaScript rendering with screenshot
scrape_this scrape https://example.com --content-only --js --screenshot page.png

# Extract comments from source code
scrape_this scrape https://example.com --content-only --include-comments --comment-type javascript
```

### 💬 Comment Extraction Integration

```bash
# Include comments in link extraction
scrape_this scrape https://example.com --include-comments --depth 2

# Extract comments across entire website during crawling
scrape_this scrape https://example.com --include-comments --depth 3 --comment-type javascript

# Get only HTML comments with content extraction
scrape_this scrape https://example.com --content-only --include-comments --comment-type html -f json

# Filter JavaScript comments by minimum length
scrape_this scrape https://spa-site.com --content-only --include-comments --comment-type javascript --min-comment-length 20
```

### Structured Data Extraction

Create a rules file (e.g., `rules.json`):

```json
{
    "title": {"selector": "h1", "attribute": "text"},
    "price": {"selector": ".price", "attribute": "text"},
    "image": {"selector": "img.product", "attribute": "src"},
    "features": {"selector": "li.feature", "attribute": "text", "all": true}
}
```

Then extract data:

```bash
scrape_this extract https://shop.example.com/product rules.json -o product.json

# With JavaScript rendering and custom headers
scrape_this extract https://spa-site.com/data rules.json --js --wait 2.0 --headers '{"X-API-Key": "secret"}'
```

### Advanced Options

```bash
# Custom headers
scrape_this scrape https://api.example.com --headers '{"Authorization": "Bearer TOKEN"}'

# Limit results
scrape_this scrape https://example.com -s ".item" --limit 10

# Export as CSV
scrape_this scrape https://example.com -s "table tr" -f csv -o data.csv
```

## Commands

- `scrape`: **🔗 Extract ALL links from web applications** (primary command)
- `links`: Extract links from a single webpage with advanced filtering  
- `extract`: Extract structured data using custom rules
- `version`: Show version information

## 📤 Output Formats & Examples

### Available Formats

- **`table`**: Rich formatted table (default for links command) - Great for terminal viewing
- **`json`**: JSON format - Perfect for programmatic processing
- **`csv`**: CSV format - Ideal for spreadsheet analysis
- **`html`**: HTML table format - For web reports

### Example JSON Output

```json
{
  "crawl_info": {
    "start_url": "https://example.com",
    "pages_crawled": 5,
    "max_depth": 2,
    "total_links": 127,
    "files_found": 15
  },
  "links": [
    {
      "url": "https://example.com/docs/guide.pdf",
      "text": "Download User Guide",
      "domain": "example.com",
      "path": "/docs/guide.pdf",
      "is_internal": true,
      "is_subdomain": false,
      "link_type": "document",
      "source": "main_content",
      "original_href": "/docs/guide.pdf",
      "found_on_page": "https://example.com/support"
    },
    {
      "url": "https://cdn.example.com/images/logo.png",
      "text": "",
      "domain": "cdn.example.com",
      "is_internal": false,
      "is_subdomain": true,
      "link_type": "image",
      "source": "header",
      "found_on_page": "https://example.com"
    }
  ]
}
```

## Link Classification & Filtering

### 🏠 Domain Classification

The tool automatically classifies links by domain relationship:

- **Internal**: Same domain as the source (including www variants)
- **Subdomain**: Subdomains of the source domain (e.g., `api.example.com` when source is `example.com`)
- **External**: Different domains entirely

### 🗂️ Link Types

The `links` command automatically categorizes links into types:

- **`page`**: Regular web pages (no file extension)
- **`image`**: Image files (.jpg, .png, .gif, .svg, etc.)
- **`document`**: Documents (.pdf, .doc, .docx, .xls, etc.)
- **`video`**: Video files (.mp4, .avi, .mkv, etc.)
- **`audio`**: Audio files (.mp3, .wav, .flac, etc.)
- **`archive`**: Compressed files (.zip, .rar, .tar, etc.)
- **`code`**: Code files (.js, .css, .json, .html, etc.)
- **`api`**: API endpoints (contain 'api' or query parameters)
- **`other`**: Everything else

### Filter Groups

You can also use these convenient filter groups:

- **`images`**: All image types
- **`documents`**: All document types  
- **`media`**: Video and audio files
- **`files`**: All downloadable files
- **`pages`**: Regular web pages
- **`code`**: Code and markup files

## Examples

### 🔗 Link Extraction Use Cases

```bash
# Extract all downloadable files from a website
scrape_this links https://example.com --filter files -o all_files.json

# Find all PDF documents
scrape_this links https://research-site.com --filter pdf -f csv

# Get all external links for SEO analysis  
scrape_this links https://mysite.com --external-only -o external_links.csv

# Extract all images from a gallery
scrape_this links https://gallery.example.com --filter images --validate

# Find internal navigation links
scrape_this links https://example.com --internal-only --filter pages

# Extract all media files (audio + video)
scrape_this links https://media-site.com --filter media -f json

# Get all subdomain links (API endpoints, CDNs, etc.)
scrape_this links https://example.com --subdomains-only --show-progress

# Comprehensive link analysis with progress details
scrape_this links https://example.com --show-progress -o all_links.json
```

### 📄 Real-World Examples

#### SEO Analysis
```bash
# Find all external links for backlink analysis
scrape_this scrape https://mysite.com --external-only --validate -o external_links.csv

# Analyze internal link structure
scrape_this scrape https://mysite.com --internal-only --depth 3 -o site_structure.json

# Find orphaned pages (pages with no internal links)
scrape_this scrape https://mysite.com --depth 5 --internal-only -f json
```

#### Asset Discovery
```bash
# Find all PDFs on a website
scrape_this scrape https://example.com -e "pdf" --links-only -o all_pdfs.csv

# Locate all media files (images, videos, audio)
scrape_this scrape https://example.com --filter media --depth 3

# Find all downloadable documents
scrape_this scrape https://docs.example.com --filter documents --max-pages 200
```

#### Security & Development
```bash
# Extract all JavaScript comments for security review
scrape_this scrape https://app.example.com --include-comments --comment-type javascript

# Find all API endpoints
scrape_this scrape https://example.com --filter api --depth 2

# Discover all form actions and endpoints
scrape_this scrape https://example.com --selector "form" --content-only
```

#### Site Migration
```bash
# Complete site inventory before migration
scrape_this scrape https://old-site.com --depth 10 --max-pages 1000 -o full_inventory.json

# Find all image assets for migration
scrape_this scrape https://old-site.com --filter images --links-only -o all_images.csv

# Identify all subdomains and external dependencies
scrape_this scrape https://example.com --subdomains-only --depth 3
```

## Why Use pipx?

**pipx** is the recommended way to install CLI tools because it:

- ✅ **Isolated environments**: Each tool gets its own virtual environment
- ✅ **Global access**: Tools are available from anywhere on your system
- ✅ **Easy updates**: `pipx upgrade scrape_this` to update
- ✅ **Easy removal**: `pipx uninstall scrape_this` to remove completely  
- ✅ **No conflicts**: Dependencies don't interfere with your system Python

## Uninstalling

```bash
# If installed with pipx
pipx uninstall scrape_this

# If installed with pip
pip uninstall scrape_this
```

## 💡 Performance & Best Practices

### Performance Tips

1. **Start Small**: Test with `--depth 0` or `--depth 1` before full crawls
2. **Use Filters Early**: Apply `--internal-only` or extension filters to reduce processing
3. **Set Page Limits**: Use `--max-pages` to prevent infinite crawls
4. **Skip JavaScript**: Only use `--js` when necessary (it's slower)
5. **Export Formats**: Use JSON for further processing, CSV for spreadsheets

### Best Practices

1. **Respect robots.txt**: Check site policies before crawling
2. **Use Rate Limiting**: Don't overwhelm servers with rapid requests
3. **Filter Smartly**: Combine filters for precise results (e.g., `--internal-only -e "pdf"`)
4. **Validate Selectively**: Use `--validate` only when needed (it's slower)
5. **Save Raw Data**: Export to JSON first, then filter/analyze offline
6. **Monitor Progress**: Use `--show-progress` for long crawls

### Advanced Usage

```bash
# Combine multiple filters for precise extraction
scrape_this scrape https://example.com \
  --internal-only \
  --filter documents \
  --extensions "pdf,docx" \
  --max-pages 100 \
  --validate \
  -o important_docs.json

# Use custom headers for authenticated scraping
scrape_this scrape https://api.example.com \
  --headers '{"Authorization": "Bearer YOUR_TOKEN"}' \
  --depth 2 \
  -o api_endpoints.json
```

## Requirements

- Python 3.8+
- typer[all]
- scrapling
- rich
- pandas

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests: `python -m pytest` (if available)
5. Submit a pull request

## License

MIT