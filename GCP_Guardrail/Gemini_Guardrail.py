"""
Gemini Guardrail
A unified guardrail system combining GCP Natural Language API and Model Armor.

Features:
    - NLP API: Sentiment, Entity Detection, Text Classification, Content Moderation
    - Model Armor: RAI, SDP, Prompt Injection, Malicious URIs, CSAM detection
    - Flexible filter selection and threshold configuration
    - Case-insensitive category names (e.g., "person", "toxic", "violent")
"""


from MODEL_ARMOR_CLIENT import ModelArmorClient
from NLP_CLIENT import NLPClient
from google.api_core import exceptions as google_exceptions
from ENUM_CLASSES import *



# Picking configuration from the secrets folder
KEY_PATH = os.path.join(os.path.dirname(__file__), "secrets/guardrail_secret.json")
DEFAULT_LOCATION = "us-central1"
DEFAULT_PROJECT = "ai-experiments-345006"
DEFAULT_TEMPLATE = "litellm-gcp-guard"



# Complete Gemini Guardrail Wrapper
class GeminiGuardrail:
    """
    Unified guardrail combining NLP API and Model Armor.
    
    All category parameters accept simple string names (case-insensitive):
        - Entity types: "person", "location", "organization", "phone_number", etc.
        - Moderation categories: "toxic", "violent", "insult", "profanity", etc.
        - Check types: "user_prompt" or "model_response"
    """
    
    def __init__(self, key_path: Optional[str] = None, project_id: Optional[str] = None, location_id: Optional[str] = None, template_id: Optional[str] = None):
        """
        Initialize the unified guardrail.
        
        Args:
            key_path: Path to service account JSON file
            project_id: GCP project ID (for Model Armor)
            location_id: GCP region (for Model Armor)
            template_id: Model Armor template ID
        """
        self._key_path = key_path or KEY_PATH
        self._project_id = project_id or DEFAULT_PROJECT
        self._location_id = location_id or DEFAULT_LOCATION
        self._template_id = template_id or DEFAULT_TEMPLATE
        
        self._nlp_client: Optional[NLPClient] = None
        self._armor_client: Optional[ModelArmorClient] = None
    
    def _get_nlp_client(self) -> NLPClient:
        """Lazy initialization of NLP client."""
        if self._nlp_client is None:
            self._nlp_client = NLPClient(self._key_path)
        return self._nlp_client
    
    def _get_armor_client(self) -> ModelArmorClient:
        """Lazy initialization of Model Armor client."""
        if self._armor_client is None:
            self._armor_client = ModelArmorClient(
                self._key_path, self._project_id, self._location_id, self._template_id
            )
        return self._armor_client

    
    def _handle_error(self, e: Exception, guardrail_type: str) -> GuardrailResult:
        """Handle API errors gracefully."""
        error_msg = str(e)
        if isinstance(e, google_exceptions.InvalidArgument):
            error_msg = f"Invalid input: {getattr(e, 'message', str(e))}"
        elif isinstance(e, google_exceptions.PermissionDenied):
            error_msg = "Permission denied. Check API credentials."
        elif isinstance(e, google_exceptions.NotFound):
            error_msg = "Resource not found. Check configuration."
        elif isinstance(e, google_exceptions.ResourceExhausted):
            error_msg = "API quota exceeded."
        elif isinstance(e, google_exceptions.ServiceUnavailable):
            error_msg = "Service temporarily unavailable."
        
        return GuardrailResult(guardrail_type=guardrail_type, error=error_msg)




    
    # Checking Sentiment from NLP Client
    def check_sentiment(self, text: str) -> GuardrailResult:
        """Check text sentiment."""
        try:
            if not text or not text.strip():
                return GuardrailResult(guardrail_type=GuardrailType.NLP_SENTIMENT.value, error="Text cannot be empty")

            result = self._get_nlp_client().analyze_sentiment(text)
            return GuardrailResult(guardrail_type=GuardrailType.NLP_SENTIMENT.value, results=result)

        except Exception as e:
            return self._handle_error(e, GuardrailType.NLP_SENTIMENT.value)




    # Checking Entities from NLP Client - block types can be provided as strings
    def check_entities(self, text: str, blocked_types: Optional[List[Union[str, EntityType]]] = None) -> GuardrailResult:
        """
        Check text for entities.
        
        Args:
            text: Text to analyze
            blocked_types: Entity types to block. Can be strings like "person", "location", 
                          "phone_number" (case-insensitive) or EntityType enums.
        """
        try:
            if not text or not text.strip():
                return GuardrailResult(guardrail_type=GuardrailType.NLP_ENTITIES.value, error="Text cannot be empty")

            result = self._get_nlp_client().analyze_entities(text, blocked_types)
            return GuardrailResult(guardrail_type=GuardrailType.NLP_ENTITIES.value,
                results={"entities": result["entities"]}, blocked_items=result["blocked"])

        except Exception as e:
            return self._handle_error(e, GuardrailType.NLP_ENTITIES.value)




    
    # Checking Classification from NLP Client - block categories can be provided with threshold flexibility
    def check_classification(self, text: str, blocked_categories: Optional[List[str]] = None, threshold: float = 0.5) -> GuardrailResult:
        """Classify text into categories."""
        try:
            if not text or not text.strip():
                return GuardrailResult(guardrail_type=GuardrailType.NLP_CLASSIFY.value, error="Text cannot be empty")

            result = self._get_nlp_client().classify_text(text, blocked_categories, threshold)

            if "error" in result:
                return GuardrailResult(guardrail_type=GuardrailType.NLP_CLASSIFY.value, error=result["error"])

            return GuardrailResult(guardrail_type=GuardrailType.NLP_CLASSIFY.value,
                results={"categories": result["categories"]}, blocked_items=result["blocked"])

        except Exception as e:
            return self._handle_error(e, GuardrailType.NLP_CLASSIFY.value)


    
    # Checking Moderation from NLP Client - block categories can be provided with threshold flexibility
    def check_moderation(self, text: str, 
                         blocked_categories: Optional[List[Union[str, ModerationCategory]]] = None, 
                         thresholds: Optional[Dict[Union[str, ModerationCategory], float]] = None) -> GuardrailResult:
        """
        Moderate text for harmful content.
        
        Args:
            text: Text to moderate
            blocked_categories: Categories to block (default: all). Can be strings like 
                               "toxic", "violent", "insult" (case-insensitive) or enums.
            thresholds: Per-category thresholds. Keys can be strings like "toxic" or enums.
                       Example: {"toxic": 0.3, "violent": 0.5}
        """
        try:
            if not text or not text.strip():
                return GuardrailResult(guardrail_type=GuardrailType.NLP_MODERATE.value, error="Text cannot be empty")

            result = self._get_nlp_client().moderate_text(text, blocked_categories, thresholds)
            return GuardrailResult(guardrail_type=GuardrailType.NLP_MODERATE.value,
                results={"moderation": result["moderation"]}, blocked_items=result["blocked"])

        except Exception as e:
            return self._handle_error(e, GuardrailType.NLP_MODERATE.value)



    
    # Checking Model Armor from Model Armor Client - user prompt or model response can be provided
    def check_model_armor(self, text: str, check_type: Union[str, CheckType] = CheckType.USER_PROMPT) -> GuardrailResult:
        """
        Check text with Model Armor (RAI, SDP, Jailbreak, Malicious URIs, CSAM).
        
        Args:
            text: Text to check
            check_type: "user_prompt" or "model_response" (case-insensitive), or CheckType enum
        """
        try:
            if not text or not text.strip():
                return GuardrailResult(guardrail_type=GuardrailType.MODEL_ARMOR.value, error="Text cannot be empty")
            
            # Parse check_type if string
            parsed_check_type = parse_check_type(check_type)
            
            client = self._get_armor_client()
            if parsed_check_type == CheckType.USER_PROMPT:
                result = client.sanitize_user_prompt(text)
            else:
                result = client.sanitize_model_response(text)
            
            return GuardrailResult(guardrail_type=GuardrailType.MODEL_ARMOR.value,
                results={"filter_results": result["filter_results"], 
                         "overall_match_state": result["overall_match_state"]},
                blocked_items=result["blocked_filters"]
            )

        except Exception as e:
            return self._handle_error(e, GuardrailType.MODEL_ARMOR.value)



    
    # Checking all guardrails - multiple guardrails can be run at once
    def check(self, text: str, guardrails: Optional[List[GuardrailType]] = None, 
              check_type: Union[str, CheckType] = CheckType.USER_PROMPT,
              # NLP Entity config
              blocked_entity_types: Optional[List[Union[str, EntityType]]] = None,
              # NLP Classify config
              blocked_classification_categories: Optional[List[str]] = None, 
              classification_threshold: float = 0.5,
              # NLP Moderate config
              blocked_moderation_categories: Optional[List[Union[str, ModerationCategory]]] = None,
              moderation_thresholds: Optional[Dict[Union[str, ModerationCategory], float]] = None) -> Dict[str, Any]:
        """
        Run multiple guardrails and combine results.
        
        Args:
            text: Text to check
            guardrails: List of guardrails to run (default: all)
            check_type: "user_prompt" or "model_response" (case-insensitive)
            blocked_entity_types: Entity types to block (e.g., ["person", "location"])
            blocked_classification_categories: Classification categories to block
            classification_threshold: Threshold for classification blocking
            blocked_moderation_categories: Moderation categories to block (e.g., ["toxic", "violent"])
            moderation_thresholds: Per-category thresholds (e.g., {"toxic": 0.3})
            
        Returns:
            Combined results from all guardrails
        """
        # Default: run all guardrails
        if guardrails is None:
            guardrails = list(GuardrailType)
        
        results = {}
        all_blocked_items = []
        errors = []
        
        for guardrail in guardrails:
            if guardrail == GuardrailType.NLP_SENTIMENT:
                result = self.check_sentiment(text)
            elif guardrail == GuardrailType.NLP_ENTITIES:
                result = self.check_entities(text, blocked_entity_types)
            elif guardrail == GuardrailType.NLP_CLASSIFY:
                result = self.check_classification(text, blocked_classification_categories, classification_threshold)
            elif guardrail == GuardrailType.NLP_MODERATE:
                result = self.check_moderation(text, blocked_moderation_categories, moderation_thresholds)
            elif guardrail == GuardrailType.MODEL_ARMOR:
                result = self.check_model_armor(text, check_type)
            else:
                continue
            
            results[guardrail.value] = result.to_dict()
            
            if result.blocked_items:
                for item in result.blocked_items:
                    item["source"] = guardrail.value
                    all_blocked_items.append(item)
            
            if result.error:
                errors.append(f"{guardrail.value}: {result.error}")
        
        output = {
            "text_preview": text[:100] + "..." if len(text) > 100 else text,
            "guardrails_run": [g.value for g in guardrails],
            "results": results
        }
        
        # Only include blocked_items if there are any
        if all_blocked_items:
            output["blocked_items"] = all_blocked_items
        
        # Only include errors if there are any
        if errors:
            output["errors"] = errors
        
        return output
