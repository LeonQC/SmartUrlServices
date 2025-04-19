from pydantic import BaseModel, HttpUrl

class URLRequest(BaseModel):
    """What users send when creating a short URL"""
    target_url: HttpUrl  # This ensures we only accept valid URLs

class URLResponse(BaseModel):
    """What we send back to users"""
    original_url: str    # The original long URL
    short_code: str      # The random code (like abc123)
    short_url: str       # The complete short URL
    title: str = None  # The title of the webpage (optional)
    clicks: int          # How many times it's been used