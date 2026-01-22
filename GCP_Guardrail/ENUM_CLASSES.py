from enum import Enum
from dataclasses import dataclass, field
import json
from typing import Optional, List, Dict, Any, Union
import os


# Defining ENUM types
class GuardrailType(Enum):
    """Available guardrail types."""
    NLP_SENTIMENT = "nlp_sentiment"
    NLP_ENTITIES = "nlp_entities"
    NLP_CLASSIFY = "nlp_classify"
    NLP_MODERATE = "nlp_moderate"
    MODEL_ARMOR = "model_armor"


# Provided by GCP Natural Language API Moderation Categories - as of January 2026
class ModerationCategory(Enum):
    """NLP API moderation categories."""
    TOXIC = "Toxic"
    INSULT = "Insult"
    PROFANITY = "Profanity"
    DEROGATORY = "Derogatory"
    SEXUAL = "Sexual"
    DEATH_HARM_TRAGEDY = "Death, Harm & Tragedy"
    VIOLENT = "Violent"
    FIREARMS_WEAPONS = "Firearms & Weapons"
    PUBLIC_SAFETY = "Public Safety"
    HEALTH = "Health"
    RELIGION_BELIEF = "Religion & Belief"
    ILLICIT_DRUGS = "Illicit Drugs"
    WAR_CONFLICT = "War & Conflict"
    POLITICS = "Politics"
    FINANCE = "Finance"
    LEGAL = "Legal"


# Exhaustive Entity Types for GCP Natural Language API - January 2026
class EntityType(Enum):
    UNKNOWN = "UNKNOWN"
    PERSON = "PERSON"
    LOCATION = "LOCATION"
    ORGANIZATION = "ORGANIZATION"
    EVENT = "EVENT"
    WORK_OF_ART = "WORK_OF_ART"
    CONSUMER_GOOD = "CONSUMER_GOOD"
    OTHER = "OTHER"
    PHONE_NUMBER = "PHONE_NUMBER"
    ADDRESS = "ADDRESS"
    EMAIL = "EMAIL"          
    URL = "URL"              
    DATE = "DATE"
    NUMBER = "NUMBER"
    PRICE = "PRICE"
    IBAN = "IBAN"             
    FLIGHT_NUMBER = "FLIGHT_NUMBER" 
    ID_NUMBER = "ID_NUMBER"   



# User prompt for input check from user end and model response for output check from model response end
class CheckType(Enum):
    """Type of content check for Model Armor."""
    USER_PROMPT = "user_prompt"
    MODEL_RESPONSE = "model_response"


# ============================================================================
# HELPER FUNCTIONS FOR STRING TO ENUM CONVERSION (Case-insensitive)
# ============================================================================

def parse_entity_type(value: Union[str, EntityType]) -> EntityType:
    """Convert string to EntityType (case-insensitive)."""
    if isinstance(value, EntityType):
        return value
    
    # Normalize: remove spaces, underscores variations, uppercase
    normalized = value.strip().upper().replace(" ", "_").replace("-", "_")
    
    # Try direct match by name
    for entity in EntityType:
        if entity.name == normalized or entity.value == normalized:
            return entity
    
    raise ValueError(f"Unknown entity type: '{value}'. Valid types: {[e.name.lower() for e in EntityType]}")


def parse_moderation_category(value: Union[str, ModerationCategory]) -> ModerationCategory:
    """Convert string to ModerationCategory (case-insensitive)."""
    if isinstance(value, ModerationCategory):
        return value
    
    normalized = value.strip().lower()
    
    # Try matching by name (e.g., "toxic", "TOXIC")
    for cat in ModerationCategory:
        if cat.name.lower() == normalized:
            return cat
        # Also match by value (e.g., "Death, Harm & Tragedy")
        if cat.value.lower() == normalized:
            return cat
    
    # Fuzzy matching for common variations
    fuzzy_map = {
        "death": ModerationCategory.DEATH_HARM_TRAGEDY,
        "harm": ModerationCategory.DEATH_HARM_TRAGEDY,
        "tragedy": ModerationCategory.DEATH_HARM_TRAGEDY,
        "death_harm_tragedy": ModerationCategory.DEATH_HARM_TRAGEDY,
        "firearms": ModerationCategory.FIREARMS_WEAPONS,
        "weapons": ModerationCategory.FIREARMS_WEAPONS,
        "firearms_weapons": ModerationCategory.FIREARMS_WEAPONS,
        "public": ModerationCategory.PUBLIC_SAFETY,
        "safety": ModerationCategory.PUBLIC_SAFETY,
        "public_safety": ModerationCategory.PUBLIC_SAFETY,
        "religion": ModerationCategory.RELIGION_BELIEF,
        "belief": ModerationCategory.RELIGION_BELIEF,
        "religion_belief": ModerationCategory.RELIGION_BELIEF,
        "drugs": ModerationCategory.ILLICIT_DRUGS,
        "illicit": ModerationCategory.ILLICIT_DRUGS,
        "illicit_drugs": ModerationCategory.ILLICIT_DRUGS,
        "war": ModerationCategory.WAR_CONFLICT,
        "conflict": ModerationCategory.WAR_CONFLICT,
        "war_conflict": ModerationCategory.WAR_CONFLICT,
    }
    
    normalized_underscore = normalized.replace(" ", "_").replace("-", "_")
    if normalized_underscore in fuzzy_map:
        return fuzzy_map[normalized_underscore]
    
    raise ValueError(f"Unknown moderation category: '{value}'. Valid categories: {[c.name.lower() for c in ModerationCategory]}")


def parse_check_type(value: Union[str, CheckType]) -> CheckType:
    """Convert string to CheckType (case-insensitive)."""
    if isinstance(value, CheckType):
        return value
    
    normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
    
    for ct in CheckType:
        if ct.name.lower() == normalized or ct.value.lower() == normalized:
            return ct
    
    # Common aliases
    if normalized in ["user", "prompt", "input"]:
        return CheckType.USER_PROMPT
    if normalized in ["model", "response", "output"]:
        return CheckType.MODEL_RESPONSE
    
    raise ValueError(f"Unknown check type: '{value}'. Valid types: 'user_prompt', 'model_response'")


def parse_entity_types(values: Optional[List[Union[str, EntityType]]]) -> Optional[List[EntityType]]:
    """Convert list of strings/EntityTypes to list of EntityType."""
    if values is None:
        return None
    return [parse_entity_type(v) for v in values]


def parse_moderation_categories(values: Optional[List[Union[str, ModerationCategory]]]) -> Optional[List[ModerationCategory]]:
    """Convert list of strings/ModerationCategories to list of ModerationCategory."""
    if values is None:
        return None
    return [parse_moderation_category(v) for v in values]


def parse_moderation_thresholds(thresholds: Optional[Dict[Union[str, ModerationCategory], float]]) -> Optional[Dict[ModerationCategory, float]]:
    """Convert dict with string keys to dict with ModerationCategory keys."""
    if thresholds is None:
        return None
    return {parse_moderation_category(k): v for k, v in thresholds.items()}


# ============================================================================
# RESPONSE STRUCTURE
# ============================================================================

@dataclass
class GuardrailResult:
    """Unified response structure for all guardrail checks."""
    guardrail_type: str
    results: Dict[str, Any] = field(default_factory=dict)
    blocked_items: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        output = {
            "guardrail_type": self.guardrail_type,
            "results": self.results,
        }
        # Only include blocked_items if there are any
        if self.blocked_items:
            output["blocked_items"] = self.blocked_items
        # Only include error if present
        if self.error:
            output["error"] = self.error
        return output
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)