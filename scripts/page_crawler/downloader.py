import time
import os
from glob import glob
import traceback
import subprocess
import re


class Downloader():
    def __init__(self, download_tool, data_raw_folder, site_save_folder):

        self.download_tool = download_tool
        self.data_raw_folder = data_raw_folder
        self.site_save_folder = site_save_folder.replace("/", "-").replace(".", "-")
        self.save_folder = f'{self.data_raw_folder}/{self.site_save_folder}'
        os.makedirs(self.save_folder, exist_ok=True)

        self.path_set = set()
        for path in glob(f"{self.data_raw_folder}/{self.save_folder}/*"):
            self.path_set.add(path)
        print(f"Exist file size of {self.site_save_folder} is {len(self.path_set)}")

        self.curl_command = "curl"

    def curl_download(self, url, crawl_delay, try_count):

        for now_count in range(try_count):
            time.sleep(crawl_delay)
            try:
                command = [self.curl_command, "-L", url]
                res = subprocess.run(command, capture_output=True)
                byte_text = res.stdout
                if len(byte_text) < 10:
                    raise Exception()
                break
            except Exception:
                if now_count == try_count-1:
                    raise Exception(f"Connection failed\nError:{traceback.format_exc()}")
                continue

        return byte_text

    # Download specified url and save to the "save_path"
    def download(self, url, reget=False, not_save=False, crawl_delay=1, try_count=5):

        # Generate save path
        if len(url) > 220:
            url_replaced = url.replace("/", "_")
            save_path = f'{self.save_folder}/{url_replaced[0:200] + "---" + url_replaced[-20:]}'
        else:
            url_replaced = url.replace("/", "_")
            save_path = f'{self.save_folder}/{url_replaced}'

        # If already downloaded, load it.
        if reget is False and save_path in self.path_set:
            with open(save_path, "rb") as f:
                byte_text = f.read()
        else:
            # Download
            if self.download_tool == "curl":
                byte_text = self.curl_download(url, crawl_delay, try_count)
            else:
                raise Exception("Not implemented")

            # Save
            if not_save is False:
                with open(save_path, "wb")as f:
                    f.write(byte_text)

        return byte_text, save_path
