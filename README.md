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

# Test specific year and month
python AZScraper.py -y 2007 -m 3

# Test with specific governorate
python AZScraper.py -dob 70315 -g 01

# Multiple governorates
python AZScraper.py -y 2007 -m 3 -g 01 02 21
```

### Arguments

- `-dob` - Exact date (YMMDD format)
- `-y` - Birth year
- `-m` - Birth month (1-12, use with -y)
- `-g` - Governorate ID(s) (see governorate_ids.md)
- `-o` - Output file (default: valid_responses.json)
- `-t` - Number of threads (default: 50)
- `--proxy` - HTTP proxy URL

## How it works

Script generates IDs in format: `30{DATE}{GOV_ID}{SEQUENCE}`
- Sends requests to Azhar WebService
- Saves valid responses to JSON file
- Uses multithreading for speed

## Output

Results saved as JSON with ID and response data.

## Disclaimer

For educational purposes only. Use responsibly.