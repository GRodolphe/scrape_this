#!/usr/bin/env python3
"""
scrape_this - A powerful web scraping tool using Scrapling
"""
import json
import csv
import re
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
from urllib.parse import urlparse, urljoin, urlunparse

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from scrapling.fetchers import Fetcher, StealthyFetcher
import pandas as pd

app = typer.Typer(
    name="scrape_this", 
    help="Extract ALL links from web applications - powered by Scrapling",
    add_completion=False
)
console = Console()


class OutputFormat(str, Enum):
    json = "json"
    csv = "csv"
    table = "table"
    html = "html"


class ScrapeConfig:
    """Configuration for scraping operations"""
    def __init__(self, headers: Optional[Dict[str, str]] = None):
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }


def get_fetcher_class(stealth: bool = False):
    """Get the appropriate fetcher class"""
    if stealth:
        return StealthyFetcher
    return Fetcher


@app.command()
def links(
    url: str = typer.Argument(..., help="URL to extract links from"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    format: OutputFormat = typer.Option(OutputFormat.table, "--format", "-f", help="Output format"),
    javascript: bool = typer.Option(False, "--js", help="Enable JavaScript rendering"),
    headers: Optional[str] = typer.Option(None, "--headers", "-h", help="Custom headers as JSON string"),
    internal_only: bool = typer.Option(False, "--internal-only", help="Only extract internal links (same domain)"),
    external_only: bool = typer.Option(False, "--external-only", help="Only extract external links (different domains)"),
    subdomains_only: bool = typer.Option(False, "--subdomains-only", help="Only extract subdomain links"),
    include_subdomains: bool = typer.Option(False, "--include-subdomains", help="Treat subdomains as internal links"),
    unique_only: bool = typer.Option(True, "--unique/--allow-duplicates", help="Remove duplicate links"),
    validate: bool = typer.Option(False, "--validate", help="Check if links are accessible (slower)"),
    show_progress: bool = typer.Option(True, "--show-progress/--no-progress", help="Show detailed progress information"),
    filter_types: Optional[str] = typer.Option(None, "--filter", help="Filter by link types (e.g., 'pdf,jpg,png' or 'images,documents')"),
    extensions: Optional[str] = typer.Option(None, "--extensions", "-e", help="Filter by file extensions (e.g., 'pdf,docx,zip')")
):
    """
    Extract all links from a webpage
    
    Examples:
        scrape_this links https://example.com
        scrape_this links https://example.com --internal-only -f json
        scrape_this links https://example.com --subdomains-only
        scrape_this links https://example.com --include-subdomains --internal-only
        scrape_this links https://example.com --validate --filter images
        scrape_this links https://example.com --extensions "pdf,docx,zip"
        scrape_this links https://example.com --external-only -o external_links.csv
    """
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Extracting links...", total=None)
            
            # Use StealthyFetcher for JavaScript rendering or regular Fetcher otherwise
            fetcher_class = get_fetcher_class(stealth=javascript)
            if javascript:
                fetcher_class.auto_match = True
            
            custom_headers = None
            if headers:
                try:
                    custom_headers = json.loads(headers)
                except json.JSONDecodeError:
                    console.print("[red]Error: Invalid JSON format for headers[/red]")
                    raise typer.Exit(1)
            
            config = ScrapeConfig(headers=custom_headers)
            
            if javascript:
                # StealthyFetcher doesn't accept headers parameter directly
                if custom_headers:
                    console.print("[yellow]Warning: Custom headers are not supported in JavaScript mode (--js). Using default stealth headers.[/yellow]")
                try:
                    response = fetcher_class.fetch(
                        url,
                        headless=True,
                        network_idle=True
                    )
                except Exception as e:
                    console.print(f"[yellow]Warning: JavaScript mode failed ({str(e)}). Falling back to regular fetching.[/yellow]")
                    response = Fetcher.get(url, headers=config.headers, stealthy_headers=True)
            else:
                response = fetcher_class.get(url, headers=config.headers, stealthy_headers=True)
            
            # Extract all links using enhanced extraction function
            base_domain = urlparse(url).netloc
            all_links = extract_links_from_page(response, url, base_domain, include_subdomains)
            
            
            # Show progress if requested
            if show_progress and all_links:
                console.print(f"[cyan]Found {len(all_links)} total links before filtering[/cyan]")
                
                # Show breakdown by type
                internal_count = len([l for l in all_links if l['is_internal']])
                subdomain_count = len([l for l in all_links if l['is_subdomain'] and not l['is_internal']])
                external_count = len([l for l in all_links if not l['is_internal'] and not l['is_subdomain']])
                
                console.print(f"[green]  • Internal: {internal_count}[/green]")
                console.print(f"[yellow]  • Subdomains: {subdomain_count}[/yellow]")
                console.print(f"[red]  • External: {external_count}[/red]")
                
                # Show breakdown by link type
                type_counts = {}
                for link in all_links:
                    link_type = link['link_type']
                    type_counts[link_type] = type_counts.get(link_type, 0) + 1
                
                console.print("[blue]Link types found:[/blue]")
                for link_type, count in sorted(type_counts.items()):
                    console.print(f"  • {link_type}: {count}")

            # Apply filters
            filtered_links = all_links
            
            # Filter by internal/external/subdomains
            if internal_only:
                filtered_links = [link for link in filtered_links if link['is_internal']]
            elif external_only:
                filtered_links = [link for link in filtered_links if not link['is_internal'] and not link['is_subdomain']]
            elif subdomains_only:
                filtered_links = [link for link in filtered_links if link['is_subdomain']]
            
            # Filter by link types
            if filter_types:
                type_filters = [t.strip().lower() for t in filter_types.split(',')]
                filtered_links = filter_by_types(filtered_links, type_filters)
            
            # Filter by file extensions (Scrapy POC inspired)
            if extensions:
                extension_filters = [ext.strip().lower().lstrip('.') for ext in extensions.split(',')]
                filtered_links = filter_by_extensions(filtered_links, extension_filters)
            
            # Remove duplicates if requested
            if unique_only:
                seen_urls = set()
                unique_links = []
                for link in filtered_links:
                    if link['url'] not in seen_urls:
                        seen_urls.add(link['url'])
                        unique_links.append(link)
                filtered_links = unique_links
            
            # Validate links if requested
            if validate:
                progress.update(progress.task_ids[0], description="Validating links...")
                filtered_links = validate_links(filtered_links, config.headers)
            
            console.print(f"\n[green]Found {len(filtered_links)} links[/green]")
            output_results(filtered_links, format, output)
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


def is_subdomain_of(domain: str, base_domain: str) -> bool:
    """Check if domain is a subdomain of base_domain"""
    if not domain or not base_domain or domain == base_domain:
        return False
    
    # Remove www. prefix for comparison
    domain_clean = domain.replace('www.', '')
    base_clean = base_domain.replace('www.', '')
    
    if domain_clean == base_clean:
        return False
    
    # Check if domain ends with .base_domain
    return domain_clean.endswith('.' + base_clean)


def is_same_or_subdomain(domain: str, base_domain: str) -> bool:
    """Check if domain is the same or a subdomain of base_domain (handles www prefix)"""
    if not domain or not base_domain:
        return False
    
    # Remove www. prefix for comparison
    domain_clean = domain.replace('www.', '')
    base_clean = base_domain.replace('www.', '')
    
    # Same domain (after removing www)
    if domain_clean == base_clean:
        return True
        
    # Check if it's a subdomain
    return domain_clean.endswith('.' + base_clean)


def get_link_type(url: str) -> str:
    """Determine the type of link based on URL patterns"""
    
    parsed = urlparse(url)
    path = parsed.path.lower()
    
    # Get file extension
    file_ext = Path(path).suffix.lower()
    
    # Image types
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico'}
    if file_ext in image_extensions:
        return 'image'
    
    # Document types
    doc_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf'}
    if file_ext in doc_extensions:
        return 'document'
    
    # Video types
    video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
    if file_ext in video_extensions:
        return 'video'
    
    # Audio types
    audio_extensions = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma'}
    if file_ext in audio_extensions:
        return 'audio'
    
    # Archive types
    archive_extensions = {'.zip', '.rar', '.tar', '.gz', '.7z', '.bz2'}
    if file_ext in archive_extensions:
        return 'archive'
    
    # Code/Script types
    code_extensions = {'.js', '.css', '.json', '.xml', '.html', '.htm', '.php', '.py', '.java'}
    if file_ext in code_extensions:
        return 'code'
    
    # API or query endpoints
    if '?' in parsed.query or 'api' in path:
        return 'api'
    
    # If no extension, likely a page
    if not file_ext:
        return 'page'
    
    return 'other'


def filter_by_extensions(links: list, extension_filters: list) -> list:
    """Filter links by file extensions (like Scrapy POC's interesting_extensions)"""
    filtered = []
    
    for link in links:
        url = link['url'].lower()
        # Check if URL ends with any of the specified extensions
        if any(url.endswith('.' + ext) for ext in extension_filters):
            filtered.append(link)
    
    return filtered


def filter_by_types(links: list, type_filters: list) -> list:
    """Filter links by specified types"""
    filtered = []
    
    # Define type groups
    type_groups = {
        'images': ['image'],
        'documents': ['document'],
        'media': ['video', 'audio'],
        'pages': ['page'],
        'files': ['document', 'image', 'video', 'audio', 'archive'],
        'code': ['code'],
        'api': ['api']
    }
    
    # Expand group filters
    expanded_filters = set()
    for filter_type in type_filters:
        if filter_type in type_groups:
            expanded_filters.update(type_groups[filter_type])
        else:
            expanded_filters.add(filter_type)
    
    # Also check for file extensions directly
    for link in links:
        link_type = link['link_type']
        url = link['url'].lower()
        
        # Check if link type matches
        if link_type in expanded_filters:
            filtered.append(link)
        # Check if any filter matches file extension
        elif any(f".{filter_ext}" in url for filter_ext in type_filters):
            filtered.append(link)
    
    return filtered


def validate_links(links: list, headers: dict) -> list:
    """Validate links by checking if they're accessible"""
    
    validated_links = []
    
    for i, link in enumerate(links):
        try:
            # Simple HEAD request to check if link is accessible
            response = Fetcher.get(link['url'], headers=headers, method='HEAD')
            status_code = getattr(response, 'status_code', getattr(response, 'status', 0))
            
            link['status_code'] = status_code
            link['is_accessible'] = status_code < 400
            
            # Add some delay to avoid overwhelming servers
            if i > 0 and i % 10 == 0:
                time.sleep(0.5)
                
        except Exception as e:
            link['status_code'] = 0
            link['is_accessible'] = False
            link['error'] = str(e)
        
        validated_links.append(link)
    
    return validated_links



@app.command()
def scrape(
    url: str = typer.Argument(..., help="Starting URL to crawl"),
    depth: int = typer.Option(2, "--depth", "-d", help="Maximum crawl depth"),
    max_pages: int = typer.Option(50, "--max-pages", "-m", help="Maximum number of pages to crawl"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    format: OutputFormat = typer.Option(OutputFormat.json, "--format", "-f", help="Output format"),
    javascript: bool = typer.Option(False, "--js", help="Enable JavaScript rendering"),
    headers: Optional[str] = typer.Option(None, "--headers", "-h", help="Custom headers as JSON string"),
    
    # Content extraction options
    selector: Optional[str] = typer.Option(None, "--selector", "-s", help="CSS selector to extract specific elements"),
    content_only: bool = typer.Option(False, "--content-only", help="Extract page content instead of links"),
    screenshot: Optional[Path] = typer.Option(None, "--screenshot", help="Save a screenshot of the page (requires --js)"),
    
    # Link filtering options
    internal_only: bool = typer.Option(False, "--internal-only", help="Only extract internal links"),
    external_only: bool = typer.Option(False, "--external-only", help="Only extract external links"),
    subdomains_only: bool = typer.Option(False, "--subdomains-only", help="Only extract subdomain links"),
    include_subdomains: bool = typer.Option(True, "--include-subdomains/--no-subdomains", help="Treat subdomains as internal links"),
    
    # File/extension filtering
    extensions: Optional[str] = typer.Option(None, "--extensions", "-e", help="Filter by file extensions (e.g., 'pdf,docx,zip')"),
    filter_types: Optional[str] = typer.Option(None, "--filter", help="Filter by link types (e.g., 'images,documents')"),
    
    # Analysis options
    validate: bool = typer.Option(False, "--validate", help="Check if links are accessible (slower)"),
    unique_only: bool = typer.Option(True, "--unique/--allow-duplicates", help="Remove duplicate links"),
    show_progress: bool = typer.Option(True, "--show-progress/--no-progress", help="Show detailed progress information"),
    
    # Output options
    links_only: bool = typer.Option(False, "--links-only", help="Output only links, not page metadata"),
    include_comments: bool = typer.Option(False, "--include-comments", help="Extract and include comments from HTML and JavaScript"),
    comment_type: Optional[str] = typer.Option(None, "--comment-type", help="Filter comment type: html, javascript, js_single, js_multi"),
    min_comment_length: int = typer.Option(0, "--min-comment-length", help="Minimum comment length to include"),
    summary: bool = typer.Option(True, "--summary/--no-summary", help="Show crawl summary at the end")
):
    """
    🔗 Extract ALL links from web applications with comprehensive analysis
    
    This is the primary command for gathering ALL links found on a web application.
    It can work on single pages (depth=0) or recursively crawl entire sites.
    
    Core functionality:
    - Extract every link from target web applications
    - Single-page mode (--depth 0) or full site crawling
    - Advanced link filtering by type, domain, extensions
    - JavaScript-heavy site support with headless browser
    - Comment extraction from HTML and JavaScript code
    - Link validation and accessibility checking
    - Multiple output formats for analysis
    
    Examples:
        # Extract all links from a single page
        scrape_this scrape https://example.com --depth 0
        
        # Crawl entire website and gather all links
        scrape_this scrape https://example.com --depth 3 --max-pages 100
        
        # Find all downloadable files across website
        scrape_this scrape https://example.com -e "pdf,docx,zip,exe" --links-only
        
        # Get all external links for SEO analysis
        scrape_this scrape https://mysite.com --external-only --validate -f csv
        
        # JavaScript-heavy app with comment extraction
        scrape_this scrape https://spa.example.com --js --include-comments --depth 2
    """
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            crawl_task = progress.add_task(description="Starting link extraction...", total=None)
            
            # Setup fetcher
            fetcher_class = get_fetcher_class(stealth=javascript)
            if javascript:
                fetcher_class.auto_match = True
            
            custom_headers = None
            if headers:
                try:
                    custom_headers = json.loads(headers)
                except json.JSONDecodeError:
                    console.print("[red]Error: Invalid JSON format for headers[/red]")
                    raise typer.Exit(1)
            
            config = ScrapeConfig(headers=custom_headers)
            
            # Handle content-only mode (single page extraction)
            if content_only or selector:
                progress.update(crawl_task, description="Extracting content from single page...")
                
                # Fetch the page
                if javascript:
                    if custom_headers:
                        console.print("[yellow]Warning: Custom headers not supported in JS mode[/yellow]")
                    try:
                        response = fetcher_class.fetch(url, headless=True, network_idle=True)
                    except Exception as e:
                        console.print(f"[yellow]JS mode failed: {str(e)}. Falling back...[/yellow]")
                        response = Fetcher.get(url, headers=config.headers, stealthy_headers=True)
                else:
                    response = fetcher_class.get(url, headers=config.headers, stealthy_headers=True)
                
                # Handle screenshot
                if screenshot:
                    try:
                        if javascript:
                            response.screenshot(screenshot)
                            console.print(f"[green]Screenshot saved to: {screenshot}[/green]")
                        else:
                            console.print("[yellow]Warning: Screenshots require --js flag[/yellow]")
                    except Exception as e:
                        console.print(f"[yellow]Warning: Could not take screenshot: {str(e)}[/yellow]")
                
                results = []
                
                if selector:
                    # Extract specific elements with CSS selector
                    try:
                        elements = response.css(selector)
                        for elem in elements:
                            try:
                                text_content = ""
                                if hasattr(elem, 'text'):
                                    text_content = elem.text or ""
                                elif hasattr(elem, 'get_text'):
                                    text_content = elem.get_text() or ""
                                else:
                                    text_content = str(elem)
                                
                                attrs = elem.attrs if hasattr(elem, 'attrs') else {}
                                
                                data = {
                                    'text': text_content,
                                    'html': str(elem),
                                    'attributes': attrs
                                }
                                
                                try:
                                    if hasattr(elem, 'href'):
                                        data['href'] = elem.href
                                    elif 'href' in attrs:
                                        data['href'] = attrs['href']
                                except:
                                    pass
                                
                                results.append(data)
                            except Exception:
                                continue
                    except Exception as e:
                        console.print(f"[red]Error parsing selector: {str(e)}[/red]")
                        raise typer.Exit(1)
                else:
                    # Extract full page content
                    try:
                        # Get page text content
                        page_text = ''
                        try:
                            body_adaptors = response.css('body')
                            if body_adaptors and hasattr(body_adaptors, 'text'):
                                page_text = body_adaptors.text.strip()
                        except:
                            pass
                        
                        if not page_text:
                            try:
                                page_text = response.text if hasattr(response, 'text') else str(response)
                            except:
                                page_text = 'Could not extract text content'
                        
                        # Get title
                        title = ''
                        try:
                            title_adaptors = response.css('title')
                            title = title_adaptors.text if hasattr(title_adaptors, 'text') else str(title_adaptors)
                        except:
                            pass
                        
                        result_data = {
                            'url': url,
                            'title': title,
                            'text_length': len(page_text),
                            'status_code': getattr(response, 'status_code', getattr(response, 'status', 200)),
                            'content_preview': page_text[:500] + '...' if len(page_text) > 500 else page_text
                        }
                        
                        # Handle comment extraction for content-only mode
                        if include_comments:
                            page_comments = extract_all_comments(response)
                            
                            # Filter by comment type if specified
                            if comment_type:
                                type_filter = comment_type.lower()
                                if type_filter == "javascript":
                                    type_filter = ["javascript_single", "javascript_multi"]
                                elif type_filter == "js_single":
                                    type_filter = ["javascript_single"]
                                elif type_filter == "js_multi":
                                    type_filter = ["javascript_multi"]
                                elif type_filter == "html":
                                    type_filter = ["html"]
                                else:
                                    type_filter = [type_filter]
                                
                                page_comments = [c for c in page_comments if c['type'] in type_filter]
                            
                            # Filter by minimum length
                            if min_comment_length > 0:
                                page_comments = [c for c in page_comments if len(c['content']) >= min_comment_length]
                            
                            result_data['comments'] = page_comments
                            result_data['comments_count'] = len(page_comments)
                            
                            # Break down comments by type
                            comment_types = {}
                            for comment in page_comments:
                                comment_type = comment['type']
                                comment_types[comment_type] = comment_types.get(comment_type, 0) + 1
                            result_data['comment_types'] = comment_types
                        
                        results.append(result_data)
                    except Exception as e:
                        console.print(f"[red]Error extracting content: {str(e)}[/red]")
                        raise typer.Exit(1)
                
                output_results(results, format, output)
                return
            
            # Initialize crawling for link extraction mode
            base_domain = urlparse(url).netloc
            visited = set()
            to_visit = [(url, 0)]
            all_pages = []
            all_links = []
            
            # Statistics
            total_pages_crawled = 0
            total_links_found = 0
            files_found = []
            
            while to_visit and len(visited) < max_pages:
                current_url, current_depth = to_visit.pop(0)
                
                if current_url in visited or current_depth > depth:
                    continue
                
                visited.add(current_url)
                total_pages_crawled += 1
                
                progress.update(crawl_task, description=f"Crawling page {total_pages_crawled}/{max_pages}: {current_url[:50]}...")
                
                try:
                    # Fetch page
                    if javascript:
                        if custom_headers:
                            console.print("[yellow]Warning: Custom headers not supported in JS mode[/yellow]")
                        try:
                            response = fetcher_class.fetch(current_url, headless=True, network_idle=True)
                        except Exception as e:
                            console.print(f"[yellow]JS mode failed: {str(e)}. Falling back...[/yellow]")
                            response = Fetcher.get(current_url, headers=config.headers, stealthy_headers=True)
                    else:
                        response = fetcher_class.get(current_url, headers=config.headers, stealthy_headers=True)
                    
                    # Page metadata
                    page_data = {
                        'url': current_url,
                        'depth': current_depth,
                        'title': '',
                        'links_on_page': 0,
                        'internal_links': 0,
                        'external_links': 0,
                        'subdomain_links': 0,
                        'files_found': 0
                    }
                    
                    # Get title
                    try:
                        title_adaptors = response.css('title')
                        if title_adaptors:
                            page_data['title'] = title_adaptors.text if hasattr(title_adaptors, 'text') else str(title_adaptors)
                    except:
                        pass
                    
                    # Extract all links from this page (using improved Scrapy-style extraction)
                    page_links = extract_links_from_page(response, current_url, base_domain, include_subdomains)
                    
                    # Filter links
                    filtered_page_links = filter_links(
                        page_links, internal_only, external_only, subdomains_only, 
                        extensions, filter_types, unique_only, all_links if unique_only else None
                    )
                    
                    # Extract comments if requested
                    if include_comments:
                        page_comments = extract_all_comments(response)
                        
                        # Filter by comment type if specified
                        if comment_type:
                            type_filter = comment_type.lower()
                            if type_filter == "javascript":
                                type_filter = ["javascript_single", "javascript_multi"]
                            elif type_filter == "js_single":
                                type_filter = ["javascript_single"]
                            elif type_filter == "js_multi":
                                type_filter = ["javascript_multi"]
                            elif type_filter == "html":
                                type_filter = ["html"]
                            else:
                                type_filter = [type_filter]
                            
                            page_comments = [c for c in page_comments if c['type'] in type_filter]
                        
                        # Filter by minimum length
                        if min_comment_length > 0:
                            page_comments = [c for c in page_comments if len(c['content']) >= min_comment_length]
                        
                        page_data['comments'] = page_comments
                        page_data['comments_count'] = len(page_comments)
                        
                        # Break down comments by type
                        comment_types = {}
                        for comment in page_comments:
                            comment_type = comment['type']
                            comment_types[comment_type] = comment_types.get(comment_type, 0) + 1
                        page_data['comment_types'] = comment_types
                    
                    # Update statistics
                    page_data['links_on_page'] = len(page_links)
                    page_data['internal_links'] = len([l for l in page_links if l['is_internal']])
                    page_data['external_links'] = len([l for l in page_links if not l['is_internal'] and not l['is_subdomain']])
                    page_data['subdomain_links'] = len([l for l in page_links if l['is_subdomain']])
                    
                    if extensions:
                        extension_filters = [ext.strip().lower().lstrip('.') for ext in extensions.split(',')]
                        page_files = [l for l in page_links if any(l['url'].lower().endswith('.' + ext) for ext in extension_filters)]
                        page_data['files_found'] = len(page_files)
                        files_found.extend(page_files)
                    
                    # Add links to master list
                    all_links.extend(filtered_page_links)
                    total_links_found += len(filtered_page_links)
                    
                    # Add pages to crawl queue (if within depth)
                    if current_depth < depth:
                        for link in page_links:
                            if link['is_internal'] or (include_subdomains and link['is_subdomain']):
                                link_url = link['url']
                                parsed_link = urlparse(link_url)
                                
                                # Don't follow file links (with extensions)
                                if not Path(parsed_link.path).suffix and link_url not in visited:
                                    to_visit.append((link_url, current_depth + 1))
                    
                    all_pages.append(page_data)
                    
                except Exception as e:
                    console.print(f"[yellow]Warning: Failed to crawl {current_url}: {str(e)}[/yellow]")
                    continue
            
            # Validate links if requested
            if validate:
                progress.update(crawl_task, description="Validating links...")
                all_links = validate_links(all_links, config.headers)
            
            # Remove duplicates globally if requested
            if unique_only:
                seen_urls = set()
                unique_links = []
                for link in all_links:
                    if link['url'] not in seen_urls:
                        seen_urls.add(link['url'])
                        unique_links.append(link)
                all_links = unique_links
            
            # Show summary
            if summary:
                console.print(f"\n[green]🎉 Crawl Complete![/green]")
                console.print(f"[cyan]📄 Pages crawled: {total_pages_crawled}[/cyan]")
                console.print(f"[blue]🔗 Total links found: {len(all_links)}[/blue]")
                
                if extensions:
                    console.print(f"[yellow]📁 Files with specified extensions: {len(files_found)}[/yellow]")
                
                if validate:
                    accessible_links = len([l for l in all_links if l.get('is_accessible', True)])
                    console.print(f"[green]✅ Accessible links: {accessible_links}/{len(all_links)}[/green]")
            
            # Prepare output
            if links_only:
                output_data = all_links
            else:
                output_data = {
                    'crawl_info': {
                        'start_url': url,
                        'pages_crawled': total_pages_crawled,
                        'max_depth': depth,
                        'total_links': len(all_links),
                        'files_found': len(files_found) if extensions else 0
                    },
                    'pages': all_pages,
                    'links': all_links
                }
                
                if extensions:
                    output_data['files'] = files_found
            
            output_results(output_data if not links_only else all_links, format, output)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Crawling interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


def extract_html_comments(html_content: str) -> List[Dict[str, Any]]:
    """Extract HTML comments from content"""
    comments = []
    
    # Pattern for HTML comments: <!-- comment -->
    html_comment_pattern = r'<!--\s*(.*?)\s*-->'
    matches = re.finditer(html_comment_pattern, html_content, re.DOTALL)
    
    for match in matches:
        comment_text = match.group(1).strip()
        if comment_text:  # Only include non-empty comments
            comments.append({
                'type': 'html',
                'content': comment_text,
                'line_start': html_content[:match.start()].count('\n') + 1,
                'position': match.start()
            })
    
    return comments


def extract_js_comments(js_content: str) -> List[Dict[str, Any]]:
    """Extract JavaScript comments from content"""
    comments = []
    
    # Pattern for single-line comments: // comment
    single_line_pattern = r'//\s*(.*?)(?:\n|$)'
    matches = re.finditer(single_line_pattern, js_content, re.MULTILINE)
    
    for match in matches:
        comment_text = match.group(1).strip()
        if comment_text:
            comments.append({
                'type': 'javascript_single',
                'content': comment_text,
                'line_start': js_content[:match.start()].count('\n') + 1,
                'position': match.start()
            })
    
    # Pattern for multi-line comments: /* comment */
    multi_line_pattern = r'/\*\s*(.*?)\s*\*/'
    matches = re.finditer(multi_line_pattern, js_content, re.DOTALL)
    
    for match in matches:
        comment_text = match.group(1).strip()
        if comment_text:
            comments.append({
                'type': 'javascript_multi',
                'content': comment_text,
                'line_start': js_content[:match.start()].count('\n') + 1,
                'position': match.start()
            })
    
    return comments


def extract_all_comments(response) -> List[Dict[str, Any]]:
    """Extract all comments from HTML and JavaScript content in a page"""
    all_comments = []
    
    try:
        # Get the full HTML content
        html_content = ""
        if hasattr(response, 'text'):
            html_content = response.text
        elif hasattr(response, 'content'):
            html_content = str(response.content)
        else:
            html_content = str(response)
        
        # Extract HTML comments
        html_comments = extract_html_comments(html_content)
        all_comments.extend(html_comments)
        
        # Extract JavaScript from script tags
        try:
            script_elements = response.css('script')
            if script_elements:
                for script_elem in script_elements:
                    script_content = ""
                    if hasattr(script_elem, 'text'):
                        script_content = script_elem.text
                    elif hasattr(script_elem, 'get_text'):
                        script_content = script_elem.get_text()
                    else:
                        script_content = str(script_elem)
                    
                    if script_content:
                        js_comments = extract_js_comments(script_content)
                        # Mark these as inline JavaScript
                        for comment in js_comments:
                            comment['location'] = 'inline_script'
                        all_comments.extend(js_comments)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not extract JavaScript comments: {str(e)}[/yellow]")
        
        # Also check for comments in the raw HTML (in case some are outside script tags)
        raw_js_comments = extract_js_comments(html_content)
        for comment in raw_js_comments:
            comment['location'] = 'html_content'
        all_comments.extend(raw_js_comments)
        
    except Exception as e:
        console.print(f"[yellow]Warning: Could not extract comments: {str(e)}[/yellow]")
    
    return all_comments


def detect_link_source(link_element, response):
    """Detect the source context where a link was found"""
    try:
        # Try to get the href for context-specific detection
        href = ''
        if hasattr(link_element, 'attrs'):
            attrs = link_element.attrs
            href = attrs.get('href', '') if attrs else ''
        
        # Method 1: Use CSS selectors to detect context (more reliable with Scrapling)
        try:
            # Check if link is in navigation
            nav_links = response.css('nav a, [class*="nav"] a, [id*="nav"] a, [class*="menu"] a, [id*="menu"] a')
            if any(l for l in nav_links if hasattr(l, 'attrs') and l.attrs.get('href') == href):
                return 'navigation'
            
            # Check if link is in header
            header_links = response.css('header a, [class*="header"] a, [id*="header"] a, [class*="banner"] a')
            if any(l for l in header_links if hasattr(l, 'attrs') and l.attrs.get('href') == href):
                return 'header'
            
            # Check if link is in footer  
            footer_links = response.css('footer a, [class*="footer"] a, [id*="footer"] a')
            if any(l for l in footer_links if hasattr(l, 'attrs') and l.attrs.get('href') == href):
                return 'footer'
            
            # Check if link is in sidebar
            sidebar_links = response.css('aside a, [class*="sidebar"] a, [id*="sidebar"] a, [class*="side"] a')
            if any(l for l in sidebar_links if hasattr(l, 'attrs') and l.attrs.get('href') == href):
                return 'sidebar'
            
            # Check if link is in main content
            main_links = response.css('main a, [class*="main"] a, [class*="content"] a, article a')
            if any(l for l in main_links if hasattr(l, 'attrs') and l.attrs.get('href') == href):
                return 'main_content'
            
            # Check if link is in breadcrumb
            breadcrumb_links = response.css('[class*="breadcrumb"] a, [id*="breadcrumb"] a, [class*="crumb"] a')
            if any(l for l in breadcrumb_links if hasattr(l, 'attrs') and l.attrs.get('href') == href):
                return 'breadcrumb'
                
        except:
            pass
        
        # Method 2: Analyze parent classes and IDs (fallback)
        try:
            parent_classes = []
            parent_ids = []
            current = link_element
            
            # Traverse up the DOM to collect parent information
            for _ in range(5):  # Look up to 5 levels up
                try:
                    if hasattr(current, 'parent'):
                        current = current.parent
                        if hasattr(current, 'attrs'):
                            attrs = current.attrs
                            if 'class' in attrs:
                                parent_classes.extend(str(attrs['class']).lower().split())
                            if 'id' in attrs:
                                parent_ids.append(str(attrs['id']).lower())
                    else:
                        break
                except:
                    break
            
            all_attributes = ' '.join(parent_classes + parent_ids)
            
            # Detect contexts based on class/id patterns
            if any(nav in all_attributes for nav in ['nav', 'navigation', 'menu']):
                return 'navigation'
            elif any(header in all_attributes for header in ['header', 'banner', 'top']):
                return 'header'
            elif any(footer in all_attributes for footer in ['footer', 'bottom']):
                return 'footer'
            elif any(sidebar in all_attributes for sidebar in ['sidebar', 'aside', 'side']):
                return 'sidebar'
            elif any(content in all_attributes for content in ['main', 'article', 'content', 'body']):
                return 'main_content'
            elif any(breadcrumb in all_attributes for breadcrumb in ['breadcrumb', 'breadcrumbs', 'crumb']):
                return 'breadcrumb'
                
        except:
            pass
        
        # Method 3: Analyze link text and href for additional context
        try:
            link_text = ''
            if hasattr(link_element, 'text'):
                link_text = str(link_element.text).lower() if link_element.text else ''
            
            # Analyze link text for context clues
            if any(word in link_text for word in ['home', 'index', 'main']):
                return 'navigation'
            elif any(word in link_text for word in ['contact', 'about', 'privacy', 'terms']):
                return 'footer'
            elif any(word in link_text for word in ['login', 'register', 'account', 'profile']):
                return 'header'
            elif any(word in link_text for word in ['read more', 'continue', 'next', 'previous']):
                return 'main_content'
                
            # Analyze href for context clues
            if any(path in href.lower() for path in ['/contact', '/about', '/privacy', '/terms']):
                return 'footer'
            elif any(path in href.lower() for path in ['/login', '/register', '/account', '/profile']):
                return 'header'
            elif any(path in href.lower() for path in ['/home', '/index', '/']):
                return 'navigation'
                
        except:
            pass
        
        # Default fallback
        return 'content'
        
    except:
        return 'unknown'


def extract_links_from_page(response, current_url, base_domain, include_subdomains):
    """Extract all links from a single page using Scrapy-inspired methods with source detection"""
    all_links = []
    
    try:
        # Get all link elements with their context
        link_elements = response.css('a')
        href_to_data = {}
        
        # First pass: collect all links with their source context
        for elem in link_elements:
            try:
                if hasattr(elem, 'attrs'):
                    attrs = elem.attrs
                    href = attrs.get('href', '') if attrs else ''
                    if href:
                        href = href.strip()
                        
                        # Get text content
                        try:
                            text_content = elem.text.strip() if hasattr(elem, 'text') and elem.text else ''
                        except:
                            text_content = ''
                        
                        # Detect source context
                        source = detect_link_source(elem, response)
                        
                        # Store link data
                        href_to_data[href] = {
                            'text': text_content,
                            'source': source,
                            'element': elem
                        }
            except:
                continue
        
        # Fallback method if main method fails
        if not href_to_data:
            try:
                href_elements = response.css('a::attr(href)')
                if href_elements:
                    for href_elem in href_elements:
                        href_text = href_elem.text if hasattr(href_elem, 'text') else str(href_elem)
                        if href_text:
                            href = href_text.strip()
                            href_to_data[href] = {
                                'text': '',
                                'source': 'unknown',
                                'element': None
                            }
            except:
                pass
        
        # Process all collected hrefs with their context
        for href, link_info in href_to_data.items():
            if href:
                # Skip problematic links (Scrapy-style filtering)
                if href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
                    continue
                
                absolute_url = urljoin(current_url, href)
                parsed_url = urlparse(absolute_url)
                
                if parsed_url.scheme in ['http', 'https']:
                    # Domain classification
                    is_internal = parsed_url.netloc == base_domain or parsed_url.netloc == ''
                    is_subdomain = is_subdomain_of(parsed_url.netloc, base_domain)
                    
                    if is_same_or_subdomain(parsed_url.netloc, base_domain):
                        is_internal = True
                    
                    if include_subdomains and is_subdomain:
                        is_internal = True
                    
                    link_data = {
                        'url': absolute_url,
                        'text': link_info['text'],
                        'domain': parsed_url.netloc,
                        'path': parsed_url.path,
                        'query': parsed_url.query,
                        'fragment': parsed_url.fragment,
                        'is_internal': is_internal,
                        'is_subdomain': is_subdomain,
                        'link_type': get_link_type(absolute_url),
                        'source': link_info['source'],
                        'original_href': href,
                        'found_on_page': current_url
                    }
                    
                    all_links.append(link_data)
    
    except Exception:
        pass
    
    return all_links


def filter_links(links, internal_only, external_only, subdomains_only, extensions, filter_types, unique_only, existing_links=None):
    """Filter links based on various criteria"""
    filtered = links
    
    # Domain filtering
    if internal_only:
        filtered = [l for l in filtered if l['is_internal']]
    elif external_only:
        filtered = [l for l in filtered if not l['is_internal'] and not l['is_subdomain']]
    elif subdomains_only:
        filtered = [l for l in filtered if l['is_subdomain']]
    
    # Extension filtering
    if extensions:
        extension_filters = [ext.strip().lower().lstrip('.') for ext in extensions.split(',')]
        filtered = filter_by_extensions(filtered, extension_filters)
    
    # Type filtering
    if filter_types:
        type_filters = [t.strip().lower() for t in filter_types.split(',')]
        filtered = filter_by_types(filtered, type_filters)
    
    return filtered


@app.command()
def extract(
    url: str = typer.Argument(..., help="URL to extract data from"),
    rules: Path = typer.Argument(..., help="JSON file with extraction rules"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    format: OutputFormat = typer.Option(OutputFormat.json, "--format", "-f", help="Output format"),
    javascript: bool = typer.Option(False, "--js", help="Enable JavaScript rendering"),
    headers: Optional[str] = typer.Option(None, "--headers", "-h", help="Custom headers as JSON string"),
    wait: Optional[float] = typer.Option(None, "--wait", "-w", help="Wait time in seconds for JS rendering")
):
    """
    Extract structured data using custom rules
    
    Example rules.json:
    {
        "title": {"selector": "h1", "attribute": "text"},
        "price": {"selector": ".price", "attribute": "text"},
        "image": {"selector": "img.product", "attribute": "src"},
        "description": {"selector": ".description", "attribute": "text", "all": true}
    }
    """
    try:
        with open(rules, 'r') as f:
            extraction_rules = json.load(f)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Extracting data...", total=None)
            
            # Use StealthyFetcher for JavaScript rendering or regular Fetcher otherwise
            fetcher_class = get_fetcher_class(stealth=javascript)
            if javascript:
                fetcher_class.auto_match = True
            
            custom_headers = None
            if headers:
                try:
                    custom_headers = json.loads(headers)
                except json.JSONDecodeError:
                    console.print("[red]Error: Invalid JSON format for headers[/red]")
                    raise typer.Exit(1)
            
            config = ScrapeConfig(headers=custom_headers)
            
            if javascript:
                # StealthyFetcher doesn't accept headers parameter directly
                if custom_headers:
                    console.print("[yellow]Warning: Custom headers are not supported in JavaScript mode (--js). Using default stealth headers.[/yellow]")
                try:
                    response = fetcher_class.fetch(
                        url,
                        headless=True,
                        network_idle=wait is not None
                    )
                except Exception as e:
                    console.print(f"[yellow]Warning: JavaScript mode failed ({str(e)}). Falling back to regular fetching.[/yellow]")
                    # Fallback to regular fetcher
                    response = Fetcher.get(url, headers=config.headers, stealthy_headers=True)
            else:
                response = fetcher_class.get(url, headers=config.headers, stealthy_headers=True)
            
            results = {}
            
            for field, rule in extraction_rules.items():
                selector = rule.get('selector')
                attribute = rule.get('attribute', 'text')
                get_all = rule.get('all', False)
                
                if selector:
                    try:
                        elements = response.css(selector)
                        
                        if get_all:
                            if attribute == 'text':
                                results[field] = []
                                for elem in elements:
                                    try:
                                        text = elem.text.strip() if hasattr(elem, 'text') and elem.text else ''
                                        if not text and hasattr(elem, 'get_text'):
                                            text = elem.get_text().strip()
                                        results[field].append(text)
                                    except:
                                        results[field].append('')
                            else:
                                results[field] = []
                                for elem in elements:
                                    try:
                                        attrs = elem.attrs if hasattr(elem, 'attrs') else {}
                                        results[field].append(attrs.get(attribute, ''))
                                    except:
                                        results[field].append('')
                        else:
                            if elements:
                                elem = elements[0]
                                if attribute == 'text':
                                    try:
                                        text = elem.text.strip() if hasattr(elem, 'text') and elem.text else ''
                                        if not text and hasattr(elem, 'get_text'):
                                            text = elem.get_text().strip()
                                        results[field] = text
                                    except:
                                        results[field] = ''
                                else:
                                    try:
                                        attrs = elem.attrs if hasattr(elem, 'attrs') else {}
                                        results[field] = attrs.get(attribute, '')
                                    except:
                                        results[field] = ''
                            else:
                                results[field] = None
                    except Exception as e:
                        results[field] = None
        
        output_results([results], format, output)
        
    except FileNotFoundError:
        console.print(f"[red]Error: Rules file not found: {rules}[/red]")
        raise typer.Exit(1)
    except json.JSONDecodeError:
        console.print("[red]Error: Invalid JSON in rules file[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


def output_results(results: List[Dict[str, Any]], format: OutputFormat, output_path: Optional[Path]):
    """Output results in the specified format"""
    if format == OutputFormat.table:
        if not results:
            console.print("[yellow]No results found[/yellow]")
            return
        
        table = Table(title="Scraping Results")
        
        if results:
            for key in results[0].keys():
                table.add_column(key, style="cyan", no_wrap=False)
            
            for result in results[:10]:  # Show max 10 rows in table
                row = []
                for key in result.keys():
                    value = str(result[key])
                    if len(value) > 50:
                        value = value[:47] + "..."
                    row.append(value)
                table.add_row(*row)
            
            if len(results) > 10:
                table.add_row(*["..." for _ in results[0].keys()])
        
        console.print(table)
        
        if output_path:
            df = pd.DataFrame(results)
            df.to_csv(output_path, index=False)
            console.print(f"\n[green]Results saved to: {output_path}[/green]")
    
    elif format == OutputFormat.json:
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            console.print(f"[green]Results saved to: {output_path}[/green]")
        else:
            rprint(json.dumps(results, indent=2))
    
    elif format == OutputFormat.csv:
        if not results:
            console.print("[yellow]No results found[/yellow]")
            return
            
        df = pd.DataFrame(results)
        
        if output_path:
            df.to_csv(output_path, index=False)
            console.print(f"[green]Results saved to: {output_path}[/green]")
        else:
            console.print(df.to_csv(index=False))
    
    elif format == OutputFormat.html:
        if not results:
            console.print("[yellow]No results found[/yellow]")
            return
            
        df = pd.DataFrame(results)
        html_content = df.to_html(index=False, escape=False)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(html_content)
            console.print(f"[green]Results saved to: {output_path}[/green]")
        else:
            console.print(html_content)



@app.command()
def version():
    """Show version information"""
    console.print("[bold cyan]scrape_this v1.0.0[/bold cyan]")
    console.print("Powered by Scrapling and Typer")


if __name__ == "__main__":
    app()