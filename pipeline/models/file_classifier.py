import logging
from typing import Tuple, Optional

try:
    from transformers import pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("⚠️ Transformers not installed. File classification will use fallback method.")


class FileTypeClassifier:
    """
    AI-powered file type classifier using Hugging Face models.
    Runs 100% locally with zero API costs.
    """
    
    def __init__(self, model_name: str = "facebook/bart-large-mnli"):
        """
        Initialize the classifier with a zero-shot classification model.
        
        Args:
            model_name: Hugging Face model to use. Options:
                - "facebook/bart-large-mnli" (default, ~1.5GB, highly accurate)
                - "MoritzLaurer/deberta-v3-base-zeroshot-v2.0" (lighter, ~300MB)
        """
        self.model_name = model_name
        self.classifier = None
        
        # Document categories for classification
        self.categories = [
            "log file",
            "system log",
            "error log",
            "application log",
            "network log",     # CIDDS/Traffic logs
            "security log",    # IDS/Firewall logs
            "server log",      # Web server logs
            "audit log",       # Database/Compliance logs
            "curriculum vitae",
            "resume",
            "invoice",
            "financial report",
            "technical report",
            "legal contract",
            "agreement",
            "other document"
        ]
        
        if TRANSFORMERS_AVAILABLE:
            self._initialize_model()
        else:
            logging.warning("⚠️ Transformers not available. Using fallback classification.")

    def _initialize_model(self):
        """Load the Hugging Face model for classification."""
        try:
            device = 0 if torch.cuda.is_available() else -1
            device_name = "GPU" if device == 0 else "CPU"
            
            logging.info(f"🤖 Loading file classifier: {self.model_name} on {device_name}...")
            
            self.classifier = pipeline(
                "zero-shot-classification",
                model=self.model_name,
                device=device
            )
            
            logging.info(f"✅ File classifier loaded successfully on {device_name}")
            
        except Exception as e:
            logging.error(f"❌ Failed to load classifier model: {e}")
            logging.warning("   Falling back to extension-based classification")
            self.classifier = None
    
    def classify_file(self, content: str, filename: str = "") -> Tuple[str, float]:
        """
        Classify a file based on its content.
        
        Args:
            content: Text content of the file
            filename: Optional filename for fallback classification
            
        Returns:
            Tuple of (category, confidence_score)
            Category will be normalized for folder naming (e.g., "cv", "resume", "log", etc.)
        """
        # 1. Strong Heuristic Override for .log files
        # If it clearly looks like a log and has .log extension, trust it to save compute/error
        if filename.lower().endswith('.log'):
            # simple check for log keywords to confirm it's not a renamed resume
            log_indicators = ["INFO", "DEBUG", "ERROR", "WARN", "timestamp", "traceback"]
            if any(ind in content for ind in log_indicators):
                logging.info(f"   ⚡ Fast-path: Identified as log based on extension & content")
                return "log", 1.0

        if self.classifier and content:
            return self._classify_with_ai(content)
        else:
            return self._classify_with_fallback(content, filename)
    
    def _classify_with_ai(self, content: str) -> Tuple[str, float]:
        """Use Hugging Face model for classification."""
        try:
            # Use first 2000 characters for classification (enough context, faster inference)
            sample = content[:2000].strip()
            
            if not sample:
                logging.warning("⚠️ Empty content for classification")
                return "other_document", 0.5
            
            # Run zero-shot classification
            result = self.classifier(sample, self.categories)
            
            top_category = result['labels'][0]
            confidence = result['scores'][0]
            
            # Normalize category name for folder creation
            normalized_category = self._normalize_category(top_category)
            
            logging.info(f"   📋 Classified as: {normalized_category} (confidence: {confidence:.2f})")
            
            return normalized_category, confidence
            
        except Exception as e:
            logging.error(f"❌ AI classification failed: {e}")
            return "other_document", 0.0
    
    def _normalize_category(self, category: str) -> str:
        """
        Normalize category names to folder-friendly formats.
        
        Maps AI classifications to standardized folder names:
        - "log file" -> "log"
        - "curriculum vitae" -> "cv"
        - "resume" -> "resume"
        - etc.
        """
        category_lower = category.lower()
        
        # Map specific categories
        if "log" in category_lower:
            return "log"
        elif "curriculum vitae" in category_lower:
            return "cv"
        elif "resume" in category_lower:
            return "resume"
        elif "invoice" in category_lower:
            return "invoice"
        elif "report" in category_lower:
            return "report"
        elif "contract" in category_lower or "agreement" in category_lower:
            return "contract"
        else:
            # Generic: replace spaces with underscores
            return category.replace(" ", "_").lower()

    def _classify_with_fallback(self, content: str, filename: str) -> Tuple[str, float]:
        """
        Fallback classification using heuristics when AI is unavailable.
        Examines file content for keywords.
        """
        content_lower = content[:2000].lower() if content else ""
        
        # Log file indicators (Expanded for CSV/PDF logs)
        log_keywords = [
            "error", "warning", "info", "debug", "exception", "stacktrace", 
            "timestamp", "kernel", "system", "service", 
            "src_ip", "dst_ip", "source ip", "destination ip", "protocol", "packet", # Network logs
            "src ip", "dst ip", "proto", "flags", "duration", "bytes", # Common CIDDS columns
            "user_id", "session_id", "access_log", "auth_failed" # Auth logs
        ]
        
        # CV/Resume indicators
        cv_keywords = ["curriculum vitae", "education", "work experience", "skills", 
                      "professional summary", "employment history", "qualifications"]
        
        resume_keywords = ["resume", "objective", "career summary", "references available"]
        
        # Invoice indicators
        invoice_keywords = ["invoice", "bill", "payment", "amount due", "total", "tax"]
        
        # Count keyword matches
        log_score = sum(1 for kw in log_keywords if kw in content_lower)
        cv_score = sum(1 for kw in cv_keywords if kw in content_lower)
        resume_score = sum(1 for kw in resume_keywords if kw in content_lower)
        invoice_score = sum(1 for kw in invoice_keywords if kw in content_lower)
        
        # Determine category based on highest score
        scores = {
            "log": log_score,
            "cv": cv_score,
            "resume": resume_score,
            "invoice": invoice_score
        }
        
        if max(scores.values()) > 0:
            best_category = max(scores, key=scores.get)
            confidence = min(scores[best_category] / 10.0, 0.9)  # Normalize to 0-0.9
            logging.info(f"   📋 Fallback classified as: {best_category} (confidence: {confidence:.2f})")
            return best_category, confidence
        else:
            # Check file extension as last resort
            if filename:
                ext = filename.split('.')[-1].lower()
                if ext in ['log', 'txt']:
                    return "log", 0.6
            
            return "other_document", 0.5


# Singleton instance for reuse
_classifier_instance: Optional[FileTypeClassifier] = None


def get_classifier() -> FileTypeClassifier:
    """
    Get or create a singleton instance of the FileTypeClassifier.
    This avoids loading the model multiple times.
    """
    global _classifier_instance
    
    if _classifier_instance is None:
        _classifier_instance = FileTypeClassifier()
    
    return _classifier_instance
