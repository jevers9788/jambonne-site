# Safari Reading List Mind Map Generator

> **Note:** These scripts are optional/legacy. For most users, we recommend using the `mindmap-service` microservice for mind map generation and integration with the Rust website. See the top-level `README.md` for project structure and integration details.

This tool extracts your Safari reading list, scrapes the content from each URL, and generates a mind map visualization to help you understand the themes and content of your saved articles.

## Features

- **Safari Reading List Extraction**: Reads your Safari bookmarks.plist file to extract your reading list
- **Web Content Scraping**: Intelligently extracts main content from web pages
- **Mind Map Generation**: Creates visual mind maps showing relationships between articles
- **Keyword Analysis**: Extracts common keywords from your reading content
- **Multiple Output Formats**: Generates PNG images and text summaries

## Quick Start

### Option 1: Automated Setup (Recommended)

```bash
cd scripts
./setup.sh
```

This will automatically install `uv` if needed and set up all dependencies from `requirements.txt`.

### Option 2: Manual Setup

#### Prerequisites

1. Install `uv` (if not already installed):
```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

#### Setup

1. Navigate to the scripts directory:
```bash
cd scripts
```

2. Install dependencies from requirements.txt:
```bash
uv pip install -r requirements.txt
```

This will:
- Create a virtual environment
- Install all dependencies from `requirements.txt`

## Usage

### Using Make Commands (Recommended)

```bash
# Run the scraper
make run-scrape

# Generate mind maps
make run-visualize

# Run both in sequence
make all

# Clean generated files
make clean

# See all available commands
make help
```

### Manual Usage

#### Step 1: Extract and Scrape Reading List

Run the main script to extract your Safari reading list and optionally scrape content:

```bash
uv run python reading_list.py
```

The script will:
1. Read your Safari reading list from `~/Library/Safari/Bookmarks.plist`
2. Ask if you want to scrape content from the URLs
3. If you choose 'y', it will scrape each URL with respectful delays
4. Save the raw data to `reading_list_content.json`
5. Generate mind map data to `mind_map_data.json`

#### Step 2: Generate Mind Map Visualizations

After scraping, create visual mind maps:

```bash
uv run python mind_map_visualizer.py
```

This will generate:
- `mind_map.png`: Basic mind map visualization
- `enhanced_mind_map.png`: Enhanced mind map with keyword analysis
- `mind_map_summary.txt`: Text summary of all articles

## Development

### Adding New Dependencies

To add a new dependency:

```bash
uv pip install package-name
# Then add it to requirements.txt
```

For development dependencies:
```bash
uv pip install --dev package-name
# Then add it to requirements.txt (comment as dev)
```

### Updating Dependencies

Just update requirements.txt as needed.

### Running with Development Tools

```bash
# Format code
make format
# or
uv run black .

# Lint code
make lint
# or
uv run flake8 .

# Run tests (if you add them)
make test
# or
uv run pytest
```

## Output Files

### reading_list_content.json
Raw scraped data including:
- Article titles and URLs
- Scraped content (truncated to 5000 characters)
- Content length statistics
- Date added information

### mind_map_data.json
Structured data for mind map generation:
- Central topic (Safari Reading List)
- Branches for each article
- Content previews and metadata

### mind_map.png
Basic mind map showing:
- Central topic in blue
- Article branches arranged in a circle
- Color-coded boxes based on content length
- Connection lines between topics

### enhanced_mind_map.png
Advanced mind map with:
- Keyword cloud in background
- Article-specific keywords
- Larger, more detailed visualization
- Better content categorization

### mind_map_summary.txt
Text summary including:
- Total article count and content length
- Individual article details
- Content previews

## Content Scraping Features

The scraper intelligently:
- Removes navigation, headers, footers, and ads
- Focuses on main content areas (article, main, content selectors)
- Handles different website structures
- Includes proper user-agent headers
- Respects robots.txt with delays between requests
- Cleans and normalizes extracted text

## Customization

### Adjusting Scraping Behavior
In `reading_list.py`, you can modify:
- `delay` parameter in `scrape_reading_list_content()` for request timing
- `timeout` parameter in `extract_text_from_url()` for request timeouts
- Content length limits for mind map processing

### Customizing Visualizations
In `mind_map_visualizer.py`, you can adjust:
- Figure sizes and DPI for different output qualities
- Color schemes for different content lengths
- Keyword extraction parameters
- Layout and positioning

## Troubleshooting

### Common Issues

1. **"Safari Bookmarks.plist not found"**
   - Make sure you're using Safari and have a reading list
   - Check if the file exists at `~/Library/Safari/Bookmarks.plist`

2. **Scraping failures**
   - Some websites block automated requests
   - Check the error messages for specific issues
   - Consider adjusting delays or user-agent headers

3. **Missing dependencies**
   - Run `uv pip install -r requirements.txt` to ensure all dependencies are installed
   - Check that you're using `uv run` to execute scripts

4. **Permission errors**
   - Ensure you have read access to Safari bookmarks
   - Check write permissions in the current directory

### Performance Tips

- For large reading lists, consider running scraping in batches
- Adjust delays based on website responsiveness
- Use the text summary for quick overviews
- The enhanced mind map works best with 10-50 articles

## Privacy and Ethics

- This tool only reads your local Safari bookmarks
- Web scraping respects robots.txt and includes delays
- No data is sent to external services
- All processing happens locally on your machine

## Future Enhancements

Potential improvements:
- Integration with NLP libraries for better keyword extraction
- Export to other mind map formats (FreeMind, XMind)
- Topic clustering and categorization
- Reading time estimates
- Integration with other browsers (Chrome, Firefox) 