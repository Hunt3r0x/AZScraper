# AZScraper

A Python script to brute force Azhar student IDs and retrieve results.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Examples

```bash
# Test specific date
python AZScraper.py -dob 70315

# Test specific year (all months and days)
python AZScraper.py -y 2007

# Test specific year and month
python AZScraper.py -y 2007 -m 3

# Test with specific governorate
python AZScraper.py -dob 70315 -g 01

# Multiple governorates
python AZScraper.py -y 2007 -m 3 -g 01 02 21

# With custom output file and threads
python AZScraper.py -y 2007 -m 3 -g 01 -o cairo_results.json -t 20

# Using proxy
python AZScraper.py -dob 70315 --proxy http://127.0.0.1:8080
```

### Arguments

**Date Options (choose one):**
- `-dob` - Exact date (YMMDD format like 70315)
- `-y, --year` - Birth year (tests all months/days in that year)
- `-y, --year` + `-m, --month` - Specific year and month

**Targeting Options:**
- `-g, --gov` - Governorate ID(s) (space-separated, see governorate_ids.md)

**Network Options:**
- `--proxy` - HTTP proxy URL (e.g. http://127.0.0.1:8080)
- `--proxy-https` - HTTPS proxy URL (optional, uses --proxy if not set)

**Output Options:**
- `-o, --file` - Output file (default: valid_responses.json)
- `-t, --threads` - Number of threads (default: 50)

### Date Input Rules

- Use `-dob` for exact dates: `-dob 70315` (March 15, 2007)
- Use `-y` alone to test entire year: `-y 2007` (all 365/366 dates)
- Use `-y` + `-m` for specific month: `-y 2007 -m 3` (all March 2007 dates)
- Cannot combine `-dob` with `-y` or `-m`

## How it works

Script generates IDs in format: `30{DATE}{GOV_ID}{SEQUENCE}`
- Sends requests to Azhar WebService
- Saves valid responses to JSON file
- Uses multithreading for speed
- Shows progress bar with real-time stats

## Output

Results saved as JSON with ID and response data.

## Disclaimer

For educational purposes only. Use responsibly.