from collections import Counter
import os
import json
import argparse

from scripts.page_crawler.index_crawler import IndexCrawler
from scripts.utils import thread_process_crawl_index

import warnings
warnings.simplefilter("once")


def main():
    site_list = []
    site_list.append(IndexCrawler(
        args=args,
        site_name="CNN",
        root_url_list=[
            "https://www.cnn.com/sitemap/article.xml",
            "https://www.cnn.com/sitemap/video.xml",
            "https://www.cnn.com/sitemap/gallery.xml"
        ],
    ))
    site_list.append(IndexCrawler(
        args=args,
        site_name="Variety",
        root_url_list=["https://variety.com/sitemap_index.xml"],
    ))
    site_list.append(IndexCrawler(
        args=args,
        site_name="TechCrunch",
        homepage_url="https://techcrunch.com"
    ))
    site_list.append(IndexCrawler(
        args=args,
        site_name="Mongabay",
        homepage_url="https://news.mongabay.com"
    ))
    site_list.append(IndexCrawler(
        args=args,
        site_name="Space.com",
        homepage_url="https://www.space.com"
    ))

    crawl_parallel_method = "thread"
    func_args = ()
    crawl_max_workers = args.max_thread
    page_list = \
        thread_process_crawl_index(site_list, func_args, executor_type=crawl_parallel_method, max_workers=crawl_max_workers)
    print()

    for site_name, count in sorted(Counter([(page["site_name"]) for page in page_list]).items()):
        print(f"{site_name}: {count}")

    # Save
    os.makedirs(args.data_path, exist_ok=True)
    with open(f"{args.data_path}/content_page_list.jsonl", "w")as f:
        for page in page_list:
            f.write(json.dumps(page, ensure_ascii=False)+"\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("--data_path", type=str, help="Path to dataset to be saved")
    parser.add_argument("--page_size", type=int, default=1000000000, help="Number of pages to download per site")
    parser.add_argument("--disable_page_reget", action="store_true", help="If true, skip already downloaded page")
    parser.add_argument("--max_thread", type=int, default=16, help="Max thread size")

    args = parser.parse_args()

    main()
