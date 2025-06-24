# =============================================================================
# NewsBot AI Utilities Module
# =============================================================================
# This module provides AI-powered functionality for the bot, including
# text cleaning and formatting, translation and summarization services,
# ad detection, and OpenAI API integration for news processing.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import re

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import openai

# =============================================================================
# Local Application Imports
# =============================================================================
from src.core.unified_config import unified_config as config


# =============================================================================
# Text Cleaning Functions
# =============================================================================
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


# =============================================================================
# OpenAI API Integration Functions
# =============================================================================
def call_chatgpt_for_news(arabic_text, openai, logger=None):
    """
    Call ChatGPT API to translate Arabic news, create a title, detect location, ads, and content relevance.
    
    Args:
        arabic_text: The Arabic text to process
        openai: OpenAI client instance
        logger: Optional logger for debugging
        
    Returns:
        Dict containing translation, title, location, and analysis results
    """
    if logger:
        logger.info("[AI_UTILS] Calling ChatGPT for translation/title/location...")
        logger.debug(f"[AI_UTILS] Input: {arabic_text[:100]}...")

    # Use the provided openai client directly instead of creating a new instance
    client = openai  # Don't try to create a new client with openai.OpenAI()

    # Define the enhanced prompt template with location detection
    PROMPT_TEMPLATE = """
    You're a translator and news analyst specializing in converting Arabic news to English and extracting key information.

    TRANSLATION INSTRUCTIONS:
    1. REMOVE ALL hashtags completely (e.g., #Syria becomes Syria)
    2. REMOVE ALL Telegram links, URLs, and channel mentions
    3. REMOVE ALL promotional content (subscribe/follow messages)
    4. REMOVE ALL emojis
    5. REMOVE ALL social media tags like "X | FB | IG | Boost", "Twitter", "Facebook", "Instagram", etc.
    6. REMOVE ALL platform references and sharing prompts
    7. Focus ONLY on the actual news content
    8. CRITICAL: Provide a COMPLETE, WORD-FOR-WORD translation - DO NOT SUMMARIZE OR SHORTEN
    9. Keep ALL factual information, ALL details, ALL sentences - translate EVERYTHING
    10. NEVER include original hashtags in your output
    11. NEVER include any telegram links in your output
    12. NEVER include anything about following or subscribing
    13. NEVER include social media platform names or sharing tags
    14. ABSOLUTELY DO NOT SUMMARIZE - Translate every single sentence and detail completely
    15. If the original has 3 sentences, your translation must have 3 sentences
    16. If the original has specific details like names, places, quotes - include ALL of them
    17. Your job is TRANSLATION, not summarization - translate the ENTIRE text literally
    18. MANDATORY: Every paragraph in Arabic must become a paragraph in English
    19. MANDATORY: Every sentence in Arabic must become a sentence in English
    20. FORBIDDEN: Condensing multiple sentences into one sentence
    21. FORBIDDEN: Omitting any factual details, names, locations, or quotes
    22. FORBIDDEN: Creating shorter versions or summaries of the original text

    TITLE INSTRUCTIONS - CRITICAL:
    - Create a concise Arabic title in EXACTLY 3-6 words (NO MORE, NO LESS)
    - The title should be in ARABIC only, not English
    - MANDATORY: Count the words - must be between 3-6 words only
    - Examples: "انفجار في دمشق" (3 words), "قصف على حلب" (3 words), "اشتباكات في إدلب" (3 words), "عاجل من سوريا" (3 words)
    - FORBIDDEN: Titles longer than 6 words or shorter than 3 words
    - Use active voice and present tense when possible
    - Make it sound like a proper Arabic news headline
    - DOUBLE-CHECK: Count your words before submitting the title

    LOCATION DETECTION INSTRUCTIONS - CRITICAL:
    - ALWAYS analyze the ENTIRE text to find the PRIMARY geographic location of the news event
    - Look for country names, city names, governorates, and geographic references in the text
    - MANDATORY: Pay special attention to Syrian cities and locations:
      * دمشق/الشام = Damascus, Syria
      * حلب = Aleppo, Syria  
      * حمص = Homs, Syria
      * حماة = Hama, Syria (IMPORTANT: محافظة حماة = Hama, Syria)
      * اللاذقية = Latakia, Syria
      * طرطوس = Tartus, Syria
      * درعا = Daraa, Syria
      * إدلب = Idlib, Syria
      * الرقة = Raqqa, Syria
      * دير الزور = Deir ez-Zor, Syria
      * الحسكة = Hasakah, Syria
      * القامشلي = Qamishli, Syria
    - CRITICAL: Look for governorate mentions: محافظة حماة = Hama, Syria, محافظة دمشق = Damascus, Syria, etc.
    - Look for Arabic prepositions that indicate location: بـ (in), في (in), من (from), إلى (to), بمحافظة (in the governorate of)
    - Examples: "بدمشق" = "Damascus, Syria", "في حلب" = "Aleppo, Syria", "بمحافظة حماة" = "Hama, Syria"
    - IMPORTANT: الدويلعة/دويلعة (Doueila) = "Damascus, Syria" (it's a district in Damascus)
    - ALWAYS format Syrian cities as "City, Syria" (e.g., "Damascus, Syria", "Aleppo, Syria", "Hama, Syria")
    - For other Middle Eastern locations: Iran, Iraq, Lebanon, Turkey, Jordan, Israel, Palestine, Saudi Arabia, Egypt, etc.
    - If multiple locations are mentioned, choose the PRIMARY location where the main event occurred
    - IMPORTANT: If the text mentions "في سوريا وآخر في لبنان" (one in Syria and another in Lebanon), choose the SPECIFIC location mentioned, not just "Syria"
    - Example: "واحد في سوريا وآخر في لبنان" = Primary location is "Lebanon" (the more specific/recent event)
    - If no clear location is mentioned, use "Unknown"
    - Use proper English names with country specification
    - NEVER just say "Syria" if a specific city is mentioned - always include the city name
    - NEVER default to "Syria" when other countries are specifically mentioned

    TRANSLATION EXAMPLE:
    Original Arabic: "هجوم على كنيسة مار إلياس وترك رسائل طائفية
    قامت مجموعة مسلحة بالهجوم على كنيسة مار إلياس في بلدة كفربو (كفربهم) بمحافظة حماة، في حادثة صادمة أثارت الخوف في نفوس السكان. وأفاد السكان المحليون بأن المهاجمين شوّهوا جدران الكنيسة بكتابات تهديدية، من بينها عبارة: 'دوركم قادم'.
    الهجوم ترك المجتمع في حالة من الذهول، وسلّط الضوء على تدهور الوضع الأمني وتصاعد المخاوف من الترهيب الطائفي.
    X | FB | IG |Boost"
    
    - WRONG (summarized): "An attack on Mar Elias Church left sectarian messages"
    - WRONG (wrong location): Location should be "Syria" 
    - CORRECT (complete, clean): "Attack on Mar Elias Church and sectarian messages left. An armed group attacked the Mar Elias Church in the town of Kafarbo (Kafarbahm) in Hama Governorate, in a shocking incident that sparked fear among residents. Local residents reported that the attackers defaced the church walls with threatening writings, including the phrase: 'Your turn is coming.' The attack left the community in a state of shock and highlighted the deteriorating security situation and escalating fears of sectarian intimidation."
    - CORRECT (location): Location should be "Hama, Syria" (because text mentions "بمحافظة حماة")

    Format your response EXACTLY as follows:

    TITLE: [concise Arabic title in 3-6 words describing the main event]
    TRANSLATION: [full, literal English translation with NO hashtags, links, or promotional content - COMPLETE, NOT SUMMARIZED]
    LOCATION: [primary country/location where the event occurred]
    IS_AD: [true/false]
    IS_SYRIA_RELATED: [true/false]
    """

    # Create the complete prompt with the input text
    prompt = f"{PROMPT_TEMPLATE}\n\nArabic text:\n{arabic_text}"

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful translator and news analyst."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1200,  # Increased for the additional location field
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
            title = title_match.group(1).strip()
            # ENFORCE 4-6 WORDS LIMIT: Split title and limit to maximum 6 words
            title_words = title.split()
            if len(title_words) > 6:
                title = " ".join(title_words[:6])
                if logger:
                    logger.warning(f"[AI_UTILS] Title too long ({len(title_words)} words), truncated to: {title}")
            elif len(title_words) < 3:
                # If too short, pad with generic words if needed
                if len(title_words) == 0:
                    title = "أخبار سورية"
                elif len(title_words) == 1:
                    title = f"عاجل {title}"
                elif len(title_words) == 2:
                    title = f"{title} اليوم"
            result["title"] = title
        else:
            result["title"] = "أخبار سورية"

        # Extract translation
        translation_match = re.search(
            r"TRANSLATION:\s*(.*?)(?:\n(?:LOCATION|IS_AD|IS_SYRIA_RELATED)|$)",
            raw_result,
            re.DOTALL,
        )
        if translation_match:
            result["translation"] = translation_match.group(1).strip()
        else:
            result["translation"] = raw_result  # Fallback to entire response

        # Extract location
        location_match = re.search(r"LOCATION:\s*(.*?)(?:\n|$)", raw_result)
        if location_match:
            location = location_match.group(1).strip()
            # Clean up the location and validate it
            location = location.replace('"', '').replace("'", "")
            if location.lower() in ['unknown', 'unclear', 'not specified', 'n/a', 'none']:
                result["location"] = "Unknown"
            else:
                result["location"] = location.title()  # Capitalize properly
        else:
            result["location"] = "Unknown"

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
            logger.debug(f"[AI_UTILS] Parsed result with location: {result}")

        return result
        
    except Exception as e:
        if logger:
            logger.error(f"[AI_UTILS] Error calling OpenAI API: {str(e)}")
        return {
            "title": "أخبار سورية",
            "translation": f"Translation unavailable: {str(e)}",
            "location": "Unknown",
        }


