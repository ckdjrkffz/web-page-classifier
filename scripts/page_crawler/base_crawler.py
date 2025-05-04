import chardet
import urllib.robotparser
from .downloader import Downloader


class BaseCrawler():
    def __init__(self):
        # Need set data_raw_folder, site_netloc, site_domain in child class
        pass

    def set_downloader(self, data_raw_folder, site_save_folder):
        self.downloader = Downloader("curl", data_raw_folder, site_save_folder)

    def set_robot_parser(self, site_domain):
        # Set robot file parser
        self.robot_parser = urllib.robotparser.RobotFileParser()
        robots_txt_url = f'{site_domain}/robots.txt'
        byte_text, _ = self.downloader.download(robots_txt_url, not_save=True)
        self.robot_parser.parse(byte_text.decode().split("\n"))

        crawl_delay_value = self.robot_parser.crawl_delay("*")
        self.crawl_delay = crawl_delay_value if crawl_delay_value is not None else 1

    def check_robots_txt(self, url):
        return self.robot_parser.can_fetch("*", url)

    def detect_encoding(self, byte_text, url, depth):
        if depth == 0:
            default_encoding = chardet.detect(byte_text)["encoding"]
            if default_encoding != "utf-8":
                self.valid_encoding_cand_list = ["utf-8", default_encoding]
            else:
                self.valid_encoding_cand_list = ["utf-8"]

        text = None
        for encoding_cand in self.valid_encoding_cand_list:
            try:
                text = byte_text.decode(encoding=encoding_cand)
                encoding = encoding_cand
            except Exception:
                continue

        if text is None:
            try:
                print(f"Default encoding is cannot used: {url}")
                encoding_cand = chardet.detect(byte_text)["encoding"]
                text = byte_text.decode(encoding=encoding_cand)
                encoding = encoding_cand
            except Exception:
                print("Cannot detect valid text encoding")
                print(url, byte_text[0:1000])
                encoding = None
                text = byte_text

        return encoding, text
