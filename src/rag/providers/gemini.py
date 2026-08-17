import os
import json
import logging
from typing import Dict, Any
import google.generativeai as genai
from google.generativeai.types import generation_types

from rag.providers.base import LLMProvider

logger = logging.getLogger(__name__)

class GeminiProvider(LLMProvider):
    """
    Implementation of the LLMProvider using Google's Gemini API.
    """
    
    def __init__(self, model_name: str = "gemini-3.6-flash", temperature: float = 0.0):
        # Pick up API key from environment
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY environment variable not set. API calls will fail unless previously configured.")
            
        if api_key:
            genai.configure(api_key=api_key)
            
        # Using flash for prototype speed, temperature 0.0 for deterministic output
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                response_mime_type="application/json"
            )
        )
        
    def generate_structured_rca(self, system_prompt: str, user_prompt: str, evidence_pack_json: str) -> Dict[str, Any]:
        """
        Executes the prompt against Gemini, forcing JSON output.
        """
        prompt = f"""
        {system_prompt}
        
        EVIDENCE PACK:
        {evidence_pack_json}
        
        USER QUERY:
        {user_prompt}
        """
        
        try:
            # Execute with error handling
            response = self.model.generate_content(prompt)
            # Parse the JSON response
            result = json.loads(response.text)
            return result
        except json.JSONDecodeError as e:
            logger.error(f"LLM returned invalid JSON: {str(e)}\nRaw output: {response.text}")
            raise RuntimeError("LLM failed to generate valid JSON") from e
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise
