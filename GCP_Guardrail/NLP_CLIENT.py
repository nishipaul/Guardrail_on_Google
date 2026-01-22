from google.oauth2 import service_account
from google.cloud import language_v1
from typing import Dict, Any, Optional, List, Union
from ENUM_CLASSES import (
    ModerationCategory, EntityType,
    parse_entity_types, parse_moderation_categories, parse_moderation_thresholds
)
import os


# Google Cloud NLP API Client
class NLPClient:
    """Google Cloud Natural Language API client."""
    
    def __init__(self, key_path: str):
        if not os.path.exists(key_path):
            raise FileNotFoundError(f"Service account key not found: {key_path}")
        credentials = service_account.Credentials.from_service_account_file(key_path)
        self._client = language_v1.LanguageServiceClient(credentials=credentials)
    
    def _create_document(self, text: str) -> language_v1.Document:
        return language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)
    
    def _get_severity(self, confidence: float) -> str:
        if confidence >= 0.8: return "HIGH"
        elif confidence >= 0.5: return "MEDIUM"
        elif confidence >= 0.3: return "LOW"
        return "NEGLIGIBLE"
    

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze text sentiment."""
        doc = self._create_document(text)
        response = self._client.analyze_sentiment(document=doc)
        sentiment = response.document_sentiment
        
        # Interpret sentiment
        if sentiment.score > 0.25: interpretation = "Positive"
        elif sentiment.score < -0.25: interpretation = "Negative"
        else: interpretation = "Neutral"
        
        if sentiment.magnitude > 2.0: intensity = "Strong"
        elif sentiment.magnitude > 1.0: intensity = "Moderate"
        else: intensity = "Mild"
        
        return {
            "score": round(sentiment.score, 4),
            "magnitude": round(sentiment.magnitude, 4),
            "interpretation": f"{intensity} {interpretation}",
            "sentences": [
                {"text": s.text.content, "score": round(s.sentiment.score, 4)}
                for s in response.sentences
            ]
        }
    

    def analyze_entities(self, text: str, blocked_types: Optional[List[Union[str, EntityType]]] = None) -> Dict[str, Any]:
        """
        Analyze entities in text.
        
        Args:
            text: Text to analyze
            blocked_types: Entity types to block. Can be strings like "person", "location" 
                          or EntityType enums. Case-insensitive.
        """
        doc = self._create_document(text)
        response = self._client.analyze_entities(document=doc)
        
        # Convert string inputs to EntityType enums
        parsed_blocked = parse_entity_types(blocked_types)
        blocked_type_values = [et.value for et in (parsed_blocked or list(EntityType))]
        
        entities = []
        blocked = []
        
        for entity in response.entities:
            entity_type = language_v1.Entity.Type(entity.type_).name
            entity_data = {
                "name": entity.name,
                "type": entity_type,
                "salience": round(entity.salience, 4)
            }
            entities.append(entity_data)
            
            if entity_type in blocked_type_values:
                blocked.append({
                    "category": "entity_detected",
                    "entity_name": entity.name,
                    "entity_type": entity_type,
                    "confidence": entity.salience,
                    "severity": self._get_severity(entity.salience)
                })
        
        return {"entities": entities, "blocked": blocked}


    
    def classify_text(self, text: str, blocked_categories: Optional[List[str]] = None, 
                      threshold: float = 0.5) -> Dict[str, Any]:
        """Classify text into categories. Requires 20+ words."""
        if len(text.split()) < 20:
            return {"error": "Text too short for classification (min 20 words)", "categories": [], "blocked": []}
        
        doc = self._create_document(text)
        response = self._client.classify_text(document=doc)
        
        categories = []
        blocked = []
        
        for cat in response.categories:
            cat_data = {"category": cat.name, "confidence": round(cat.confidence, 4)}
            categories.append(cat_data)
            
            if blocked_categories and cat.confidence >= threshold:
                for pattern in blocked_categories:
                    if pattern.lower() in cat.name.lower():
                        blocked.append({
                            "category": cat.name,
                            "matched_pattern": pattern,
                            "confidence": cat.confidence,
                            "severity": self._get_severity(cat.confidence)
                        })
                        break
        
        return {"categories": categories, "blocked": blocked}


    
    def moderate_text(self, text: str, 
                      blocked_categories: Optional[List[Union[str, ModerationCategory]]] = None,
                      thresholds: Optional[Dict[Union[str, ModerationCategory], float]] = None) -> Dict[str, Any]:
        """
        Moderate text for harmful content.
        
        Args:
            text: Text to moderate
            blocked_categories: Categories to block (default: all). Can be strings like 
                               "toxic", "violent" or ModerationCategory enums. Case-insensitive.
            thresholds: Per-category confidence thresholds (default: 0.5 for all).
                       Keys can be strings like "toxic" or ModerationCategory enums.
        """
        doc = self._create_document(text)
        response = self._client.moderate_text(document=doc)
        
        # Convert string inputs to ModerationCategory enums
        parsed_blocked = parse_moderation_categories(blocked_categories)
        parsed_thresholds = parse_moderation_thresholds(thresholds)
        
        # Default: block all categories
        if parsed_blocked is None:
            parsed_blocked = list(ModerationCategory)
        blocked_values = [cat.value for cat in parsed_blocked]
        
        # Default threshold
        default_threshold = 0.5
        
        moderation_results = []
        blocked = []
        
        for mod_cat in response.moderation_categories:
            severity = self._get_severity(mod_cat.confidence)
            moderation_results.append({
                "category": mod_cat.name,
                "confidence": round(mod_cat.confidence, 4),
                "severity": severity
            })
            
            if mod_cat.name in blocked_values:
                # Get threshold for this category
                cat_enum = next((c for c in ModerationCategory if c.value == mod_cat.name), None)
                threshold = (parsed_thresholds or {}).get(cat_enum, default_threshold)
                
                if mod_cat.confidence >= threshold:
                    blocked.append({
                        "category": mod_cat.name,
                        "confidence": mod_cat.confidence,
                        "threshold": threshold,
                        "severity": severity
                    })
        
        return {"moderation": moderation_results, "blocked": blocked}

