# Web Page Classification using LLMs for Crawling Support

This repository contains the code for our paper "Web Page Classification using LLMs for Crawling Support"

[arXiv link](https://arxiv.org/abs/2505.06972)


## Setup

- Python Version: 3.10+ (The experiment was conducted using Python 3.10.5)
- Install dependencies using requirements.txt.
```
pip install -r requirements.txt
```
- Copy `config/config_template.json` to `config/config.json`. Then, set the OpenAI API key in this file.

## How to use

### Crawl

#### Crawl all web pages
```
python -u crawl.py \
--data_path ./data/page_json/data_sample \
--disable_page_reget --page_size 10000
```

### Crawl index page

Crawl only index page, and collect contents page from it.
```
python -u crawl_index.py \
--data_path ./data/page_json/data_sample \
--disable_page_reget
```

### Preprocess

```
python -u preprocess.py \
--data_path ./data/page_json/data_sample
```

### Inference & Evaluate

The following are some examples. For details, refer to the help for each script argument.

#### All Pages (without classification)

```
python -u inference.py \
--data_path ./data/page_json/data_sample \
--prediction_data_path ./data/prediction_json/data_sample_all \
--data_split test \
--classification_method all

python -u evaluate.py \
--prediction_data_path ./data/prediction_json/data_sample_all \
--data_split test
```

#### Rule-Based

```
python -u inference.py \
--data_path ./data/page_json/data_sample \
--prediction_data_path ./data/prediction_json/data_sample_rule \
--data_split test \
--classification_method rule

python -u evaluate.py \
--prediction_data_path ./data/prediction_json/data_sample_rule \
--data_split test
```

#### GPT-4o-mini (Input: Title)

```
python -u inference.py \
--data_path ./data/page_json/data_sample \
--prediction_data_path ./data/prediction_json/data_sample_gpt-4o-mini_title \
--data_split test \
--classification_method llm --llm_input_list title --generation_model_name gpt-4o-mini

python -u evaluate.py \
--prediction_data_path ./data/prediction_json/data_sample_gpt-4o-mini_title \
--data_split test
```

#### Hybrid method of GPT-4o (Input: Title + Body text) and "All Pages"

```
python -u inference.py \
--data_path ./data/page_json/data_sample \
--prediction_data_path ./data/prediction_json/data_sample_gpt-4o_title_main \
--data_split test \
--classification_method llm --llm_input_list title main_text --generation_model_name gpt-4o

python -u evaluate.py \
--prediction_data_path ./data/prediction_json/data_sample_gpt-4o_title_main \
--data_split test --use_mix
```

## Licence
Apache License 2.0