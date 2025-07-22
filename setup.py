#!/usr/bin/env python3
"""Setup script for scrape_this"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="scrape_this",
    version="1.0.0",
    description="A powerful web scraping CLI tool powered by Scrapling",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Ghio Rodolphe",
    author_email="contact@rodolpheg.xyz",
    url="https://github.com/GRodolphe/scrape_this",
    py_modules=["scrape_this"],
    python_requires=">=3.8",
    install_requires=[
        "typer[all]>=0.9.0",
        "scrapling>=0.2.0",
        "rich>=13.0.0",
        "pandas>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "scrape_this=scrape_this:app",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Networking",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="web scraping cli scrapling typer automation data extraction",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/scrape_this/issues",
        "Source": "https://github.com/yourusername/scrape_this",
    },
)