"""图像分析工具 - 多模态理解"""
import base64
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def analyze_image(
    image_path: str,
    question: str = "Describe this image in detail",
    model: str = None
) -> Dict[str, Any]:
    """Analyze image using vision-capable LLM.
    
    Args:
        image_path: Path to image file (jpg, png, gif, webp)
        question: Question to ask about the image
        model: Vision model to use (auto-selected if None)
    
    Returns:
        {
            "success": bool,
            "description": str,
            "error": str (if failed)
        }
    """
    try:
        path = Path(image_path)
        if not path.exists():
            return {"success": False, "error": f"Image not found: {image_path}"}
        
        # Read and encode image
        with open(path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        # Detect image type
        suffix = path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_types.get(suffix, "image/jpeg")
        
        # Use vision-capable model
        from app.llm_client import get_llm_client
        from app.config import NVIDIA_API_KEY, NVIDIA_BASE_URL
        
        client = get_llm_client()
        
        # Try vision models (NVIDIA NIM supports some)
        vision_models = [
            "nvidia/llama-3.2-11b-vision-instruct",
            "microsoft/phi-3-vision-128k-instruct",
        ]
        
        model_to_use = model or vision_models[0]
        
        # Build message with image
        response = client.chat.completions.create(
            model=model_to_use,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000,
        )
        
        description = response.choices[0].message.content
        
        return {
            "success": True,
            "description": description,
            "model": model_to_use,
        }
        
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "description": None,
        }


def extract_text_from_image(image_path: str) -> Dict[str, Any]:
    """Extract text from image using OCR.
    
    Args:
        image_path: Path to image file
    
    Returns:
        {
            "success": bool,
            "text": str,
            "error": str (if failed)
        }
    """
    try:
        # Try pytesseract (Tesseract OCR)
        try:
            import pytesseract
            from PIL import Image
            
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img, lang='chi_sim+eng')
            
            return {
                "success": True,
                "text": text.strip(),
                "method": "tesseract",
            }
        except ImportError:
            pass
        
        # Try easyocr as fallback
        try:
            import easyocr
            reader = easyocr.Reader(['ch_sim', 'en'])
            results = reader.readtext(image_path)
            text = "\n".join([r[1] for r in results])
            
            return {
                "success": True,
                "text": text,
                "method": "easyocr",
            }
        except ImportError:
            pass
        
        # Fallback to vision model
        return analyze_image(
            image_path,
            question="Extract all text from this image. Output only the text content.",
        )
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "text": None,
        }


def compare_images(image_path1: str, image_path2: str, question: str = None) -> Dict[str, Any]:
    """Compare two images.
    
    Args:
        image_path1: Path to first image
        image_path2: Path to second image
        question: Specific comparison question
    
    Returns:
        {
            "success": bool,
            "comparison": str,
            "error": str (if failed)
        }
    """
    try:
        # Analyze both images
        desc1 = analyze_image(image_path1, "Describe this image concisely")
        desc2 = analyze_image(image_path2, "Describe this image concisely")
        
        if not desc1["success"] or not desc2["success"]:
            return {
                "success": False,
                "error": f"Failed to analyze images: {desc1.get('error')} {desc2.get('error')}",
            }
        
        # Use LLM to compare
        from app.llm_client import chat_completion
        
        prompt = f"""Compare these two images:

Image 1: {desc1['description']}

Image 2: {desc2['description']}

{question or "What are the similarities and differences?"}
"""
        
        response = chat_completion([
            {"role": "user", "content": prompt}
        ])
        
        comparison = response.choices[0].message.content
        
        return {
            "success": True,
            "comparison": comparison,
            "image1_description": desc1["description"],
            "image2_description": desc2["description"],
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def detect_objects(image_path: str) -> Dict[str, Any]:
    """Detect objects in image (basic implementation).
    
    Args:
        image_path: Path to image
    
    Returns:
        {
            "success": bool,
            "objects": list,
            "error": str (if failed)
        }
    """
    result = analyze_image(
        image_path,
        question="List all objects you can see in this image. Format as a JSON array of object names."
    )
    
    if not result["success"]:
        return result
    
    # Try to parse as JSON
    import json
    import re
    
    try:
        # Extract JSON array from response
        match = re.search(r'\[.*?\]', result["description"], re.DOTALL)
        if match:
            objects = json.loads(match.group())
        else:
            # Fallback to line-by-line
            objects = [line.strip() for line in result["description"].split("\n") if line.strip()]
        
        return {
            "success": True,
            "objects": objects,
            "raw_description": result["description"],
        }
    except:
        return {
            "success": True,
            "objects": [],
            "raw_description": result["description"],
        }
