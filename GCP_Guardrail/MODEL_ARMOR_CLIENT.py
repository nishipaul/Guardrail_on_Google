from google.cloud import modelarmor_v1
from google.oauth2 import service_account
from google.api_core.client_options import ClientOptions
from typing import Dict, Any
from ENUM_CLASSES import CheckType
import os


# Model Armor Client Initialization
class ModelArmorClient:
    """Google Cloud Model Armor API client."""
    
    def __init__(self, key_path: str, project_id: str, location_id: str, template_id: str):
        if not os.path.exists(key_path):
            raise FileNotFoundError(f"Service account key not found: {key_path}")
        
        credentials = service_account.Credentials.from_service_account_file(key_path)
        self._client = modelarmor_v1.ModelArmorClient(
            credentials=credentials,
            transport="rest",
            client_options=ClientOptions(api_endpoint=f"modelarmor.{location_id}.rep.googleapis.com")
        )
        self._template_path = f"projects/{project_id}/locations/{location_id}/templates/{template_id}"
    

    def _parse_response(self, response, check_type: str) -> Dict[str, Any]:
        """Parse Model Armor response."""
        sanitization = response.sanitization_result
        overall_match = str(sanitization.filter_match_state.name) if sanitization.filter_match_state else "UNKNOWN"
        
        filter_results = {}
        blocked_filters = []
        
        for filter_key, filter_value in sanitization.filter_results.items():
            parsed = self._parse_filter(filter_key, filter_value)
            filter_results[filter_key] = parsed
            
            if parsed.get("match_state") == "MATCH_FOUND":
                blocked_item = {"filter": filter_key, "match_state": "MATCH_FOUND"}
                if parsed.get("confidence_level"):
                    blocked_item["confidence_level"] = parsed["confidence_level"]
                if filter_key == "rai" and parsed.get("categories"):
                    blocked_item["matched_categories"] = [
                        {"category": k, "confidence_level": v.get("confidence_level")}
                        for k, v in parsed["categories"].items()
                        if v.get("match_state") == "MATCH_FOUND"
                    ]
                blocked_filters.append(blocked_item)
        
        return {
            "blocked": overall_match == "MATCH_FOUND",
            "overall_match_state": overall_match,
            "filter_results": filter_results,
            "blocked_filters": blocked_filters
        }


    
    def _parse_filter(self, filter_key: str, filter_value) -> Dict[str, Any]:
        """Parse a single filter result."""
        result = {"filter_type": filter_key, "execution_state": "UNKNOWN", "match_state": "UNKNOWN"}
        
        if filter_key == "rai" and filter_value.rai_filter_result:
            rai = filter_value.rai_filter_result
            result["execution_state"] = str(rai.execution_state.name) if rai.execution_state else "UNKNOWN"
            result["match_state"] = str(rai.match_state.name) if rai.match_state else "UNKNOWN"
            result["categories"] = {
                cat_name: {
                    "match_state": str(cat_result.match_state.name) if cat_result.match_state else "UNKNOWN",
                    "confidence_level": str(cat_result.confidence_level.name) 
                        if cat_result.confidence_level and cat_result.confidence_level.name != "CONFIDENCE_LEVEL_UNSPECIFIED" else None
                }
                for cat_name, cat_result in rai.rai_filter_type_results.items()
            }
        elif filter_key == "sdp" and filter_value.sdp_filter_result:
            sdp = filter_value.sdp_filter_result
            if sdp.inspect_result:
                result["execution_state"] = str(sdp.inspect_result.execution_state.name) if sdp.inspect_result.execution_state else "UNKNOWN"
                result["match_state"] = str(sdp.inspect_result.match_state.name) if sdp.inspect_result.match_state else "UNKNOWN"
        elif filter_key == "pi_and_jailbreak" and filter_value.pi_and_jailbreak_filter_result:
            pij = filter_value.pi_and_jailbreak_filter_result
            result["execution_state"] = str(pij.execution_state.name) if pij.execution_state else "UNKNOWN"
            result["match_state"] = str(pij.match_state.name) if pij.match_state else "UNKNOWN"
            result["confidence_level"] = str(pij.confidence_level.name) if pij.confidence_level and pij.confidence_level.name != "CONFIDENCE_LEVEL_UNSPECIFIED" else None
        elif filter_key == "malicious_uris" and filter_value.malicious_uri_filter_result:
            uri = filter_value.malicious_uri_filter_result
            result["execution_state"] = str(uri.execution_state.name) if uri.execution_state else "UNKNOWN"
            result["match_state"] = str(uri.match_state.name) if uri.match_state else "UNKNOWN"
        elif filter_key == "csam" and filter_value.csam_filter_filter_result:
            csam = filter_value.csam_filter_filter_result
            result["execution_state"] = str(csam.execution_state.name) if csam.execution_state else "UNKNOWN"
            result["match_state"] = str(csam.match_state.name) if csam.match_state else "UNKNOWN"
        
        return result
    


    def sanitize_user_prompt(self, text: str) -> Dict[str, Any]:
        """Sanitize user prompt."""
        request = modelarmor_v1.SanitizeUserPromptRequest(
            name=self._template_path,
            user_prompt_data=modelarmor_v1.DataItem(text=text)
        )
        response = self._client.sanitize_user_prompt(request=request)
        return self._parse_response(response, CheckType.USER_PROMPT.value)
    


    def sanitize_model_response(self, text: str) -> Dict[str, Any]:
        """Sanitize model response."""
        request = modelarmor_v1.SanitizeModelResponseRequest(
            name=self._template_path,
            model_response_data=modelarmor_v1.DataItem(text=text)
        )
        response = self._client.sanitize_model_response(request=request)
        return self._parse_response(response, CheckType.MODEL_RESPONSE.value)

