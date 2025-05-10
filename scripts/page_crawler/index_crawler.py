import re
import datetime
import time
import itertools
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

from .base_crawler import BaseCrawler
from .downloader import Downloader

import warnings
warnings.simplefilter("once")


class IndexCrawler(BaseCrawler):
    def __init__(self, args, site_name, root_url_list=None, homepage_url=None):
        super().__init__()

        self.site_name = site_name
        self.root_url_list = root_url_list

        self.page_reget = (args.disable_page_reget is False)
        self.page_size = args.page_size

        self.target_root_url = \
            homepage_url if homepage_url is not None else \
            root_url_list[0]
        parsed_url = urlparse(self.target_root_url)
        self.site_scheme = parsed_url.scheme
        self.site_netloc = parsed_url.netloc
        self.site_domain = f"{self.site_scheme}://{self.site_netloc}"

        self.data_raw_folder = "./data/index_raw"

        self.set_downloader(self.data_raw_folder, self.site_netloc)
        self.set_robot_parser(self.site_domain)

    def crawl_wrapper(self):

        if self.site_name == "TechCrunch":
            return self.process_techcrunch()
        elif self.site_name == "Mongabay":
            return self.process_mongabay()
        elif self.site_name == "Space.com":
            return self.process_space_com()
        else:
            return self.process_standard_sitemap()

    # Crawl index page by using XML sitemap
    def process_standard_sitemap(self):

        start_time = time.time()

        site_name = self.site_name
        root_url_list = self.root_url_list

        print(f"Start process {site_name}")

        page_list = []
        parsed_url = urlparse(root_url_list[0])
        top_page_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        link_list = []
        for root_url in root_url_list:
            byte_text, save_path = self.downloader.download(root_url, page_reget=self.page_reget)
            text = byte_text.decode()
            link_list += re.findall(rf"<loc>({top_page_url}/.*?)</loc>", text)
        link_list = link_list[0:self.page_size]
        for link_num, link in enumerate(link_list):
            byte_text, save_path = self.downloader.download(link, page_reget=self.page_reget)
            text = byte_text.decode()
            content_link_list = re.findall(rf"<loc>({top_page_url}/.*?)</loc>", text)
            for content_link in content_link_list:
                page_list.append({
                    "url": content_link,
                    "site_name": site_name,
                })

            elasped_time = datetime.timedelta(seconds=time.time() - start_time)
            if (link_num + 1) % 100 == 0:
                print(f"Crawled {link_num + 1} pages of {self.site_name}, elasped time is {elasped_time}")
            if link_num + 1 == len(link_list):
                print(f"End crawling {link_num + 1} pages of {self.site_name}, elasped time is {elasped_time}")

        return page_list

    def process_techcrunch(self):

        start_time = time.time()

        page_list = []
        site_name = self.site_name
        print(f"Start process {site_name}")

        link_list = [f"https://techcrunch.com/latest/page/{i}/" for i in range(1, 13380+1)][0:self.page_size]
        for link_num, link in enumerate(link_list):
            byte_text, save_path = self.downloader.download(link, page_reget=self.page_reget)
            text = byte_text.decode()

            soup = BeautifulSoup(text, "html.parser")
            content_link_list = [element.get("href") for element in soup.find_all("a", attrs={"class": "loop-card__title-link"}, href=True)]
            for content_link in content_link_list:
                page_list.append({
                    "url": content_link,
                    "site_name": site_name,
                })

            elasped_time = datetime.timedelta(seconds=time.time() - start_time)
            if (link_num + 1) % 100 == 0:
                print(f"Crawled {link_num + 1} pages of {self.site_name}, elasped time is {elasped_time}")
            if link_num + 1 == len(link_list):
                print(f"End crawling {link_num + 1} pages of {self.site_name}, elasped time is {elasped_time}")

        return page_list

    def process_mongabay(self):

        start_time = time.time()

        page_list = []
        site_name = self.site_name
        print(f"Start process {site_name}")

        link_list = [f"https://news.mongabay.com/list/2024/page/{i}/" for i in range(1, 790+1)][0:self.page_size]
        for link_num, link in enumerate(link_list):
            byte_text, _ = self.downloader.download(link, page_reget=self.page_reget)
            text = byte_text.decode()

            soup = BeautifulSoup(text, "html.parser")
            soup = soup.find("div", attrs={"id": "post-results"})
            content_link_list = [element.get("href") for element in soup.find_all("a", href=True)]
            for content_link in content_link_list:
                page_list.append({
                    "url": content_link,
                    "site_name": site_name,
                })

            elasped_time = datetime.timedelta(seconds=time.time() - start_time)
            if (link_num + 1) % 100 == 0:
                print(f"Crawled {link_num + 1} pages of {self.site_name}, elasped time is {elasped_time}")
            if link_num + 1 == len(link_list):
                print(f"End crawling {link_num + 1} pages of {self.site_name}, elasped time is {elasped_time}")

        return page_list

    def process_space_com(self):

        start_time = time.time()

        page_list = []
        site_name = self.site_name
        print(f"Start process {site_name}")

        link_list = [
            f"https://www.space.com/archive/{year:04}/{month:02}"
            for year, month in list(itertools.product(range(1999, 2024+1), range(1, 12+1)))
        ][0:self.page_size]
        for link_num, link in enumerate(link_list):
            byte_text, save_path = self.downloader.download(link, page_reget=self.page_reget)
            text = byte_text.decode()
            soup = BeautifulSoup(text, "html.parser")
            content_link_list = [element.find("a", href=True).get("href") for element in soup.find_all("li", attrs={"class": "day-article"})]
            for content_link in content_link_list:
                page_list.append({
                    "url": content_link,
                    "site_name": site_name,
                })

            elasped_time = datetime.timedelta(seconds=time.time() - start_time)
            if (link_num + 1) % 100 == 0:
                print(f"Crawled {link_num + 1} pages of {self.site_name}, elasped time is {elasped_time}")
            if link_num + 1 == len(link_list):
                print(f"End crawling {link_num + 1} pages of {self.site_name}, elasped time is {elasped_time}")

        return page_list

    def process_webmd(self):

        start_time = time.time()

        page_list = []
        site_name = self.site_name
        print(f"Start process {site_name}")

        link_list = [f"https://www.webmd.com/news/articles?pg={i}" for i in range(1, 70+1)][0:self.page_size]
        for link_num, link in enumerate(link_list):
            byte_text, save_path = self.downloader.download(link, page_reget=self.page_reget)
            text = byte_text.decode()

            soup = BeautifulSoup(text, "html.parser")
            soup = soup.find(attrs={"class": "news-toc-section dyn_index_articles"})
            content_link_list = [element.get("href") for element in soup.find_all("a", href=True)]
            for content_link in content_link_list:
                page_list.append({
                    "url": content_link,
                    "site_name": site_name,
                })

            elasped_time = datetime.timedelta(seconds=time.time() - start_time)
            if (link_num + 1) % 100 == 0:
                print(f"Crawled {link_num + 1} pages of {self.site_name}, elasped time is {elasped_time}")
            if link_num + 1 == len(link_list):
                print(f"End crawling {link_num + 1} pages of {self.site_name}, elasped time is {elasped_time}")

        return page_list

    def process_scientific_american(self):

        start_time = time.time()

        page_list = []
        site_name = self.site_name
        print(f"Start process {site_name}")

        link_list = [f"https://www.scientificamerican.com/latest/?page={i}" for i in range(1, 50+1)][0:self.page_size]
        for link_num, link in enumerate(link_list):
            byte_text, save_path = self.downloader.download(link, page_reget=self.page_reget)
            text = byte_text.decode()

            soup = BeautifulSoup(text, "html.parser")
            content_link_list = [element.get("href") for element in soup.find_all("a", attrs={"class": "articleLink-2OMNo"}, href=True)]
            for content_link in content_link_list:
                content_link = urljoin("https://www.scientificamerican.com/", content_link)
                page_list.append({
                    "url": content_link,
                    "site_name": site_name,
                })

            elasped_time = datetime.timedelta(seconds=time.time() - start_time)
            if (link_num + 1) % 100 == 0:
                print(f"Crawled {link_num + 1} pages of {self.site_name}, elasped time is {elasped_time}")
            if link_num + 1 == len(link_list):
                print(f"End crawling {link_num + 1} pages of {self.site_name}, elasped time is {elasped_time}")

        return page_list
