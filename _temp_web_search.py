import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import time
from functools import lru_cache

# 🔧 搜索缓存：相同查询5分钟内返回缓存
@lru_cache(maxsize=100)
def _cached_search(query: str, cache_timestamp: int) -> tuple:
    """Internal cached search. cache_timestamp ensures 5-min TTL."""
    return _do_search(query)


def _do_search(query: str, num_results: int = 5) -> list:
    """Actual search implementation."""
    results = []
    
    # 方法1: DuckDuckGo HTML
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for result in soup.select(".result"):
            title_el = result.select_one(".result__title a")
            snippet_el = result.select_one(".result__snippet")
            href_el = result.select_one(".result__url")

            if title_el:
                results.append({
                    "title": title_el.get_text(strip=True),
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    "url": href_el.get_text(strip=True) if href_el else "",
                })
                if len(results) >= num_results:
                    break
        
        if results:
            return results
    except Exception:
        pass  # fallback to method 2
    
    # 方法2: Bing搜索API (免费tier，需要API key，这里用HTML抓取备选)
    try:
        url = f"https://www.bing.com/search?q={quote(query)}&count={num_results}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        for item in soup.select(".b_algo"):
            title_el = item.select_one("h2 a")
            snippet_el = item.select_one(".b_caption p")
            if title_el:
                results.append({
                    "title": title_el.get_text(strip=True),
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    "url": title_el.get("href", ""),
                })
                if len(results) >= num_results:
                    break
    except Exception as e:
        if not results:
            results.append({"title": "Search Error", "snippet": str(e), "url": ""})
    
    return results


def search_web(query: str, num_results: int = 5) -> list:
    """Web search with 5-minute cache."""
    cache_timestamp = int(time.time() / 300)  # 5分钟一个时间片
    return list(_cached_search(query, cache_timestamp))


def fetch_url(url: str, max_chars: int = 5000) -> str:
    """Fetch and extract text content from a URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove scripts and styles
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        return text[:max_chars]
    except Exception as e:
        return f"Failed to fetch URL: {e}"
