import requests
import traceback
import time
import tiktoken


class BaseGenerator():
    def __init__(self, model_name=None, api_key=None):
        self.model_name = \
            "gpt-4o-2024-08-06" if model_name == "gpt-4o" else \
            "gpt-4o-mini-2024-07-18" if model_name == "gpt-4o-mini" else \
            model_name
        self.api_key = api_key

        self.tokenizer_dict = {
            "gpt-4o-mini-2024-07-18": "o200k_base",
            "gpt-4o-2024-08-06": "o200k_base",
            "default": "o200k_base",
        }
        self.encoding_dict = {k: tiktoken.get_encoding(v) for k, v in self.tokenizer_dict.items()}
        self.timeout = (300, 300)

    # Extract tokenized(text)[start_pos:end]
    def get_text_part(self, text, start_pos=0, end_pos=10000000000):
        encoding = self.encoding_dict.get(self.model_name, self.encoding_dict[self.model_name])

        tokens = encoding.encode(text)
        tokens_part = tokens[start_pos:end_pos]
        text_part = encoding.decode(tokens_part)

        return text_part

    def generate_text(self, messages, seed=0, max_tokens=512):

        data = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "logprobs": True,
            "top_logprobs": 20,
        }

        compute_host = "https://api.openai.com"
        url = f"{compute_host}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        generated_text = ""
        try_count_max = 5
        for try_count in range(try_count_max):
            try:
                response = None
                data["seed"] = try_count * 100 + seed
                response = requests.post(url, json=data, headers=headers, timeout=self.timeout).json()
                generated_text = response["choices"][0]["message"]["content"]
                log_probs = response["choices"][0]["logprobs"]["content"]
                time.sleep(1.0)
                break
            except Exception:
                if try_count + 1 == try_count_max:
                    print("Error count reaches max")
                    print(response)
                    print(traceback.format_exc())
                    time.sleep(1.0)
                else:
                    time.sleep(min(5 * 2 ** try_count, 60))
                    continue

        return generated_text, log_probs
