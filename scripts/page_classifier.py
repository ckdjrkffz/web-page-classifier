import random
import textwrap
import re
import traceback

from .base_generator import BaseGenerator


class PageClassifier(BaseGenerator):
    def __init__(self, **kwargs):

        super().__init__(**kwargs)

    def generate_prompt(self, title, main_text):
        if title is None:
            raise Exception("Not implemented")

        # There are two types of prompt.
        # The first is for entering only the title, and the second is for entering the title and main text.
        if main_text is None:
            prompt_text = textwrap.dedent("""\
                You will be given the title of a web page.
                Please determine whether this page belongs to "Index page" or "Content page". The definitions are as follows:

                1. Index page
                A page that lists other web pages.
                Title Example 1: "Latest News"
                Title Example 2: "Apple news and analysis"
                Title Example 3: "Sport - Scores, Fixtures, News"
                Title Example 4: "Asia"
                Title Example 5: "John Smith" (A page that lists articles written by a reporter named John Smith.)

                2. Content page
                Pages other than the index page. In other words, pages that contain information such as news articles and columns.
                This category also includes advertising pages and error pages because they are not index pages.
                Title Example 1: "Russia detains Uzbek man over general's killing in Moscow"
                Title Example 2: "Four paths Trudeau can take as his leadership faces scrutiny"
                Title Example 3: "Ridley Scott's RSA Sets Doc 'Surviving Black Hawk Down' at Netflix"
                Title Example 4: "Brad Pitt Speaks Out on 'Awful' Scam That Cost French Woman $850,000"
                Title Example 5: "Access to this page has been denied"

                Generally, the title of the content page is longer, and the title of the index page is shorter.
                Finally, please classify the page as either "Index page" or "Content page". Please follow the format below and do not write anything unnecessary.

                ###Example 1###
                [Input]
                Title: "Russia detains Uzbek man over general's killing in Moscow"
                [Output]
                Page type: Content page

                ###Example 2###
                [Input]
                Title: "Apple news and analysis"
                [Output]
                Page type: Index page

                Now, please output the appropriate page type for the following input.
                [Input]
                """) \
                + f"Title: {title}\n" \
                + "[Output]\n"

        elif main_text is not None:
            prompt_text = textwrap.dedent("""\
                You will be given the title and part of the processed main text of a web page.
                Please determine whether this page belongs to "Index page" or "Content page". The definitions are as follows:

                1. Index page
                A page that lists other web pages.
                Title Example 1: "Latest News"
                Title Example 2: "Apple news and analysis"
                Title Example 3: "Sport - Scores, Fixtures, News"
                Title Example 4: "Asia"
                Title Example 5: "John Smith" (A page that lists articles written by a reporter named John Smith.)

                2. Content page
                Pages other than the index page. In other words, pages that contain information such as news articles and columns.
                This category also includes advertising pages and error pages because they are not index pages.
                Title Example 1: "Russia detains Uzbek man over general's killing in Moscow"
                Title Example 2: "Four paths Trudeau can take as his leadership faces scrutiny"
                Title Example 3: "Ridley Scott's RSA Sets Doc 'Surviving Black Hawk Down' at Netflix"
                Title Example 4: "Brad Pitt Speaks Out on 'Awful' Scam That Cost French Woman $850,000"
                Title Example 5: "Access to this page has been denied"

                First, check the title. Generally, the title of the content page is longer, and the title of the index page is shorter.
                If you cannot make a decision based on the title, please check the main text next.
                If the main text is highly related to the title, it is a content page.
                If the content corresponding to the title is not included in the main text, or if the main text contains a lot of content that is not directly related to the title, it is an index page.
                Please note that the main text is automatically extracted from the HTML, and any hyperlinks to other articles or noisy text are removed beforehand.

                Finally, please classify the page as either "Index page" or "Content page". Please follow the format below and do not write anything unnecessary.

                ###Example 1###
                [Input]
                Title: "Russia detains Uzbek man over general's killing in Moscow"
                Main text: (The main text of the target page. Omitted in the example.)
                [Output]
                Page type: Content page

                ###Example 2###
                [Input]
                Title: "Apple news and analysis"
                Main text: (The main text of the target page. Omitted in the example.)
                [Output]
                Page type: Index page

                Now, please output the appropriate page type for the following input.
                [Input]
                """) \
                + f"Title: {title}\n" \
                + f"Main text: {main_text}\n" \
                + "[Output]\n"

        return prompt_text

    def classify_gold(self, page):

        page["index_probability"] = 1.0 if page["gold"] == "index" else 0.0
        page["prediction"] = "contents" if page["index_probability"] < 0.5 else "index"

        return page

    def classify_all(self, page):

        page["index_probability"] = 1.0
        page["prediction"] = "contents" if page["index_probability"] < 0.5 else "index"

        return page

    def classify_rule(self, page):

        page["index_probability"] = \
            1.0 if len(page["title"].split()) <= 9 else \
            0.0
        page["prediction"] = "contents" if page["index_probability"] < 0.5 else "index"

        return page

    def classify_llm(self, page, llm_input_list, llm_input_main_text_length):

        if "title" in llm_input_list:
            title = page["title"].strip()
        else:
            title = None

        if "main_text" in llm_input_list:
            main_text = self.get_text_part(page["main_text"], start_pos=0, end_pos=llm_input_main_text_length).strip()
            if main_text == "":
                main_text = "There is no main text."
        else:
            main_text = None

        prompt_text = self.generate_prompt(title, main_text)
        messages = [{"role": "system", "content": prompt_text}]

        # Repeat {try_count_max} times until you get the appropriate format output.
        try_count_max = 3
        for try_count in range(try_count_max):
            try:
                generated_text, _ = self.generate_text(messages, seed=try_count, max_tokens=64)

                match = re.search(r"Page type: (.*? page)", generated_text)
                if match is None:
                    raise Exception(f"Incorrected judge\nGenerated text: {generated_text}")

                result = match.group(1)
                if result == "Content page":
                    index_prob = 0.0
                elif result == "Index page":
                    index_prob = 1.0
                else:
                    raise Exception(f"Incorrected judge\nGenerated text: {generated_text}")
                break
            except Exception:
                if try_count + 1 == try_count_max:
                    print("Try count reaches max, so use default value.")
                    print(traceback.format_exc())
                    index_prob = 0.0
                else:
                    continue

        page["index_probability"] = index_prob
        page["prediction"] = "contents" if page["index_probability"] < 0.5 else "index"

        return page
