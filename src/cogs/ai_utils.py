"""
AI Utilities for NewsBot

This module provides AI-powered functionality for the bot, including:
- Text cleaning and formatting
- Translation and summarization services
- Ad detection
"""

import re


def clean_text_output(text: str) -> str:
    """
    Cleans up text for Discord output:
    - Strips leading/trailing whitespace from each line
    - Collapses multiple newlines into one
    - Collapses multiple spaces into one
    - Removes empty lines
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\n+", "\n", cleaned)
    cleaned = re.sub(r" +", " ", cleaned)
    return cleaned


def call_chatgpt_for_news(arabic_text, openai, logger=None):
    """Call ChatGPT API to translate Arabic news, create a title, and detect ads/non-Syria content."""
    if logger:
        logger.info("[AI_UTILS] Calling ChatGPT for translation/title...")
        logger.debug(f"[AI_UTILS] Input: {arabic_text[:100]}...")

    # Use the provided openai client directly instead of creating a new instance
    client = openai  # Don't try to create a new client with openai.OpenAI()

    # Define the prompt template here
    PROMPT_TEMPLATE = """
    You're a translator specializing in converting Arabic news to English.

    TRANSLATION INSTRUCTIONS:
    1. REMOVE ALL hashtags completely (e.g., #Syria becomes Syria)
    2. REMOVE ALL Telegram links, URLs, and channel mentions
    3. REMOVE ALL promotional content (subscribe/follow messages)
    4. REMOVE ALL emojis
    5. Focus ONLY on the actual news content
    6. Make the translation as FULL and LITERAL as possible (do NOT summarize)
    7. Keep ALL factual information, do NOT omit details
    8. NEVER include original hashtags in your output
    9. NEVER include any telegram links in your output
    10. NEVER include anything about following or subscribing
    11. DO NOT SUMMARIZE. Translate the entire text as literally and completely as possible.

    TITLE INSTRUCTIONS:
    - Create a complete sentence in 3-6 words that captures the main news event
    - The title should be a grammatically complete sentence that makes sense on its own
    - Examples: "Syria Receives Aid Shipment", "Rebels Capture Strategic City", "President Announces New Policy"
    - Avoid incomplete phrases or fragments

    Format your response EXACTLY as follows:

    TITLE: [complete sentence in 3-6 words describing the main event]
    TRANSLATION: [full, literal English translation with NO hashtags, links, or promotional content]
    IS_AD: [true/false]
    IS_SYRIA_RELATED: [true/false]
    """

    # Create the complete prompt with the input text
    prompt = f"{PROMPT_TEMPLATE}\n\nArabic text:\n{arabic_text}"

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful translator."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1000,
        )

        raw_result = response.choices[0].message.content
        if logger:
            logger.info("[AI_UTILS] Received translation response")
            logger.debug(f"[AI_UTILS] Raw response: {raw_result[:100]}...")

        # Parse the response into a dictionary
        result = {}

        # Extract title
        title_match = re.search(r"TITLE:\s*(.*?)(?:\n|$)", raw_result)
        if title_match:
            result["title"] = title_match.group(1).strip()
        else:
            result["title"] = "News Update"

        # Extract translation
        translation_match = re.search(
            r"TRANSLATION:\s*(.*?)(?:\n(?:IS_AD|IS_SYRIA_RELATED)|$)",
            raw_result,
            re.DOTALL,
        )
        if translation_match:
            result["translation"] = translation_match.group(1).strip()
        else:
            result["translation"] = raw_result  # Fallback to entire response

        # Extract if it's an ad
        ad_match = re.search(r"IS_AD:\s*(true|false)", raw_result, re.IGNORECASE)
        result["is_ad"] = ad_match and ad_match.group(1).lower() == "true"

        # Extract if it's Syria-related
        syria_match = re.search(
            r"IS_SYRIA_RELATED:\s*(true|false)", raw_result, re.IGNORECASE
        )
        result["is_syria_related"] = (
            not syria_match or syria_match.group(1).lower() == "true"
        )

        # Clean up the translation further
        result["translation"] = clean_translation(result["translation"])

        if logger:
            logger.debug(f"[AI_UTILS] Parsed result: {result}")

        return result
    except Exception as e:
        if logger:
            logger.error(f"[AI_UTILS] Error calling OpenAI API: {str(e)}")
        return {
            "title": "News Update",
            "translation": f"Translation unavailable: {str(e)}",
        }


def clean_translation(text):
    """
    Clean up translation text:
    - Remove any remaining hashtags
    - Remove any telegram links and subscription messages
    - Remove promotional content
    - Remove phrases like .شبكةاخبارسوريا_الحرة
    """
    # First, handle hashtags - completely remove them
    text = re.sub(r"#\w+", "", text)
    text = re.sub(r"#", "", text)  # Remove any lone # symbols

    # Remove ALL URLs
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(
        r"(?:www|t\.me)\.\S+", "", text
    )  # Catch www and t.me links without http

    # Remove all emoji
    emoji_pattern = re.compile(
        "["
        "\U0001f600-\U0001f64f"  # emoticons
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f680-\U0001f6ff"  # transport & map symbols
        "\U0001f700-\U0001f77f"  # alchemical symbols
        "\U0001f780-\U0001f7ff"  # Geometric Shapes
        "\U0001f800-\U0001f8ff"  # Supplemental Arrows-C
        "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
        "\U0001fa00-\U0001fa6f"  # Chess Symbols
        "\U0001fa70-\U0001faff"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027b0"  # Dingbats
        "\U000024c2-\U0001f251"
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub(r"", text)

    # Remove common promotional phrases - more aggressive list
    promo_phrases = [
        r"(?i)subscribe to our channel",
        r"(?i)follow us on telegram",
        r"(?i)join our channel",
        r"(?i)subscribe to the telegram channel",
        r"(?i)telegram channel",
        r"(?i)urgent service",
        r"(?i)free.*news network",
        r"(?i)news network.*service",
        r"(?i)subscribe",
        r"(?i)follow",
        r"(?i)👇",
        r"(?i)channel.*👇",
        r"(?i)service \|\|",
        r"(?i)urgent",  # Often part of promotional headlines
        r"(?i)🔵",  # Common emoji used in promotions
        r"(?i)free syria news network",
        r"(?i)urgent service",
        r"(?i)for more",
        r"(?i)t\.me",
        r"(?i)telegram",
        r"(?i)our service",
        r"(?i)our network",
        r"(?i)channel",
        r"(?i)bot news",
        r"(?i)news service",
        r"(?i)service$",
        r"(?i)free.*service",
        r"(?i)join",
        r"(?i)شبكة.?اخبار.?سوريا.?_?الحرة",  # Remove .شبكةاخبارسوريا_الحرة and variants
    ]
    for phrase in promo_phrases:
        text = re.sub(phrase, "", text)

    # Remove lines that are too short (likely just promotional leftovers)
    lines = text.split("\n")
    filtered_lines = [line for line in lines if len(line.strip()) > 5]
    text = "\n".join(filtered_lines)

    # Clean up any excess whitespace from removals
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n\s*\n", "\n", text)
    text = text.strip()

    # Remove any remaining promotional phrases that might be at the beginning or end
    text = re.sub(r"^.*(news service|network)\s*[:]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+$", "", text)  # Remove trailing whitespace

    return text
