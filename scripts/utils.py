from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from tqdm import tqdm
import traceback
import itertools
from multiprocessing import Manager, get_context


def thread_process_crawl(site_list, func_args, executor_type="thread", max_workers=32):

    processed_item_list = []

    executor_class = \
        ThreadPoolExecutor if executor_type == "thread" else \
        ProcessPoolExecutor if executor_type == "process" else \
        None

    with executor_class(max_workers=max_workers) as executor:
        futures = []
        for crawler in site_list:
            func = crawler.page_list_crawl
            future = executor.submit(func, *func_args)
            futures.append(future)
        for future in as_completed(futures):
            try:
                processed_item_list += future.result()
            except Exception:
                raise Exception(traceback.format_exc())

    return processed_item_list


def thread_process_crawl_index(site_list, func_args, executor_type="thread", max_workers=32):

    processed_item_list = []

    executor_class = \
        ThreadPoolExecutor if executor_type == "thread" else \
        ProcessPoolExecutor if executor_type == "process" else \
        None

    with executor_class(max_workers=max_workers) as executor:
        futures = []
        for crawler in site_list:
            func = crawler.crawl_wrapper
            future = executor.submit(func, *func_args)
            futures.append(future)
        for future in as_completed(futures):
            try:
                processed_item_list += future.result()
            except Exception:
                raise Exception(traceback.format_exc())

    return processed_item_list


# called from "thread_process" func
def thread_process_inner(inner_item_list, func, func_args, progress_queue):
    result = []
    for item in inner_item_list:
        result.append(func(item, *func_args))
        progress_queue.put(1)
    return result


# Multi processing. Processed by "ThreadPoolExecutor" or "ProcessPoolExecutor".
def thread_process(item_list, func, func_args, executor_type="thread", max_workers=32):

    processed_item_list = []

    if executor_type == "thread":
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for item in item_list:
                future = executor.submit(func, item, *func_args)
                futures.append(future)
            completed_list = tqdm(as_completed(futures), total=len(item_list))
            for future in completed_list:
                try:
                    processed_item_list.append(future.result())
                except Exception:
                    raise Exception(traceback.format_exc())

    elif executor_type == "process":
        with Manager() as manager:
            progress_queue = manager.Queue()
            processed_item_list = []

            batches = [item_list[i::max_workers] for i in range(max_workers)]

            ctx = get_context("spawn")
            with ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx) as executor:
                futures = [
                    executor.submit(thread_process_inner, batch, func, func_args, progress_queue)
                    for batch in batches
                ]

                with tqdm(total=len(item_list)) as pbar:
                    finished = 0
                    while finished < len(item_list):
                        progress_queue.get()
                        pbar.update(1)
                        finished += 1

                for future in futures:
                    try:
                        processed_item_list.extend(future.result())
                    except Exception:
                        raise Exception(traceback.format_exc())

    return processed_item_list
