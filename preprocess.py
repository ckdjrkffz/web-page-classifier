import re
from collections import Counter
import os
import json
import argparse
import random
import itertools
import pandas as pd
from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup
import traceback
import html
from tqdm import tqdm

from scripts.content_extractor import ExtractContent
from scripts.utils import thread_process

import warnings
warnings.simplefilter("once")


def normalize_url(url):
    parsed_url = urlparse(url)

    path = parsed_url.path
    if path.endswith("index.htm") or path.endswith("index.html"):
        path = path[:path.rfind("/")]

    if path.endswith("/") == False:
        path += "/"

    normalized_url = urlunparse(parsed_url._replace(path=path))
    return normalized_url


class PagePreprocessing():
    def __init__(self, content_page_url_set, target_site_to_split):

        self.content_page_url_set = content_page_url_set
        self.target_site_to_split = target_site_to_split

        self.extractor = ExtractContent()

    # recieve html, return the detected publish date of the html
    def publish_datetime_estimator(self, text, url):

        # Extraction from "application/ld+json"
        def extract_from_ld_json(soup):
            try:
                element_list = soup.find_all("script", attrs={"type": "application/ld+json"})
                if len(element_list) == 0:
                    return None

                item = "\n".join([item.text for item in element_list])
                publish_date = re.search(r'"datePublished":\s*?"(\d{4}-\d{2}-\d{2})', item)
                if publish_date is None:
                    return None

                publish_date = publish_date.group(1)

                return publish_date

            except Exception:
                print("Raised exception", url)
                print(traceback.format_exc())
                return None

        # Extraction from 'meta property="article:published_time"'
        def extract_from_meta(soup):
            try:
                element_list = soup.find_all("meta", attrs={"property": "article:published_time"})
                if len(element_list) == 0:
                    return None

                item = "\n".join([item.get("content") for item in element_list])
                publish_date = re.search(r'(\d{4}-\d{2}-\d{2})', item)
                if publish_date is None:
                    return None

                publish_date = publish_date.group(1)

                return publish_date

            except Exception:
                print("Raised exception", url)
                print(traceback.format_exc())
                return None

        soup = BeautifulSoup(text, "html.parser")

        publish_date = extract_from_ld_json(soup)
        if publish_date is not None:
            return publish_date

        publish_date = extract_from_meta(soup)
        if publish_date is not None:
            return publish_date

        date_str = "None"

        return date_str

    def preprocess_page(self, page):

        with open(page["save_path"], "rb")as f:
            byte_text = f.read()
        html_text = byte_text.decode(page["encoding"])
        html_text = html.unescape(html_text)

        main_text_list, title = self.extractor.analyse(html_text)

        main_text = " ".join(main_text_list).replace(title, "")
        main_text = main_text.replace("\n", "").replace('"', "'")
        publish_datetime = self.publish_datetime_estimator(html_text, page["url"])

        page["main_text"] = main_text
        page["title"] = title
        page["publish_datetime"] = publish_datetime
        page["invalid_page"] = (len(html_text) <= 100)

        page["split"] = self.target_site_to_split[page["site_name"]]
        if page["split"] in ["dev", "test"]:
            if normalize_url(page["url"]) in self.content_page_url_set:
                page["gold"] = "contents"
            else:
                page["gold"] = "index"
        else:
            page["gold"] = "unknown"

        page["url_hyperlink"] = f'=HYPERLINK("{page["url"]}")'

        return page


def main():

    print("Start preparing")

    random.seed(0)

    config_file_name = "target_site.csv"
    target_site_list = pd.read_csv(f"config/{config_file_name}").to_dict(orient="records")
    target_site_list = target_site_list[0:args.site_size]
    target_site_name_list = [t["site_name"] for t in target_site_list]
    target_site_to_split = {site["site_name"]: site["split"] for site in target_site_list}

    page_list = []
    with open(f"{args.data_path}/page_list.jsonl")as f:
        for page in f:
            page_list.append(json.loads(page))

    content_page_list = []
    with open(f"{args.data_path}/content_page_list.jsonl")as f:
        for page in f:
            content_page_list.append(json.loads(page))

    content_page_url_set = set([normalize_url(page["url"]) for page in content_page_list])

    print(f"All page size: {len(page_list)}")
    print(f"All content size: {len(page_list)}")

    page_processing = PagePreprocessing(content_page_url_set, target_site_to_split)

    # Filter page
    print("start filter")
    for num, page in enumerate(page_list):
        page["page_id"] = num
    func = page_processing.preprocess_page
    func_args = ()
    page_list = list(itertools.chain.from_iterable(
            [[page for page in page_list if page["site_name"] == site_name][0:args.page_size]
                for site_name in target_site_name_list]
    ))

    page_list = thread_process(page_list, func, func_args, executor_type="process", max_workers=args.max_process)

    print(f"processed all page size: {len(page_list)}")

    for index, count in Counter([(page["site_name"], page["gold"]) for page in page_list]).items():
        print(f"{index}: {count}")

    page_list_dev = [page for page in page_list if page["split"] in ["dev"]]
    page_list_test = [page for page in page_list if page["split"] in ["test", "test-noisy"]]
    os.makedirs(args.data_path, exist_ok=True)

    # Save
    with open(f"{args.data_path}/processed_page_list_dev.jsonl", "w")as f:
        for page in page_list_dev:
            f.write(json.dumps(page, ensure_ascii=False)+"\n")
    with open(f"{args.data_path}/processed_page_list_test.jsonl", "w")as f:
        for page in page_list_test:
            f.write(json.dumps(page, ensure_ascii=False)+"\n")

    # Save as csv format for human check
    default_columns = ["split", "site_name", "title", "publish_datetime", "page_depth", "gold", "url_hyperlink"]
    page_df = pd.DataFrame.from_records(page_list)[default_columns]
    page_df.to_csv(f"{args.data_path}/processed_page_list.csv", index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("--data_path", type=str, default=None)
    parser.add_argument("--page_size", type=int, default=1000000000, help="Page size per site")
    parser.add_argument("--site_size", type=int, default=100)
    parser.add_argument("--max_process", type=int, default=8)

    args = parser.parse_args()

    main()
