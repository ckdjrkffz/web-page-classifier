# Web Page Classification using LLMs for Crawling Support

This is code of our paper "Web Page Classification using LLMs for Crawling Support"

[Paper Link (arXiv)](Coming Soon)


## Setup

- Python version is 3.10+ (The experiment was conducted using Python 3.10.5)
- Instrall libraries by using requirements.txt.
```
pip install -r requirements.txt
```
- Copy `config/config_template.json` and generate `config/config.json`. Then, set the OpenAI API key in this file.

## How to use

### Crawl

#### Crawl all web pages
```
python -u crawl.py \
--data_path ./data/page_json/data_sample \
--disable_page_reget --page_size 10000
```

### Crawl index page
- crawl only index page, and collect contents page from it.
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

- Arguments:
    - `--classification_method`: Page classification method. Options are below:
        - all: Treat all pages as index pages
        - rule: Classification by rule-based.
        - llm: Classification by LLM (gpt-4o-mini or gpt-4o)
    - `--generation_model_name`: If you use LLMs, please specify the model name here.
    - `--llm_input_list`: If you use LLMs, please specify the input to the LLMs.

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

#### GPT-4o (Input: Title + Body text)

```
python -u inference.py \
--data_path ./data/page_json/data_sample \
--prediction_data_path ./data/prediction_json/data_sample_gpt-4o-mini_title_main \
--data_split test \
--classification_method llm --llm_input_list title main_text --generation_model_name gpt-4o

python -u evaluate.py \
--prediction_data_path ./data/prediction_json/data_sample_gpt-4o_title_main \
--data_split test
```

## Licence
Apache License 2.0