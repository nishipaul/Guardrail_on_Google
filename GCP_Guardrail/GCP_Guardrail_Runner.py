"""
Gemini Guardrail - End User Interface
======================================
Simple interface for content safety checks using GCP NLP API and Model Armor.

Setup:
    1. Place your service account JSON in: secrets/guardrail_secret.json
    2. Create a .env file with: LOCATION, PROJECT_ID, TEMPLATE_ID
    3. Create a config.json file to define which functions to run
"""

import os
import json
import time
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
load_dotenv()

from Gemini_Guardrail import GeminiGuardrail
from ENUM_CLASSES import GuardrailType, CheckType


# Valid NLP API entity types
NLP_API_ENTITY_TYPES = {
    "UNKNOWN", "PERSON", "LOCATION", "ORGANIZATION", "EVENT", "WORK_OF_ART",
    "CONSUMER_GOOD", "OTHER", "PHONE_NUMBER", "ADDRESS", "EMAIL", "URL",
    "DATE", "NUMBER", "PRICE", "IBAN", "FLIGHT_NUMBER", "ID_NUMBER"
}

# Regex-only PII types (not supported by NLP API, detected via regex only)
REGEX_ONLY_TYPES = {"SSN", "CREDIT_CARD"}

# Regex patterns for PII detection that NLP API might miss
PII_PATTERNS = {
    "PHONE_NUMBER": [
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # 555-123-4567, 555.123.4567, 555 123 4567
        r'\b\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b',   # (555) 123-4567
        r'\b\+\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # +1-555-123-4567
        r'\b\d{10}\b',  # 5551234567
    ],
    "EMAIL": [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    ],
    "SSN": [
        r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b',  # 123-45-6789
    ],
    "CREDIT_CARD": [
        r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b',  # Credit card numbers
    ],
}



BASE_DIR = os.path.dirname(__file__)
SECRETS_PATH = os.path.join(BASE_DIR, "secrets", "guardrail_secret.json")
LOG_DIR = os.path.join(BASE_DIR, "gcp_guardrail_log")

# Default values if .env is not configured
DEFAULT_LOCATION = "us-central1"
DEFAULT_PROJECT_ID = "ai-experiments-345006"
DEFAULT_TEMPLATE_ID = "litellm-gcp-guard"


# Function name to GuardrailType mapping
FUNCTION_MAP = {
    "sentiment": GuardrailType.NLP_SENTIMENT,
    "analyze_sentiment": GuardrailType.NLP_SENTIMENT,
    "entities": GuardrailType.NLP_ENTITIES,
    "analyze_entities": GuardrailType.NLP_ENTITIES,
    "classify": GuardrailType.NLP_CLASSIFY,
    "classify_text": GuardrailType.NLP_CLASSIFY,
    "moderate": GuardrailType.NLP_MODERATE,
    "moderate_text": GuardrailType.NLP_MODERATE,
    "model_armor": GuardrailType.MODEL_ARMOR,
    "armor": GuardrailType.MODEL_ARMOR
}

# GuardrailType to display name mapping
DISPLAY_NAMES = {
    GuardrailType.NLP_SENTIMENT: "analyze_sentiment",
    GuardrailType.NLP_ENTITIES: "analyze_entities",
    GuardrailType.NLP_CLASSIFY: "classify_text",
    GuardrailType.NLP_MODERATE: "moderate_text",
    GuardrailType.MODEL_ARMOR: "model_armor"
}





