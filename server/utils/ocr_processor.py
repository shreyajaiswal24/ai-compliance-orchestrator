from PIL import Image
import pytesseract
import cv2
import numpy as np
from typing import Dict, List, Any, Optional
import os
import base64
import io

class OCRProcessor:
    """Handles OCR extraction from images with preprocessing"""
    
    def __init__(self):
        # Configure tesseract path if needed
        # pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'  # Linux
        self.supported_formats = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']
        
    def extract_text_from_image(self, image_path: str) -> Dict[str, Any]:
        """Extract text from image file"""
        try:
            if not os.path.exists(image_path):
                return {
                    "success": False,
                    "error": f"Image file not found: {image_path}",
                    "extracted_text": "",
                    "confidence": 0.0
                }
            
            # Check file format
            file_ext = os.path.splitext(image_path)[1].lower()
            if file_ext not in self.supported_formats:
                return {
                    "success": False,
                    "error": f"Unsupported image format: {file_ext}",
                    "extracted_text": "",
                    "confidence": 0.0
                }
            
            # Load and preprocess image
            image = Image.open(image_path)
            processed_image = self._preprocess_image(image)
            
            # Extract text with confidence scores
            data = pytesseract.image_to_data(processed_image, output_type=pytesseract.Output.DICT)
            
            # Filter out low confidence text
            filtered_text = []
            confidences = []
            
            for i, text in enumerate(data['text']):
                confidence = int(data['conf'][i])
                if confidence > 30 and text.strip():  # Filter low confidence
                    filtered_text.append(text.strip())
                    confidences.append(confidence)
            
            extracted_text = ' '.join(filtered_text)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Detect compliance-related elements
            detected_elements = self._detect_compliance_elements(extracted_text)
            
            return {
                "success": True,
                "error": None,
                "extracted_text": extracted_text,
                "confidence": avg_confidence / 100.0,  # Normalize to 0-1
                "detected_elements": detected_elements,
                "word_count": len(filtered_text),
                "image_path": image_path
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"OCR processing failed: {str(e)}",
                "extracted_text": "",
                "confidence": 0.0
            }
    
    def extract_text_from_base64(self, base64_data: str) -> Dict[str, Any]:
        """Extract text from base64 encoded image"""
        try:
            # Decode base64 to image
            image_data = base64.b64decode(base64_data)
            image = Image.open(io.BytesIO(image_data))
            
            # Process image
            processed_image = self._preprocess_image(image)
            
            # Extract text
            data = pytesseract.image_to_data(processed_image, output_type=pytesseract.Output.DICT)
            
            filtered_text = []
            confidences = []
            
            for i, text in enumerate(data['text']):
                confidence = int(data['conf'][i])
                if confidence > 30 and text.strip():
                    filtered_text.append(text.strip())
                    confidences.append(confidence)
            
            extracted_text = ' '.join(filtered_text)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            detected_elements = self._detect_compliance_elements(extracted_text)
            
            return {
                "success": True,
                "error": None, 
                "extracted_text": extracted_text,
                "confidence": avg_confidence / 100.0,
                "detected_elements": detected_elements,
                "word_count": len(filtered_text)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Base64 OCR processing failed: {str(e)}",
                "extracted_text": "",
                "confidence": 0.0
            }
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image to improve OCR accuracy"""
        try:
            # Convert PIL to OpenCV format
            open_cv_image = np.array(image)
            if len(open_cv_image.shape) == 3:
                open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            if len(open_cv_image.shape) == 3:
                gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = open_cv_image
            
            # Apply image preprocessing techniques
            # 1. Noise reduction
            denoised = cv2.medianBlur(gray, 3)
            
            # 2. Threshold to get better contrast
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 3. Morphological operations to clean up
            kernel = np.ones((1, 1), np.uint8)
            processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            # Convert back to PIL
            processed_image = Image.fromarray(processed)
            
            return processed_image
            
        except Exception:
            # If preprocessing fails, return original image
            return image
    
    def _detect_compliance_elements(self, text: str) -> List[str]:
        """Detect compliance-related UI elements in extracted text"""
        text_lower = text.lower()
        
        detected_elements = []
        
        # Authentication elements
        auth_keywords = [
            'multi-factor', 'mfa', 'two-factor', '2fa', 'authentication',
            'login', 'password', 'username', 'sign in', 'otp', 'token',
            'biometric', 'fingerprint', 'face id'
        ]
        
        for keyword in auth_keywords:
            if keyword in text_lower:
                detected_elements.append(f"auth_{keyword.replace(' ', '_').replace('-', '_')}")
        
        # Settings/Configuration elements
        settings_keywords = [
            'settings', 'configuration', 'preferences', 'options',
            'security', 'privacy', 'account', 'profile'
        ]
        
        for keyword in settings_keywords:
            if keyword in text_lower:
                detected_elements.append(f"settings_{keyword}")
        
        # UI Controls
        control_keywords = [
            'enable', 'disable', 'toggle', 'switch', 'checkbox',
            'button', 'dropdown', 'select', 'input', 'field'
        ]
        
        for keyword in control_keywords:
            if keyword in text_lower:
                detected_elements.append(f"control_{keyword}")
        
        # Compliance indicators
        compliance_keywords = [
            'required', 'mandatory', 'optional', 'recommended',
            'compliant', 'non-compliant', 'violation', 'policy'
        ]
        
        for keyword in compliance_keywords:
            if keyword in text_lower:
                detected_elements.append(f"compliance_{keyword}")
        
        return list(set(detected_elements))  # Remove duplicates
    
    def batch_process_images(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """Process multiple images in batch"""
        results = []
        
        for image_path in image_paths:
            result = self.extract_text_from_image(image_path)
            result['image_path'] = image_path
            results.append(result)
        
        return results
    
    def get_mock_ocr_result(self, image_path: str) -> Dict[str, Any]:
        """Generate mock OCR result for demo purposes"""
        mock_texts = [
            "Multi-Factor Authentication Settings: SMS verification enabled, TOTP disabled, Backup codes generated",
            "Security Settings: Session timeout: 30 minutes, Auto-lock enabled, Password complexity: High",
            "User Access Control: Admin privileges required, MFA mandatory for admin functions",
            "Compliance Dashboard: Policy violations: 0, Last audit: 2024-01-15, Status: Compliant"
        ]
        
        import random
        mock_text = random.choice(mock_texts)
        
        return {
            "success": True,
            "error": None,
            "extracted_text": mock_text,
            "confidence": 0.94,
            "detected_elements": ["settings_security", "auth_multi_factor", "compliance_compliant"],
            "word_count": len(mock_text.split()),
            "image_path": image_path
        }

# Global instance
ocr_processor = OCRProcessor()