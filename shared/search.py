import os, sys, requests, re
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from .agents import AGENTS


# Build a personality-biased search query for each agent
def build_search_query(agent_id: str, topic: str) -> str:
    bias = AGENTS[agent_id]["search_bias"].replace("{topic}", topic)
    return bias


# Search using SerpApi, return title + snippet + link
def search_web(query: str, n_results: int = 5) -> list[dict]:
    SERP_KEY = os.environ.get("SERP_API_KEY")
    if not SERP_KEY:
        print(f"  ⚠️  No SERP key — mocking results for: {query}")
        return [{"title": "Mock result", "snippet": f"Mock content about {query}", "link": ""}]
    
    response = requests.get("https://serpapi.com/search", params={
        "q": query,
        "api_key": SERP_KEY,
        "num": n_results
    })
    data = response.json()
    return [
        {
            "title": r.get("title", ""),
            "snippet": r.get("snippet", ""),
            "link": r.get("link", "")
        }
        for r in data.get("organic_results", [])[:n_results]
    ]


# Fetch and truncate a URL's text content
def fetch_url_content(url: str, max_chars: int = 5000) -> str:
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        text = response.text
        
        # Remove script and style blocks entirely (catches JSON-LD)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        
        # Strip remaining HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Filter out lines that look like JSON or code
        lines = [l for l in text.split('.')
                 if len(l.strip()) > 30
                 and '{' not in l
                 and '@' not in l]
        
        return '. '.join(lines)[:max_chars]
    except Exception as e:
        print(f"  fetch failed for {url}: {e}")
        return ""