import re

TEST_for_markdown_to_scrapbox = "### A is level 3 header\n## B is level 2 header"


def markdown_to_scrapbox(text):
    """easy conversion from markdown to scrapbox
    >>> print(markdown_to_scrapbox(TEST_for_markdown_to_scrapbox))
    [* A is level 3 header]
    [** B is level 2 header]
    """
    # Replace '### ' with '[* ' and close with ']'
    text = re.sub(r"### (.+)", r"[* \1]", text)
    # Replace '## ' with '[** ' and close with ']'
    text = re.sub(r"## (.+)", r"[** \1]", text)
    return text


def extract_microformat_to_ai(input_str):
    """
    Extracts text enclosed between `TO_AI:` and backticks from the input string.

    Args:
        input_str (str): The input string containing the target text.

    Returns:
        str: The extracted text, or None if no match is found.

    Examples:
        >>> extract_microformat_to_ai("aaa`TO_AI: bbb`ccc")
        'bbb'

        >>> extract_microformat_to_ai("Some text without TO_AI")
        ...
    """
    pattern = r"`TO_AI: (.*?)`"
    match = re.search(pattern, input_str)
    if match:
        extracted_text = match.group(1)
        return extracted_text
    else:
        return None


if __name__ == "__main__":
    import doctest

    doctest.testmod()
