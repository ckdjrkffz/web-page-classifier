import os
import json
import datetime
import time
import argparse
import random
import pandas as pd

from scripts.page_crawler.general_crawler import GeneralCrawler
from scripts.utils import thread_process_crawl

import warnings
warnings.simplefilter("once")


def crawl():

    start_time = time.time()

    print("Start preparing")

    random.seed(0)

    crawl_link_setting = "strict"
    config_file_name = "target_site.csv"
    target_file_type = ["html"]
    crawl_max_depth = 8
    crawl_max_workers = args.max_process
    crawl_parallel_method = "process"
    data_raw_folder = args.data_raw_folder
    crawl_log_interval = 100

    # Initialize
    print("Start initializing crawler")

    target_site_list = pd.read_csv(f"config/{config_file_name}").to_dict(orient="records")
    target_site_list = target_site_list[0:args.site_size]

    site_list = []
    for site_dict in target_site_list:
        crawler = GeneralCrawler(
            site_dict["site_name"], site_dict["URL"],
            args.disable_page_reget, crawl_max_depth,
            crawl_link_setting, data_raw_folder, crawl_log_interval,
        )
        site_list.append(crawler)

    page_list = []
    page_size = args.page_size
    print(f"Download page size: {page_size}")
    print(f"Download site size: {len(target_site_list)}")

    # Download page
    print("Get page list")
    func_args = (page_size, target_file_type)
    page_list = \
        thread_process_crawl(site_list, func_args, executor_type=crawl_parallel_method, max_workers=crawl_max_workers)
    print()

    print(f"Collected page size: {len(page_list)}")
    elasped_time = datetime.timedelta(seconds=time.time() - start_time)
    print(f"End download {elasped_time}")
    print()

    os.makedirs(args.data_path, exist_ok=True)
    with open(f"{args.data_path}/page_list.jsonl", "w")as f:
        for page in page_list:
            f.write(json.dumps(page, ensure_ascii=False) + "\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_path", type=str, default=None)
    parser.add_argument("--data_raw_folder", type=str, default="./data/page_raw")
    parser.add_argument("--page_size", type=int, default=1000000000)
    parser.add_argument("--site_size", type=int, default=100)
    parser.add_argument("--disable_page_reget", action="store_true")
    parser.add_argument("--max_process", type=int, default=16)

    args = parser.parse_args()

    crawl()
