"""
Local Image Processing Tool for WhatsApp Agent.

This tool provides local-only image understanding capabilities including OCR and
basic vision analysis, strictly adhering to ADR-0019 (no network egress).
"""

import os
import base64
from typing import Dict, Any, Optional, List
from kenny_agent.base_tool import BaseTool


class LocalImageProcessor(BaseTool):
    """Tool for local-only image processing and understanding."""
    
    def __init__(self):
        """Initialize the local image processor."""
        super().__init__(
            name="image_processor",
            description="Local-only image processing with OCR and vision analysis",
            category="image",
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["ocr", "analyze", "extract_text"]},
                    "image_path": {"type": "string"},
                    "image_data": {"type": "string", "description": "Base64 encoded image data"},
                    "options": {
                        "type": "object",
                        "properties": {
                            "language": {"type": "string", "default": "en"},
                            "confidence_threshold": {"type": "number", "default": 0.5}
                        }
                    }
                },
                "required": ["operation"],
                "oneOf": [
                    {"required": ["image_path"]},
                    {"required": ["image_data"]}
                ]
            }
        )
        self._setup_local_models()
    
    def _setup_local_models(self):
        """Initialize local OCR and vision models."""
        try:
            # Try to import pytesseract for OCR (local-only)
            import pytesseract
            self.tesseract_available = True
            print("[image_processor] Tesseract OCR available")
        except ImportError:
            self.tesseract_available = False
            print("[image_processor] Tesseract OCR not available - install with: brew install tesseract")
        
        try:
            # Try to import PIL for basic image processing
            from PIL import Image
            self.pil_available = True
            print("[image_processor] PIL available for image processing")
        except ImportError:
            self.pil_available = False
            print("[image_processor] PIL not available - install with: pip install Pillow")
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute image processing operation.
        
        Args:
            parameters: Operation parameters
            
        Returns:
            Result of the image processing operation
        """
        operation = parameters.get("operation")
        
        if operation == "ocr" or operation == "extract_text":
            return self._extract_text(parameters)
        elif operation == "analyze":
            return self._analyze_image(parameters)
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    def _extract_text(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Extract text from image using local OCR."""
        if not self.tesseract_available or not self.pil_available:
            return {
                "operation": "ocr",
                "text": "",
                "confidence": 0.0,
                "error": "OCR dependencies not available (tesseract, PIL)",
                "mock": True
            }
        
        try:
            import pytesseract
            from PIL import Image
            
            # Get image
            image = self._load_image(parameters)
            if not image:
                return {
                    "operation": "ocr",
                    "text": "",
                    "confidence": 0.0,
                    "error": "Could not load image"
                }
            
            # Extract options
            options = parameters.get("options", {})
            language = options.get("language", "en")
            
            # Perform OCR
            custom_config = f'--oem 3 --psm 6 -l {language}'
            extracted_text = pytesseract.image_to_string(image, config=custom_config)
            
            # Get confidence scores
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "operation": "ocr",
                "text": extracted_text.strip(),
                "confidence": avg_confidence / 100.0,  # Convert to 0-1 scale
                "language": language,
                "word_count": len(extracted_text.split()),
                "local_only": True  # Confirm no network used
            }
            
        except Exception as e:
            print(f"[image_processor] OCR error: {e}")
            return {
                "operation": "ocr",
                "text": "Mock OCR text: This is simulated text extraction from image",
                "confidence": 0.8,
                "error": str(e),
                "mock": True
            }
    
    def _analyze_image(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze image for basic properties and content."""
        if not self.pil_available:
            return {
                "operation": "analyze",
                "properties": {},
                "error": "PIL not available for image analysis",
                "mock": True
            }
        
        try:
            from PIL import Image
            
            # Get image
            image = self._load_image(parameters)
            if not image:
                return {
                    "operation": "analyze",
                    "properties": {},
                    "error": "Could not load image"
                }
            
            # Extract basic properties
            properties = {
                "format": image.format,
                "mode": image.mode,
                "size": image.size,
                "width": image.width,
                "height": image.height,
                "has_transparency": image.mode in ("RGBA", "LA") or "transparency" in image.info,
                "local_only": True  # Confirm no network used
            }
            
            # Basic content analysis (no AI models, just heuristics)
            content_hints = []
            
            # Check if image is very wide/tall (might be screenshot)
            aspect_ratio = image.width / image.height
            if aspect_ratio > 2 or aspect_ratio < 0.5:
                content_hints.append("screenshot_or_document")
            
            # Check for predominantly text-like characteristics
            # (This is a simple heuristic - real implementation would use local ML models)
            if image.mode in ("L", "1"):  # Grayscale or black/white
                content_hints.append("text_document")
            
            properties["content_hints"] = content_hints
            
            return {
                "operation": "analyze",
                "properties": properties,
                "local_only": True
            }
            
        except Exception as e:
            print(f"[image_processor] Analysis error: {e}")
            return {
                "operation": "analyze",
                "properties": {
                    "mock": True,
                    "format": "unknown",
                    "size": [800, 600],
                    "content_hints": ["mock_image"]
                },
                "error": str(e)
            }
    
    def _load_image(self, parameters: Dict[str, Any]):
        """Load image from path or base64 data."""
        try:
            from PIL import Image
            import io
            
            if "image_path" in parameters:
                image_path = parameters["image_path"]
                if os.path.exists(image_path):
                    return Image.open(image_path)
                else:
                    print(f"[image_processor] Image path not found: {image_path}")
                    return None
            
            elif "image_data" in parameters:
                # Decode base64 image data
                image_data = parameters["image_data"]
                if image_data.startswith("data:image"):
                    # Strip data URL prefix
                    image_data = image_data.split(",", 1)[1]
                
                image_bytes = base64.b64decode(image_data)
                return Image.open(io.BytesIO(image_bytes))
            
            return None
            
        except Exception as e:
            print(f"[image_processor] Failed to load image: {e}")
            return None