"""网页自动化工具 - 浏览器操作"""
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def browse_website(
    url: str,
    action: str = "visit",
    selector: str = None,
    text: str = None,
    wait_time: int = 3,
    screenshot_path: str = None
) -> Dict[str, Any]:
    """Automate browser actions.
    
    Args:
        url: Website URL
        action: Action to perform (visit, click, type, extract, screenshot, scroll)
        selector: CSS selector for element
        text: Text to type (for type action)
        wait_time: Time to wait after action (seconds)
        screenshot_path: Path to save screenshot
    
    Returns:
        {
            "success": bool,
            "result": str or dict,
            "error": str (if failed)
        }
    """
    try:
        # Try selenium
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options
            
            # Setup Chrome
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            
            driver = webdriver.Chrome(options=options)
            
            try:
                driver.get(url)
                
                if action == "visit":
                    time.sleep(wait_time)
                    result = {
                        "title": driver.title,
                        "url": driver.current_url,
                    }
                
                elif action == "click":
                    if not selector:
                        return {"success": False, "error": "Missing selector for click action"}
                    
                    element = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    element.click()
                    time.sleep(wait_time)
                    result = {"clicked": True}
                
                elif action == "type":
                    if not selector or not text:
                        return {"success": False, "error": "Missing selector or text for type action"}
                    
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    element.clear()
                    element.send_keys(text)
                    time.sleep(0.5)
                    result = {"typed": text}
                
                elif action == "extract":
                    time.sleep(wait_time)
                    
                    if selector:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        result = [el.text for el in elements]
                    else:
                        # Extract all text
                        result = driver.find_element(By.TAG_NAME, "body").text
                
                elif action == "screenshot":
                    time.sleep(wait_time)
                    
                    if not screenshot_path:
                        screenshot_path = f"E:/AgentProject/data/screenshots/screenshot_{int(time.time())}.png"
                    
                    Path(screenshot_path).parent.mkdir(parents=True, exist_ok=True)
                    driver.save_screenshot(screenshot_path)
                    result = {"screenshot": screenshot_path}
                
                elif action == "scroll":
                    driver.execute_script(f"window.scrollBy(0, {text or 500})")
                    time.sleep(wait_time)
                    result = {"scrolled": text or 500}
                
                else:
                    result = {"warning": f"Unknown action: {action}"}
                
                return {
                    "success": True,
                    "result": result,
                }
                
            finally:
                driver.quit()
        
        except ImportError:
            pass
        
        # Fallback: requests for simple extraction
        if action == "extract":
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove script and style
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text(separator="\n", strip=True)
            
            return {
                "success": True,
                "result": text[:5000],  # Limit output
                "method": "requests",
            }
        
        return {
            "success": False,
            "error": "Selenium not available. Install: pip install selenium",
        }
        
    except Exception as e:
        logger.error(f"Browser automation failed: {e}")
        return {"success": False, "error": str(e)}


def fill_form(
    url: str,
    form_data: Dict[str, str],
    submit_selector: str = None
) -> Dict[str, Any]:
    """Fill and submit a form.
    
    Args:
        url: Form page URL
        form_data: Dict mapping CSS selectors to values
        submit_selector: CSS selector for submit button
    
    Returns:
        {
            "success": bool,
            "result": str,
            "error": str (if failed)
        }
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        
        driver = webdriver.Chrome(options=options)
        
        try:
            driver.get(url)
            time.sleep(2)
            
            # Fill each field
            for selector, value in form_data.items():
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    element.clear()
                    element.send_keys(value)
                except Exception as e:
                    logger.warning(f"Failed to fill {selector}: {e}")
            
            # Submit
            if submit_selector:
                submit_btn = driver.find_element(By.CSS_SELECTOR, submit_selector)
                submit_btn.click()
                time.sleep(2)
            
            return {
                "success": True,
                "result": {
                    "title": driver.title,
                    "url": driver.current_url,
                }
            }
        
        finally:
            driver.quit()
    
    except ImportError:
        return {
            "success": False,
            "error": "Selenium required. Install: pip install selenium",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def scrape_multiple_pages(
    base_url: str,
    selectors: List[str],
    pagination_selector: str = None,
    max_pages: int = 5
) -> Dict[str, Any]:
    """Scrape multiple pages.
    
    Args:
        base_url: Starting URL
        selectors: List of CSS selectors to extract
        pagination_selector: CSS selector for next page button
        max_pages: Maximum pages to scrape
    
    Returns:
        {
            "success": bool,
            "results": list,
            "error": str (if failed)
        }
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument("--headless")
        
        driver = webdriver.Chrome(options=options)
        results = []
        
        try:
            driver.get(base_url)
            
            for page in range(max_pages):
                time.sleep(2)
                
                page_data = {}
                for selector in selectors:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    page_data[selector] = [el.text for el in elements]
                
                results.append(page_data)
                
                # Go to next page
                if pagination_selector and page < max_pages - 1:
                    try:
                        next_btn = driver.find_element(By.CSS_SELECTOR, pagination_selector)
                        next_btn.click()
                    except:
                        break
            
            return {
                "success": True,
                "results": results,
                "pages_scraped": len(results),
            }
        
        finally:
            driver.quit()
    
    except ImportError:
        return {
            "success": False,
            "error": "Selenium required. Install: pip install selenium",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def download_file(
    url: str,
    output_path: str = None,
    headers: Dict[str, str] = None
) -> Dict[str, Any]:
    """Download file from URL.
    
    Args:
        url: File URL
        output_path: Local path to save (default: temp file)
        headers: Optional headers
    
    Returns:
        {
            "success": bool,
            "path": str,
            "size": int,
            "error": str (if failed)
        }
    """
    try:
        import requests
        
        if not output_path:
            from urllib.parse import urlparse
            filename = Path(urlparse(url).path).name or "download"
            output_path = f"E:/AgentProject/data/downloads/{filename}"
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return {
            "success": True,
            "path": output_path,
            "size": Path(output_path).stat().st_size,
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}
