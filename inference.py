from collections import defaultdict
from tqdm import tqdm
import os
import json
import argparse
import random
import itertools
import pandas as pd

from scripts.page_classifier import PageClassifier
from scripts.utils import thread_process

import warnings
warnings.simplefilter("once")


def main():

    print("Start preparing")

    random.seed(0)

    with open("config/config.json")as f:
        config = json.load(f)
    api_key = config["api_key"]

    config_file_name = "target_site.csv"
    generation_model_name = args.generation_model_name

    page_list = []
    with open(f"{args.data_path}/processed_page_list_{args.data_split}.jsonl")as f:
        for page in f:
            page_list.append(json.loads(page))

    site_dict = defaultdict(int)
    for page in page_list:
        page["collect_order_id"] = site_dict[page["site_name"]]
        site_dict[page["site_name"]] += 1

    target_site_list = pd.read_csv(f"config/{config_file_name}").to_dict(orient="records")
    target_site_list = target_site_list[0:args.site_size]
    target_site_name_list = [t["site_name"] for t in target_site_list]

    page_list = list(itertools.chain.from_iterable(
        [[page for page in page_list if page["site_name"] == site_name][0:args.page_size]
            for site_name in target_site_name_list]
    ))

    page_division_dict = defaultdict(list)
    for page in page_list:
        page_division_dict[page["site_name"]].append(page)
    for site_name, sub_page_list in page_division_dict.items():
        print(f"Site {site_name}: size is {len(sub_page_list[0:args.page_size])}")
    page_list = list(itertools.chain.from_iterable(
        [sub_page_list[0:args.page_size] for _, sub_page_list in page_division_dict.items()]
    ))

    # Classify, use subprocess
    print("Classify page")
    page_classifier = PageClassifier(model_name=generation_model_name, api_key=api_key)
    func = \
        page_classifier.classify_gold if args.classification_method == "gold" else \
        page_classifier.classify_all if args.classification_method == "all" else \
        page_classifier.classify_rule if args.classification_method == "rule" else \
        page_classifier.classify_llm if args.classification_method == "llm" else \
        None
    func_args = \
        (args.llm_input_list, args.llm_input_main_text_length) if args.classification_method in ["llm"] else \
        ()

    if args.classification_method in ["llm"]:
        page_list = thread_process(page_list, func, func_args, executor_type="thread", max_workers=args.max_thread)
    else:
        page_list = [func(page, *func_args) for page in tqdm(page_list)]

    # Result are sorted by page_id
    page_list = sorted(page_list, key=lambda x: x["page_id"])

    os.makedirs(args.prediction_data_path, exist_ok=True)
    with open(f"{args.prediction_data_path}/prediction_page_list_{args.data_split}.jsonl", "w")as f:
        for page in page_list:
            f.write(json.dumps(page, ensure_ascii=False)+"\n")

    default_columns = ["split", "site_name", "title", "publish_datetime", "page_depth", "gold", "prediction", "url_hyperlink"]
    page_df = pd.DataFrame.from_records(page_list)[default_columns]
    page_df.to_csv(f"{args.prediction_data_path}/prediction_page_list_{args.data_split}.csv", index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("--data_path", type=str, help="Path to dataset to be loaded")
    parser.add_argument("--prediction_data_path", type=str, help="Path where prediction results are saved")
    parser.add_argument("--page_size", type=int, default=1000000000, help="Number of pages to process per site")
    parser.add_argument("--site_size", type=int, default=100, help="Max website size to process")
    parser.add_argument("--max_thread", type=int, default=256, help="Max thread size")
    parser.add_argument("--classification_method", type=str, help=(
            "Classification method. Select from below: "
            "all: Tread all pages as index pages",
            "rule: Classifiy by rule-base (use title word count)",
            "llm: Use LLM. The model is specified in --generation_model_name",
            "gold: Use gold label",
        ),
        choices=["all", "rule", "llm", "gold"]
    )
    parser.add_argument("--llm_input_list", type=str, nargs="*", help=(
            "If you use LLMs, please specify the input to the LLMs (multipled selection allowed)",
            "title: Title of web pages",
            "main_text: Body of the web pages"
        ),
        choices=["title", "main_text"]
    )
    parser.add_argument("--llm_input_main_text_length", type=int, default=500, help="Max length of web page body")
    parser.add_argument("--generation_model_name", type=str, default="None", help=(
            "Generation model name. Currently, supports gpt-4o-mini and gpt-4o"
        ),
        choices=["gpt-4o-mini", "gpt-4o"]
    )
    parser.add_argument("--data_split", type=str, default="test", help="Data split to use", choices=["dev", "test"])

    args = parser.parse_args()

    main()
