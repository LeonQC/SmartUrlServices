import requests
from bs4 import BeautifulSoup

def extract_title(url):
    """Extract title from a webpage URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('title')

        if title_tag:
            return title_tag.text.strip()
        else:
            return None
    except Exception as e:
        # Log error but don't propagate
        print(f"Error extracting title: {e}")
        return None