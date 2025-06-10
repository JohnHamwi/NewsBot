import re
import pytest

# Example text cleaning function (replace with actual import if exists)
def clean_text(text):
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove hashtags
    text = re.sub(r'#\w[\w\d_\u0600-\u06FF]*', '', text, flags=re.UNICODE)
    return text.strip()

def test_clean_text_removes_urls_and_hashtags():
    raw = 'Check this out! https://example.com #BreakingNews #أخبار'
    cleaned = clean_text(raw)
    assert 'http' not in cleaned
    assert '#' not in cleaned
    assert 'BreakingNews' not in cleaned
    assert 'أخبار' not in cleaned 