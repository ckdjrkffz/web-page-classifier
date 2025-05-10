from collections import defaultdict
import json
import datetime
import argparse
import numpy as np
import itertools
import pandas as pd

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

import warnings
warnings.simplefilter("once")


def main():

    page_list = []
    with open(f"{args.prediction_data_path}/prediction_page_list_{args.data_split}.jsonl")as f:
        for page in f:
            page_list.append(json.loads(page))

    site_dict = defaultdict(int)
    for page in page_list:
        page["collect_order_id"] = site_dict[page["site_name"]]
        site_dict[page["site_name"]] += 1

    config_file_name = "target_site.csv"
    target_site_list = pd.read_csv(f"config/{config_file_name}").to_dict(orient="records")
    target_site_list = [
        site for site in target_site_list
        if len([page for page in page_list if page["site_name"] == site["site_name"]]) > 0
    ]

    target_site_name_list_dict = {}
    target_site_name_list_dict["all"] = \
        [site["site_name"] for site in target_site_list]
    target_site_name_list_dict["clean"] = \
        [site["site_name"] for site in target_site_list if site["split"] in ["dev", "test"]]
    target_site_name_list_dict["noisy"] = \
        [site["site_name"] for site in target_site_list if site["split"] in ["test-noisy"]]

    # Preprocess
    page_list = sorted(page_list, key=lambda x: x["page_id"])

    for page in page_list:
        page["publish_datetime_obj"] = \
            datetime.datetime.strptime(page["publish_datetime"], "%Y-%m-%d") if page["publish_datetime"] != "None" else \
            datetime.datetime.strptime("1901-01-01", "%Y-%m-%d")

    target_page_datetime_span = 5

    site_to_last_datetime = defaultdict()
    for site_name in target_site_name_list_dict["all"]:
        site_page_list = [page for page in page_list if page["site_name"] == site_name]
        last_publish_datetime_obj = sorted([page["publish_datetime_obj"] for page in site_page_list])[-1]
        site_to_last_datetime[site_name] = last_publish_datetime_obj

    for page in page_list:
        start_datetime = site_to_last_datetime[page["site_name"]] - datetime.timedelta(days=target_page_datetime_span)
        end_datetime = site_to_last_datetime[page["site_name"]]
        page["flag_eval_target"] = (start_datetime <= page["publish_datetime_obj"] <= end_datetime)

    url_to_page_dict = {page["url"]: page for page in page_list}

    # Statics
    print("Data statics:")
    print("site_name,All,Gold index,Predicted index,Past 1 day,Past 5 day,Past 30 day")
    for site_name in target_site_name_list_dict["all"]:
        site_page_list = [page for page in page_list if page["site_name"] == site_name]
        if len(site_page_list) == 0:
            continue

        all_length = len(site_page_list)
        gold_index_length = len([page for page in site_page_list if page["gold"] == "index"])
        predicted_index_length = len([page for page in site_page_list if page["prediction"] == "index"])

        target_page_length_dict = {}
        for target_page_datetime_span in [1, 5, 30]:
            for page in site_page_list:
                start_datetime = site_to_last_datetime[page["site_name"]] - datetime.timedelta(days=target_page_datetime_span)
                end_datetime = site_to_last_datetime[page["site_name"]]
                page["flag_eval_target"] = (start_datetime <= page["publish_datetime_obj"] <= end_datetime)

            target_page_list = [page for page in site_page_list if page["flag_eval_target"]]
            target_page_length_dict[target_page_datetime_span] = len(target_page_list)
        # Report statics in csv format
        print(f'{site_name},{all_length},{gold_index_length},{predicted_index_length},{target_page_length_dict[1]},{target_page_length_dict[5]},{target_page_length_dict[30]},')
    print()

    # Classification performance, evaluated by accuracy and precision, recall, f1 socre
    print("Result:")
    result_dict = defaultdict(list)
    for site_name in target_site_name_list_dict["clean"]:
        site_page_list = [page for page in page_list if page["site_name"] == site_name]

        convert_dict = {"contents": 0, "index": 1}
        x = [convert_dict[page["prediction"]] for page in site_page_list]
        y = [convert_dict[page["gold"]] for page in site_page_list]

        result_dict["accuracy"].append(accuracy_score(y, x))
        result_dict["precision"].append(precision_score(y, x))
        result_dict["recall"].append(recall_score(y, x))
        result_dict["f1"].append(f1_score(y, x))

    # Coverage performance, evaluated on how many percent of the new pages the system can reach from the index page.
    excluded_url_list = []
    for data_type in ["clean", "noisy"]:
        for target_page_datetime_span in [1, 30]:
            for page in page_list:
                start_datetime = site_to_last_datetime[page["site_name"]] - datetime.timedelta(days=target_page_datetime_span)
                end_datetime = site_to_last_datetime[page["site_name"]]
                page["flag_eval_target"] = (start_datetime <= page["publish_datetime_obj"] <= end_datetime)

            for site_name in target_site_name_list_dict[data_type]:
                site_page_list = [page for page in page_list if page["site_name"] == site_name]

                target_page_list = [page for page in site_page_list if page["flag_eval_target"]]
                target_url_set = set([page["url"] for page in target_page_list])

                for top_count in [10, 30, 100, 300, 1000]:
                    # Hybrid setting: Use shallow page (nearest homepage) and LLM predicted page
                    for page_num, page in enumerate(site_page_list):
                        if args.use_mix and page_num < int(top_count / 2):
                            page["index_probability_copy"] = 1.0
                        else:
                            page["index_probability_copy"] = page["index_probability"]

                    index_page_list = \
                        sorted(site_page_list, key=lambda x: (-x["index_probability_copy"], x["collect_order_id"]))[0:top_count]

                    linked_url_from_index_set = set(itertools.chain.from_iterable(
                        [[page["url"]] + page["child_url_list"] for page in index_page_list]
                    ))

                    # Find new pages that can be reached by following the index pages from index pages.
                    max_loop_step = 10
                    for loop_step in range(max_loop_step):
                        old_size = len(linked_url_from_index_set)
                        target_linked_url_set = target_url_set & linked_url_from_index_set
                        second_linked_url_from_index_set = set(itertools.chain.from_iterable(
                            [url_to_page_dict.get(url, {}).get("child_url_list", []) for url in target_linked_url_set]
                        ))
                        linked_url_from_index_set = linked_url_from_index_set | second_linked_url_from_index_set

                        if len(linked_url_from_index_set) == old_size:
                            break

                    linked_page_count = len(target_url_set & linked_url_from_index_set)
                    target_page_count = len(target_url_set)
                    linked_page_ratio = linked_page_count / target_page_count

                    result_dict["-".join([data_type, str(target_page_datetime_span), str(top_count)])].append(linked_page_ratio)

                    if target_page_datetime_span == 1 and top_count == 1000:
                        excluded_url_list += list(target_url_set - linked_url_from_index_set)

    # Report result in csv format
    for key in result_dict.keys():
        print(f"{key}", end=",")
    print()
    for value in result_dict.values():
        print(f"{np.mean(value):.4f}", end=",")
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("--prediction_data_path", type=str, help="Path to prediction results to be loaded")
    parser.add_argument("--data_split", type=str, default="test", help="Data split to use", choices=["dev", "test"])
    parser.add_argument("--use_mix", action="store_true", help=(
        "If true, hybrid method that uses half of the pages specified prediction results and the other half for shallow-level pages that are not based on the prediction results as the starting points"
    ))

    args = parser.parse_args()

    main()
