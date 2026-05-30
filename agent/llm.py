"""
llm.py
Local Ollama integration for the Dependency Analyzer Agent.
Runs locally - no internet required after model download!
"""

from __future__ import annotations
import json
import os
import requests
from typing import Dict, List, Optional, Any

# Ollama local server settings
OLLAMA_BASE_URL = "http://localhost:11434"


class OllamaLLM:
    """
    Local Ollama LLM client for dependency analysis.
    
    Runs LOCALLY - no API keys, no internet, no firewall issues!
    
    Supported models (download at home, use at work):
    - llama3.1 (recommended, good balance)
    - llama3.1:8b (default, fastest)
    - llama3.1:70b (best quality, requires powerful PC)
    - mistral (alternative)
    - codellama (code-focused)
    """
    
    def __init__(
        self,
        model_id: str = "llama3.1:8b",
        base_url: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ):
        """
        Initialize local Ollama client.
        
        Args:
            model_id: Ollama model name (e.g., "llama3.1:8b")
            base_url: Ollama server URL (default: http://localhost:11434)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)
        """
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.base_url = base_url or OLLAMA_BASE_URL
        
        # Check if Ollama is running
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                print(f"Ollama is running! Available models: {', '.join(model_names) if model_names else 'None'}")
                
                if not model_names:
                    print("\nWarning: No models downloaded yet!")
                    print("   Download from home/mobile hotspot:")
                    print("   ollama pull llama3.1")
                elif model_id not in model_names and f"{model_id}:latest" not in model_names:
                    print(f"\nWarning: Model '{model_id}' not found. Using first available model.")
                    self.model_id = model_names[0]
            else:
                print("Warning: Ollama server not responding properly")
        except requests.exceptions.ConnectionError:
            print("\nError: Ollama is NOT running!")
            print("   1. Install Ollama: https://ollama.com/download")
            print("   2. Start Ollama (it runs automatically on Windows)")
            print("   3. Download model from home: ollama pull llama3.1")
        except Exception as e:
            print(f"Warning: Error connecting to Ollama: {e}")
    
    def _format_messages(self, messages: List[Dict], system: Optional[str] = None) -> str:
        """Format messages for Ollama API."""
        formatted_prompt = ""
        
        if system:
            formatted_prompt += f"System: {system}\n\n"
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                formatted_prompt += f"User: {content}\n"
            elif role == "assistant":
                formatted_prompt += f"Assistant: {content}\n"
        
        formatted_prompt += "Assistant: "
        return formatted_prompt
    
    def invoke(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invoke the local Ollama model.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system: Optional system prompt
        
        Returns:
            {
                "content": str,
                "stop_reason": str,
                "usage": dict,
                "model_id": str
            }
        """
        try:
            # Format prompt
            prompt = self._format_messages(messages, system)
            
            # Call local Ollama API
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_id,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("response", "")
                
                return {
                    "content": content.strip(),
                    "stop_reason": "stop",
                    "usage": {
                        "prompt_tokens": result.get("prompt_eval_count", 0),
                        "completion_tokens": result.get("eval_count", 0),
                        "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0)
                    },
                    "model_id": self.model_id
                }
            else:
                return {
                    "content": "",
                    "error": f"Ollama API error: {response.status_code} - {response.text}",
                    "stop_reason": "error",
                    "usage": {},
                    "model_id": self.model_id
                }
            
        except requests.exceptions.ConnectionError:
            return {
                "content": "**Ollama Not Running**\n\nPlease start Ollama and download a model:\n1. Install from https://ollama.com/download\n2. Run: ollama pull llama3.1\n3. Ollama runs automatically",
                "error": "Ollama server not running",
                "stop_reason": "error",
                "usage": {},
                "model_id": self.model_id
            }
        except Exception as e:
            return {
                "content": "",
                "error": f"Error: {str(e)}",
                "stop_reason": "error",
                "usage": {},
                "model_id": self.model_id
            }
    
    def stream_invoke(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None
    ):
        """
        Stream responses from local Ollama.
        """
        try:
            prompt = self._format_messages(messages, system)
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_id,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens
                    }
                },
                stream=True,
                timeout=120
            )
            
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    if "response" in chunk:
                        yield chunk["response"]
        
        except Exception as e:
            yield f"\n[Error: {str(e)}]"


def create_ollama_client(
    model_id: str = None,
    base_url: str = None
) -> OllamaLLM:
    """
    Create local Ollama client.
    
    Args:
        model_id: Ollama model name (defaults to llama3.1:8b)
        base_url: Ollama server URL
    """
    model_id = model_id or os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    return OllamaLLM(model_id=model_id, base_url=base_url)


# Available Ollama models (all run locally!)
OLLAMA_MODELS = {
    "llama3.1:8b": "llama3.1:8b",
    "llama3.1:70b": "llama3.1:70b", 
    "llama3.1": "llama3.1",
    "mistral": "mistral",
    "codellama": "codellama",
}