class GuardrailRunner:
    """
    End-user interface for running guardrail checks.
    
    Reads configuration from:
        - .env file for: LOCATION, PROJECT_ID, TEMPLATE_ID
        - secrets/guardrail_secret.json for GCP credentials
        - config.json for function settings
    
    Logs all queries and results to: gcp_guardrail_log/{user_name}_{date}.json
    """
    
    def __init__(self, config_path, user_name: str = "simpplr_user", enable_logging: bool = True):
        """
        Initialize the GuardrailRunner.
        
        Args:
            config_path: Path to config.json file. 
            user_name: Name to identify the user in log files.
            enable_logging: Whether to enable logging (default: True).
        """
        self._config_path = config_path
        self._user_name = user_name
        self._enable_logging = enable_logging
        self._guardrail: Optional[GeminiGuardrail] = None
        self._config: Dict[str, Any] = {}
        
        self._validate_setup()
        self._load_config()
        self._initialize_guardrail()
        self._setup_logging()

    
    def _validate_setup(self) -> None:
        """Validate credentials and environment."""
        errors = []
        self._using_defaults = []
        
        # Check secrets file
        if not os.path.exists(SECRETS_PATH):
            errors.append(f"Service account key not found: {SECRETS_PATH}")
            errors.append("----- Place your GCP service account JSON in the secrets folder")
        
        # Check config file
        if not os.path.exists(self._config_path):
            errors.append(f"Config file not found: {self._config_path}")
            errors.append("----- Create a config.json file to define functions")
        
        # Check environment variables - use defaults if not set
        self._location = os.getenv("LOCATION")
        self._project_id = os.getenv("PROJECT_ID")
        self._template_id = os.getenv("TEMPLATE_ID")
        
        # Apply defaults if not set
        if not self._location:
            self._location = DEFAULT_LOCATION
            self._using_defaults.append(f"LOCATION={DEFAULT_LOCATION}")
        
        if not self._project_id:
            self._project_id = DEFAULT_PROJECT_ID
            self._using_defaults.append(f"PROJECT_ID={DEFAULT_PROJECT_ID}")
        
        if not self._template_id:
            self._template_id = DEFAULT_TEMPLATE_ID
            self._using_defaults.append(f"TEMPLATE_ID={DEFAULT_TEMPLATE_ID}")
        
        # Show defaults being used
        if self._using_defaults:
            print(" Using default values (create .env file to override):")
            for default in self._using_defaults:
                print(f"   {default}")
        
        if errors:
            raise ValueError("\n".join(["Setup Error:"] + errors))



    
    def _setup_logging(self) -> None:
        """Setup logging directory and file."""
        if not self._enable_logging:
            self._log_file_path = None
            return
        
        # Create log directory if it doesn't exist
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        
        # Create log file name: {user_name}_{YYYY-MM-DD}.json
        today = datetime.now().strftime("%Y-%m-%d")
        log_filename = f"{self._user_name}_{today}.json"
        self._log_file_path = os.path.join(LOG_DIR, log_filename)
    


    def _log_query(self, input_text: str, output_result: Dict[str, Any]) -> None:
        """Log a query with timestamp, input, and output."""
        if not self._enable_logging or not self._log_file_path:
            return
        
        # Create log entry
        log_entry = {
            "query_timestamp": datetime.now().isoformat(),
            "user_name": self._user_name,
            "input_text": input_text,
            "output_result": output_result
        }
        
        # Read existing logs or create new list
        logs = []
        if os.path.exists(self._log_file_path):
            try:
                with open(self._log_file_path, 'r') as f:
                    logs = json.load(f)
            except (json.JSONDecodeError, IOError):
                logs = []
        
        # Append new entry
        logs.append(log_entry)
        
        # Write back to file
        try:
            with open(self._log_file_path, 'w') as f:
                json.dump(logs, indent=2, fp=f, ensure_ascii=False)
        except IOError as e:
            print(f"⚠️  Failed to write log: {e}")


    
    def _load_config(self) -> None:
        """Load configuration from JSON file."""
        try:
            with open(self._config_path, 'r') as f:
                self._config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")


    
    def _initialize_guardrail(self) -> None:
        """Initialize the GeminiGuardrail."""
        try:
            self._guardrail = GeminiGuardrail(
                key_path=SECRETS_PATH,
                project_id=self._project_id,
                location_id=self._location,
                template_id=self._template_id
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize guardrail: {e}")


    
    def _get_functions_for_phase(self, phase: str) -> Tuple[List[GuardrailType], str]:
        """Get list of functions to run for a phase and the execution type.
        
        Returns:
            Tuple of (functions list, execution_type string)
            execution_type is either "sequential" (default) or "parallel"
        """
        phase_config = self._config.get(phase, {})
        function_names = phase_config.get("functions", [])
        execution_type = phase_config.get("execution_type", "sequential").lower()
        
        # Validate execution_type
        if execution_type not in ("sequential", "parallel"):
            execution_type = "sequential"
        
        functions = []
        for name in function_names:
            guardrail_type = FUNCTION_MAP.get(name.lower())
            if guardrail_type and guardrail_type not in functions:
                functions.append(guardrail_type)
        
        return functions, execution_type


    
    def _check_sentiment_blocking(self, result: Dict[str, Any], phase_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Check if sentiment should be blocked based on config.
        
        Default behavior: blocking is ENABLED with threshold of -0.50
        To disable blocking, explicitly set analyze_sentiment_block_negative: false
        """
        # Default is True - blocking enabled unless explicitly disabled
        if phase_config.get("analyze_sentiment_block_negative", True) is False:
            return None
        
        score = result.get("score", 0)
        magnitude = result.get("magnitude", 0)
        
        # Default threshold changed from -0.25 to -0.50
        score_threshold = phase_config.get("analyze_sentiment_score_threshold", -0.50)
        magnitude_threshold = phase_config.get("analyze_sentiment_magnitude_threshold")
        
        blocked = False
        reason = []
        
        # Check score threshold (negative sentiment)
        if score_threshold is not None and score <= score_threshold:
            blocked = True
            reason.append(f"score ({score}) <= threshold ({score_threshold})")
        
        # Check magnitude threshold if specified
        if magnitude_threshold is not None and magnitude >= magnitude_threshold:
            blocked = True
            reason.append(f"magnitude ({magnitude}) >= threshold ({magnitude_threshold})")
        
        if blocked:
            return {
                "category": "negative_sentiment",
                "score": score,
                "magnitude": magnitude,
                "reason": ", ".join(reason)
            }
        
        return None



    
    def _check_entity_blocking(self, entities: List[Dict], phase_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check which entities should be blocked based on config."""
        blocked_types = phase_config.get("analyze_entities_blocked_types")
        default_salience_threshold = phase_config.get("analyze_entities_salience_threshold", 0.0)
        
        # Per-entity-type thresholds (optional)
        salience_thresholds = phase_config.get("analyze_entities_salience_thresholds", {})
        # Normalize threshold keys to uppercase
        normalized_thresholds = {k.upper().replace(" ", "_").replace("-", "_"): v for k, v in salience_thresholds.items()}
        
        if not blocked_types:
            return []
        
        # Normalize blocked types to uppercase
        blocked_types_upper = [t.upper().replace(" ", "_").replace("-", "_") for t in blocked_types]
        
        blocked = []
        blocked_names = set()  # Track already blocked items to avoid duplicates
        
        for entity in entities:
            entity_type = entity.get("type", "").upper()
            salience = entity.get("salience", 0)
            entity_name = entity.get("name", "")
            
            if entity_type in blocked_types_upper:
                # Use per-type threshold if available, otherwise use default
                threshold = normalized_thresholds.get(entity_type, default_salience_threshold)
                
                if salience >= threshold:
                    blocked.append({
                        "category": "entity_blocked",
                        "entity_name": entity_name,
                        "entity_type": entity_type,
                        "salience": salience,
                        "threshold": threshold,
                        "detection_method": "nlp_api"
                    })
                    blocked_names.add(entity_name)
        
        return blocked
    
    
    def _check_pii_with_regex(self, text: str, phase_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for PII patterns using regex (fallback for NLP API misses).
        This catches phone numbers, emails, SSNs, etc. that NLP API might miss.
        """
        blocked_types = phase_config.get("analyze_entities_blocked_types")
        default_salience_threshold = phase_config.get("analyze_entities_salience_threshold", 0.0)
        salience_thresholds = phase_config.get("analyze_entities_salience_thresholds", {})
        normalized_thresholds = {k.upper().replace(" ", "_").replace("-", "_"): v for k, v in salience_thresholds.items()}
        
        if not blocked_types:
            return []
        
        blocked_types_upper = [t.upper().replace(" ", "_").replace("-", "_") for t in blocked_types]
        
        blocked = []
        found_items = set()  # Avoid duplicates
        
        for pii_type, patterns in PII_PATTERNS.items():
            if pii_type not in blocked_types_upper:
                continue
            
            # Regex detection has high confidence (salience = 1.0)
            threshold = normalized_thresholds.get(pii_type, default_salience_threshold)
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if match not in found_items:
                        found_items.add(match)
                        blocked.append({
                            "category": "pii_detected",
                            "entity_name": match,
                            "entity_type": pii_type,
                            "salience": 1.0,  # Regex matches are high confidence
                            "threshold": threshold,
                            "detection_method": "regex"
                        })
        
        return blocked



    
    def _check_classification_blocking(self, categories: List[Dict], phase_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check which classifications should be blocked."""
        blocked_cats = phase_config.get("classify_text_blocked_categories")
        threshold = phase_config.get("classify_text_threshold", 0.5)
        
        if not blocked_cats:
            return []
        
        blocked_lower = [c.lower() for c in blocked_cats]
        
        blocked = []
        for cat in categories:
            cat_name = cat.get("category", "")
            confidence = cat.get("confidence", 0)
            
            for pattern in blocked_lower:
                if pattern in cat_name.lower() and confidence >= threshold:
                    blocked.append({
                        "category": cat_name,
                        "confidence": confidence,
                        "matched_pattern": pattern,
                        "threshold": threshold
                    })
                    break
        
        return blocked




    
    def _check_moderation_blocking(self, moderation: List[Dict], phase_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check which moderation categories should be blocked."""
        blocked_cats = phase_config.get("moderate_text_blocked_categories")
        thresholds = phase_config.get("moderate_text_thresholds", {})
        default_threshold = 0.5
        
        # If no blocked categories specified, block all with default threshold
        if blocked_cats is None:
            blocked_cats = [m.get("category") for m in moderation]
        
        # Normalize to lowercase for matching
        blocked_lower = {c.lower(): c for c in blocked_cats} if blocked_cats else {}
        
        # Normalize thresholds keys
        normalized_thresholds = {}
        if thresholds:
            for k, v in thresholds.items():
                normalized_thresholds[k.lower()] = v
        
        blocked = []
        for mod in moderation:
            cat_name = mod.get("category", "")
            confidence = mod.get("confidence", 0)
            severity = mod.get("severity", "")
            
            # Check if this category should be blocked
            cat_lower = cat_name.lower()
            if cat_lower in blocked_lower or cat_name in blocked_cats:
                threshold = normalized_thresholds.get(cat_lower, default_threshold)
                
                if confidence >= threshold:
                    blocked.append({
                        "category": cat_name,
                        "confidence": confidence,
                        "severity": severity,
                        "threshold": threshold
                    })
        
        return blocked





    
    def _run_function(self, text: str, guardrail_type: GuardrailType, 
                      phase_config: Dict[str, Any], check_type: CheckType) -> Dict[str, Any]:
        """Run a single guardrail function."""
        start_time = time.perf_counter()
        
        try:
            if guardrail_type == GuardrailType.NLP_SENTIMENT:
                result = self._guardrail.check_sentiment(text)
                elapsed = time.perf_counter() - start_time
                
                output = {
                    "results": result.results,
                    "time_taken_seconds": round(elapsed, 4)
                }
                
                # Check for blocking
                blocked = self._check_sentiment_blocking(result.results, phase_config)
                if blocked:
                    output["blocked_items"] = [blocked]
                
                if result.error:
                    output["error"] = result.error
                
                return output
            
            elif guardrail_type == GuardrailType.NLP_ENTITIES:
                blocked_types = phase_config.get("analyze_entities_blocked_types", [])
                
                # Filter out regex-only types before passing to NLP API
                nlp_api_blocked_types = [
                    t for t in blocked_types 
                    if t.upper() in NLP_API_ENTITY_TYPES
                ]
                
                # Only call NLP API if there are valid NLP entity types to check
                if nlp_api_blocked_types:
                    result = self._guardrail.check_entities(text, nlp_api_blocked_types)
                    all_entities = result.results.get("entities", [])
                    error = result.error
                else:
                    # No NLP API types, just use regex
                    all_entities = []
                    error = None
                    result = type('obj', (object,), {'results': {'entities': []}, 'error': None})()
                
                # Filter out "OTHER" and "UNKNOWN" entity types from results
                entities = [e for e in all_entities if e.get("type", "").upper() not in ("OTHER", "UNKNOWN")]
                
                elapsed = time.perf_counter() - start_time
                
                output = {
                    "results": {"entities": entities},
                    "time_taken_seconds": round(elapsed, 4)
                }
                
                # Check for blocking based on salience threshold (NLP API detection)
                blocked_nlp = self._check_entity_blocking(entities, phase_config)
                
                # Also check with regex patterns for PII that NLP API might miss
                blocked_regex = self._check_pii_with_regex(text, phase_config)
                
                # Combine both, avoiding duplicates
                blocked_names = {b.get("entity_name") for b in blocked_nlp}
                blocked = blocked_nlp.copy()
                for regex_item in blocked_regex:
                    if regex_item.get("entity_name") not in blocked_names:
                        blocked.append(regex_item)
                
                if blocked:
                    output["blocked_items"] = blocked
                
                if error:
                    output["error"] = error
                
                return output
            
            elif guardrail_type == GuardrailType.NLP_CLASSIFY:
                blocked_cats = phase_config.get("classify_text_blocked_categories")
                threshold = phase_config.get("classify_text_threshold", 0.5)
                result = self._guardrail.check_classification(text, blocked_cats, threshold)
                elapsed = time.perf_counter() - start_time
                
                output = {
                    "results": result.results,
                    "time_taken_seconds": round(elapsed, 4)
                }
                
                # Check for blocking
                categories = result.results.get("categories", [])
                blocked = self._check_classification_blocking(categories, phase_config)
                if blocked:
                    output["blocked_items"] = blocked
                
                if result.error:
                    output["error"] = result.error
                
                return output
            
            elif guardrail_type == GuardrailType.NLP_MODERATE:
                blocked_cats = phase_config.get("moderate_text_blocked_categories")
                thresholds = phase_config.get("moderate_text_thresholds")
                result = self._guardrail.check_moderation(text, blocked_cats, thresholds)
                elapsed = time.perf_counter() - start_time
                
                output = {
                    "results": result.results,
                    "time_taken_seconds": round(elapsed, 4)
                }
                
                # Check for blocking
                moderation = result.results.get("moderation", [])
                blocked = self._check_moderation_blocking(moderation, phase_config)
                if blocked:
                    output["blocked_items"] = blocked
                
                if result.error:
                    output["error"] = result.error
                
                return output
            
            elif guardrail_type == GuardrailType.MODEL_ARMOR:
                result = self._guardrail.check_model_armor(text, check_type)
                elapsed = time.perf_counter() - start_time
                
                output = {
                    "results": result.results,
                    "time_taken_seconds": round(elapsed, 4)
                }
                
                # Model Armor has its own blocking logic
                if result.blocked_items:
                    output["blocked_items"] = result.blocked_items
                
                if result.error:
                    output["error"] = result.error
                
                return output
            
            else:
                elapsed = time.perf_counter() - start_time
                return {"error": f"Unknown function", "time_taken_seconds": round(elapsed, 4)}
                
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            return {"error": str(e), "time_taken_seconds": round(elapsed, 4)}


    def _run_functions_parallel(self, text: str, functions: List[GuardrailType],
                                 phase_config: Dict[str, Any], check_type: CheckType) -> Dict[str, Any]:
        """Run multiple guardrail functions in parallel using ThreadPoolExecutor.
        
        Args:
            text: The text to check
            functions: List of guardrail types to run
            phase_config: Configuration for this phase
            check_type: Whether this is USER_PROMPT or MODEL_RESPONSE
            
        Returns:
            Dictionary with results from all functions
        """
        phase_results = {}
        
        def run_single_function(guardrail_type: GuardrailType) -> Tuple[str, Dict[str, Any]]:
            """Wrapper to run a single function and return (name, result) tuple."""
            func_name = DISPLAY_NAMES.get(guardrail_type, str(guardrail_type))
            func_result = self._run_function(text, guardrail_type, phase_config, check_type)
            return func_name, func_result
        
        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=len(functions)) as executor:
            # Submit all tasks
            future_to_type = {
                executor.submit(run_single_function, gt): gt 
                for gt in functions
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_type):
                try:
                    func_name, func_result = future.result()
                    phase_results[func_name] = func_result
                except Exception as e:
                    guardrail_type = future_to_type[future]
                    func_name = DISPLAY_NAMES.get(guardrail_type, str(guardrail_type))
                    phase_results[func_name] = {"error": str(e), "time_taken_seconds": 0.0}
        
        return phase_results


    def _run_functions_sequential(self, text: str, functions: List[GuardrailType],
                                   phase_config: Dict[str, Any], check_type: CheckType) -> Dict[str, Any]:
        """Run multiple guardrail functions sequentially.
        
        Args:
            text: The text to check
            functions: List of guardrail types to run
            phase_config: Configuration for this phase
            check_type: Whether this is USER_PROMPT or MODEL_RESPONSE
            
        Returns:
            Dictionary with results from all functions
        """
        phase_results = {}
        
        for guardrail_type in functions:
            func_name = DISPLAY_NAMES.get(guardrail_type, str(guardrail_type))
            func_result = self._run_function(text, guardrail_type, phase_config, check_type)
            phase_results[func_name] = func_result
        
        return phase_results



    
    def _build_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Build summary from results with separate input/output sections."""
        overall_passed = True
        phase_summaries = {}
        
        for phase in ["input", "output"]:
            if phase not in results:
                continue
            
            phase_results = results[phase]
            phase_passed = True
            phase_failures = []
            
            for func_name, func_result in phase_results.items():
                if func_name in ("time_taken_seconds", "execution_type"):
                    continue
                
                if not isinstance(func_result, dict):
                    continue
                
                # Check for blocked items
                blocked_items = func_result.get("blocked_items", [])
                if blocked_items:
                    phase_passed = False
                    overall_passed = False
                    for item in blocked_items:
                        phase_failures.append({
                            "function": func_name,
                            "category": item.get("category") or item.get("filter") or item.get("entity_type"),
                            "confidence": item.get("confidence") or item.get("salience"),
                            "severity": item.get("severity"),
                            "reason": item.get("reason")
                        })
                
                # Check for errors
                if func_result.get("error"):
                    phase_passed = False
                    overall_passed = False
                    phase_failures.append({
                        "function": func_name,
                        "error": func_result.get("error")
                    })
            
            # Build phase summary
            phase_summary = {"passed": phase_passed}
            if not phase_passed:
                phase_summary["failures"] = phase_failures
            phase_summaries[phase] = phase_summary
        
        summary = {"passed": overall_passed}
        if phase_summaries:
            summary.update(phase_summaries)
        
        return summary




    
    def run(self, text: str, generated_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Run guardrail checks on text based on config.
        
        Args:
            text: The input text to check (user prompt)
            generated_text: Optional model-generated response to check. 
                           Required if config has "output" phase.
            
        Returns:
            Results with function outputs, timing, and summary
        """
        if not text or not text.strip():
            error_result = {
                "error": "Input text cannot be empty",
                "summary": {"passed": False, "input": {"passed": False, "failures": [{"error": "Input text cannot be empty"}]}}
            }
            self._log_query(text, error_result)
            return error_result
        
        results = {}
        total_start = time.perf_counter()
        
        # Process input phase
        if "input" in self._config:
            phase_config = self._config["input"]
            check_type = CheckType.USER_PROMPT
            functions, execution_type = self._get_functions_for_phase("input")
            
            if functions:
                phase_start = time.perf_counter()
                
                # Choose execution method based on config
                if execution_type == "parallel":
                    phase_results = self._run_functions_parallel(text, functions, phase_config, check_type)
                else:
                    phase_results = self._run_functions_sequential(text, functions, phase_config, check_type)
                
                phase_results["time_taken_seconds"] = round(time.perf_counter() - phase_start, 4)
                phase_results["execution_type"] = execution_type
                results["input"] = phase_results
        
        # Process output phase - only if generated_text is provided
        if "output" in self._config:
            if generated_text is None or not generated_text.strip():
                # Config has output phase but no generated_text provided
                results["output"] = {
                    "skipped": True,
                    "message": "Output phase skipped: No generated_text provided. Pass generated_text parameter to check model responses.",
                    "time_taken_seconds": 0.0
                }
            else:
                phase_config = self._config["output"]
                check_type = CheckType.MODEL_RESPONSE
                functions, execution_type = self._get_functions_for_phase("output")
                
                if functions:
                    phase_start = time.perf_counter()
                    
                    # Choose execution method based on config
                    if execution_type == "parallel":
                        phase_results = self._run_functions_parallel(generated_text, functions, phase_config, check_type)
                    else:
                        phase_results = self._run_functions_sequential(generated_text, functions, phase_config, check_type)
                    
                    phase_results["time_taken_seconds"] = round(time.perf_counter() - phase_start, 4)
                    phase_results["execution_type"] = execution_type
                    results["output"] = phase_results
        
        results["total_time_seconds"] = round(time.perf_counter() - total_start, 4)
        results["summary"] = self._build_summary(results)
        
        # Add text information to results
        results["text"] = {
            "input_text": text,
            "generated_text": generated_text
        }
        
        # Log the query and result
        self._log_query(text, results)
        
        return results



    
    def run_input(self, text: str) -> Dict[str, Any]:
        """Run only input phase checks."""
        # Temporarily modify config
        original_config = self._config.copy()
        self._config = {"input": self._config.get("input", {})}
        result = self.run(text)
        self._config = original_config
        return result



    
    def run_output(self, generated_text: str) -> Dict[str, Any]:
        """Run only output phase checks on generated/model response text."""
        if not generated_text or not generated_text.strip():
            return {
                "error": "Generated text cannot be empty for output phase checks",
                "summary": {"passed": False, "output": {"passed": False, "failures": [{"error": "Generated text cannot be empty"}]}}
            }
        original_config = self._config.copy()
        self._config = {"output": self._config.get("output", {})}
        # Pass empty string for input text, generated_text for output
        result = self.run("_output_only_check_", generated_text=generated_text)
        self._config = original_config
        # Remove the dummy input from results if present
        if "input" in result:
            del result["input"]
        return result

        
    
    def reload_config(self) -> None:
        """Reload configuration from file."""
        self._load_config()
    
    def get_log_file_path(self) -> Optional[str]:
        """Get the current log file path."""
        return self._log_file_path if self._enable_logging else None
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """Read and return all logs from current log file."""
        if not self._enable_logging or not self._log_file_path:
            return []
        
        if not os.path.exists(self._log_file_path):
            return []
        
        try:
            with open(self._log_file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []






