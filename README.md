# Poskok.info Web Scraper

A comprehensive web scraping toolkit for archiving articles from Poskok.info, a Bosnian news portal. This scraper efficiently collects, processes, and filters content while respecting the website's resources.

## 🌟 Features

- **Complete Archive Collection**: Scrapes articles from 2012 to present
- **Intelligent Filtering**: Automatically detects and separates foreign language content
- **Parallel Processing**: Uses multiprocessing for faster scraping
- **Robust Error Handling**: Includes retry mechanisms and checkpointing
- **Language Detection**: Filters out English and Italian articles
- **Deduplication**: Automatically removes duplicate articles
- **Progress Tracking**: Detailed logging and progress monitoring
- **Batch Processing**: Handles large datasets efficiently
- **Data Export**: Creates organized text files and ZIP archives

## 📋 Prerequisites

- Python 3.7+
- BeautifulSoup4
- Requests
- Basic understanding of web scraping ethics

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/poskok-scraper.git
cd poskok-scraper
```

### 2. Set up a virtual environment

```bash
python3 -m venv poskok_env
source poskok_env/bin/activate  # On Windows: poskok_env\Scripts\activate
```

### 3. Install dependencies

```bash
pip install beautifulsoup4 requests
```

### 4. Run a quick test

```bash
python basic_quick_test.py
```

## 💻 Full Usage Guide

### Scraping Entire Website (2012-2025)

1. **Create configuration file**:

```bash
cat > full_config.json << 'EOF'
{
  "start_year": 2012,
  "end_year": 2025,
  "max_pages_per_category": 300,
  "batch_size": 100,
  "checkpoint_interval": 20,
  "max_retries": 5,
  "retry_delay": 3,
  "timeout": 30,
  "scrape_archive": true,
  "force_refresh_links": true,
  "output_folder": "PoskokFullArchive",
  "max_workers": 4,
  "batch_link_size": 500
}
EOF
```

2. **Run the complete scraping process**:

```bash
# Collect links
python3 link_collector.py --output-dir PoskokData/links --config full_config.json

# Process articles in batches
python3 batch_processor.py --input-dir PoskokData/link_batches --output-dir PoskokData/articles --config full_config.json

# Filter content
python3 filter.py --input PoskokData/articles --output-local PoskokData/filtered/local --output-foreign PoskokData/filtered/foreign --mode all-batches

# Combine and create final output
python3 combine.py --input-dir PoskokData/filtered/local --output-file PoskokData/final/AllPoskokArticles.txt --create-zip --generate-report
```

### Running Individual Components

You can also run individual components separately:

```bash
# Run just the link collector
python3 link_collector.py --output-dir links_output --config config.json

# Process a specific batch
python3 batch_processor.py --batch-range 1-5 --config config.json

# Run using the main orchestrator
python3 main.py --full-pipeline --config config.json
```

## 📁 Project Structure

```
poskok-scraper/
├── article_scraper.py       # Scrapes individual articles
├── batch_processor.py       # Manages parallel processing
├── link_collector.py        # Collects article URLs
├── filter.py               # Filters foreign language content
├── combine.py              # Combines filtered articles
├── config.py               # Configuration constants
├── main.py                 # Main orchestrator script
├── quick_test.py           # Quick testing script
├── basic_quick_test.py     # No-dependency test script
├── scraping_config.json    # Default configuration
├── full_config.json        # Full scraping configuration
└── README.md               # This file
```

## ⚙️ Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `start_year` | Starting year for archive scraping | 2012 |
| `end_year` | Ending year for archive scraping | Current year |
| `max_pages_per_category` | Maximum pages to scrape per category | 300 |
| `batch_size` | Number of articles per batch file | 100 |
| `max_workers` | Number of parallel workers | 4 |
| `retry_delay` | Delay between retries (seconds) | 3 |
| `timeout` | Request timeout (seconds) | 30 |

## 📊 Output Format

Articles are saved in a structured text format:

```
<***>
NOVINA: poskok.info
DATUM: 30. travnja 2025.
RUBRIKA: Novice
NADNASLOV: N/A
NASLOV: Article Title
PODNASLOV: Subtitle
STRANA: https://poskok.info/article-url/
AUTOR(I): Author Name

Article content goes here...
```

## 🛡️ Error Handling

The scraper includes robust error handling:

- Automatic retries with exponential backoff
- Checkpoint saving for resume capability
- Detailed logging of all operations
- Graceful handling of 404 and connection errors

## 📈 Performance

Based on testing with 33,363 URLs:
- Link collection: ~8 hours
- Article scraping: ~6 hours (with 4 workers)
- Filtering: ~1 minute
- Combining: ~30 seconds

## 🚫 Limitations

- Designed specifically for Poskok.info
- May require adjustments for website structure changes
- Respects robots.txt and implements polite scraping
- Foreign language detection is rule-based, not ML-based

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## ⚠️ Disclaimer

This scraper is intended for educational and archival purposes. Users must:
- Respect the website's robots.txt
- Not overwhelm the server with requests
- Comply with all applicable laws and terms of service
- Use the data responsibly and ethically

---

Made with ❤️ for web archiving and data preservation