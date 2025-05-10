from bs4 import BeautifulSoup
import datetime
import datetime
from collections import deque
from urllib.parse import urlparse, urljoin
import magic
import time
import traceback

from .base_crawler import BaseCrawler


class GeneralCrawler(BaseCrawler):
    def __init__(
        self,
        site_name, site_root_url,
        disable_page_reget, max_depth,
        crawl_link_setting, data_raw_folder, crawl_log_interval
    ):
        super().__init__()

        self.site_name = site_name
        self.target_root_url = site_root_url

        parsed_url = urlparse(self.target_root_url)
        self.site_scheme = parsed_url.scheme
        self.site_netloc = parsed_url.netloc
        self.site_path = parsed_url.path
        self.site_domain = f"{self.site_scheme}://{self.site_netloc}"
        self.check_target_root = self.site_domain

        self.max_depth = max_depth

        self.data_raw_folder = data_raw_folder

        self.download_judge_dict = {}
        self.this_time_download_set = set()

        self.disable_page_reget = disable_page_reget
        self.crawl_link_setting = crawl_link_setting
        self.valid_encoding_cand_list = []

        self.crawl_log_interval = crawl_log_interval

        self.set_downloader(self.data_raw_folder, self.site_netloc)
        self.set_robot_parser(self.site_domain)

    def page_list_crawl(
        self, max_page_size=1, target_file_type=["html"]
    ):
        link_queue = deque()
        link_queue.append((self.target_root_url, "", 0))
        page_list = []
        start_time = time.time()
        self.this_time_download_set.add(self.target_root_url)

        collected_page_count = 0

        while True:
            if len(link_queue) == 0:
                elasped_time = datetime.timedelta(seconds=time.time() - start_time)
                print(f"End crawling {collected_page_count} pages of {self.site_name} because crawed all pages, elasped time is {elasped_time}")
                break
            if collected_page_count >= max_page_size:
                elasped_time = datetime.timedelta(seconds=time.time() - start_time)
                print(f"End crawling {collected_page_count} pages of {self.site_name}, elasped time is {elasped_time}")
                break

            url, parent_url, depth = link_queue.popleft()

            if self.check_robots_txt(url) is False:
                continue

            url_split = urlparse(url).path.split(".")
            if len(url_split) >= 2 and len(url_split[-1]) <= 5:
                tmp_file_type = url_split[-1]
            else:
                tmp_file_type = ""

            # Download only if domain is match with root (search in-domain page)
            if url.startswith(self.check_target_root) is False:
                continue

            if tmp_file_type in ["jpg", "jpeg", "png", "xml", "xlsx", "x-empty", "mp3", "mp4", "zip"]:
                continue

            if self.disable_page_reget:
                page_reget = False
            else:
                page_reget = True

            try:
                byte_text, save_path = self.downloader.download(
                    url, page_reget=page_reget, crawl_delay=self.crawl_delay
                )
            except Exception as e:
                if str(e).startswith("Connection failed"):
                    print(f"Cannot access to {url} because of connection error")
                    continue
                else:
                    print(f"Cannot access to {url}, parent: {parent_url}")
                    print(traceback.format_exc())
                    continue

            # Detect file format
            file_type = magic.from_buffer(byte_text, mime=True).split("/")[-1]
            file_type = \
                "html" if file_type == "javascript" else \
                file_type

            # Detect encoding
            if file_type == "html":
                encoding, text = self.detect_encoding(byte_text, url, depth)
            else:
                encoding = None
                text = None

            child_url_list = []
            if file_type == "html" and depth + 1 < self.max_depth:
                soup = BeautifulSoup(text, "html.parser")
                link_list = [element.get("href").strip() for element in soup.find_all("a", href=True)]
                for link in link_list:
                    try:
                        parsed_link = urlparse(link)
                    except Exception:
                        print(f"Failed to parse link: {link}")
                        continue

                    if parsed_link.scheme not in ["", "http", "https"]:
                        continue

                    if parsed_link.netloc == "":
                        link = urljoin(url, link)

                    # Remove flagment
                    link = urlparse(link)._replace(fragment="").geturl()

                    child_url_list.append(link)

            # Remove duplicate
            processed_child_url_list = []
            for link in child_url_list:
                if link in self.this_time_download_set:
                    continue
                self.this_time_download_set.add(link)
                processed_child_url_list.append(link)

            # Append child url to queue
            for link in processed_child_url_list:
                link_queue.append((link, url, depth+1))

            # Append downloaded page to list
            if file_type in target_file_type + ["html"]:
                page_list.append({
                    "url": url,
                    "parent_url": parent_url,
                    "child_url_list": child_url_list,
                    "save_path": save_path,
                    "site_name": self.site_name,
                    "file_type": file_type,
                    "encoding": encoding,
                    "page_depth": depth,
                })

            if file_type in target_file_type:
                collected_page_count += 1
                if collected_page_count % self.crawl_log_interval == 0 and collected_page_count > 0:
                    elasped_time = datetime.timedelta(seconds=time.time() - start_time)
                    print(f"Crawled {collected_page_count} pages of {self.site_name}, current depth is {depth}, elasped time is {elasped_time}")

        return page_list