async def get_openai_response(prompt: str, max_tokens: int = 200, temperature: float = 0.3) -> str:
    """
    Get response from OpenAI API for general prompts.
    
    Args:
        prompt: The prompt to send to OpenAI
        max_tokens: Maximum tokens in response
        temperature: Temperature for response creativity
        
    Returns:
        Response string from OpenAI, or None if failed
    """
    try:
        # Get API key from config
        api_key = config.get("openai.api_key")
        if not api_key:
            return None
            
        # Create async client
        client = openai.AsyncOpenAI(api_key=api_key)
        
        # Make API call
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant for news analysis."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        # Log error but don't raise to avoid breaking the caller
        print(f"OpenAI API error: {e}")
        return None


# =============================================================================
# Translation Cleaning Functions
# =============================================================================
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

    # Remove social media platform tags first
    social_media_patterns = [
        r"(?i)X\s*\|\s*FB\s*\|\s*IG\s*\|\s*Boost",
        r"(?i)X\s*\|\s*FB\s*\|\s*IG",
        r"(?i)Twitter\s*\|\s*Facebook\s*\|\s*Instagram",
        r"(?i)FB\s*\|\s*IG\s*\|\s*X",
        r"(?i)\bX\b\s*\|\s*\bFB\b",
        r"(?i)\bIG\b\s*\|\s*\bBoost\b",
        r"(?i)Share:\s*\w+",
        r"(?i)Follow:\s*\w+",
        r"(?i)Like\s*\|\s*Share\s*\|\s*Subscribe",
    ]
    for pattern in social_media_patterns:
        text = re.sub(pattern, "", text)

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
