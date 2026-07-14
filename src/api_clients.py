# src/api_clients.py

import os
import time
from abc import ABC, abstractmethod
from openai import OpenAI
import google.generativeai as genai
import requests
from dotenv import load_dotenv

load_dotenv()


class LLMClient(ABC):
    """Abstract base class for LLM API clients"""
    
    @abstractmethod
    def query(self, prompt: str, system_prompt: str) -> str:
        """Send a query to the LLM and return the response"""
        pass
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """Return the platform name"""
        pass


class ChatGPTClient(LLMClient):
    """OpenAI ChatGPT API client"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        self.last_error = None

    def query(self, prompt: str, system_prompt: str) -> str:
        try:
            # Use the Responses API with web search so answers cite real,
            # live sources instead of the plain Chat Completions API, which
            # has no internet access and can't produce real citations.
            response = self.client.responses.create(
                model=self.model,
                instructions=system_prompt,
                input=prompt,
                temperature=0.6,
                tools=[{"type": "web_search_preview"}]
            )
            self.last_error = None
            return response.output_text
        except Exception as e:
            self.last_error = str(e)
            print(f"ChatGPT Error: {e}")
            return ""
    
    def get_platform_name(self) -> str:
        return "ChatGPT"



class GeminiClient(LLMClient):
    """Google Gemini API client"""
    
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash-lite"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(self.model)
        self.last_error = None

    def query(self, prompt: str, system_prompt: str) -> str:
        try:
            # Combine system and user prompts
            full_prompt = f"{system_prompt}\n\nUser question: {prompt}"

            response = self.client.generate_content(full_prompt)

            # Check if response has text
            if hasattr(response, 'text') and response.text:
                self.last_error = None
                return response.text
            else:
                self.last_error = "No text in response"
                print(f"Gemini: No text in response")
                return ""

        except Exception as e:
            self.last_error = str(e)
            print(f"Gemini Error: {e}")
            return ""
    
    def get_platform_name(self) -> str:
        return "Gemini"
        

class PerplexityClient(LLMClient):
    """Perplexity API client"""
    
    def __init__(self, api_key: str = None, model: str = "sonar"):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.model = model
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.last_error = None

    def query(self, prompt: str, system_prompt: str) -> str:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.6,
                "max_tokens": 1024
            }

            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=30
            )

            # Debug: print response details
            if response.status_code != 200:
                self.last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                print(f"Perplexity Status Code: {response.status_code}")
                print(f"Perplexity Response: {response.text}")
                return ""

            result = response.json()
            self.last_error = None
            return result["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            self.last_error = str(e)
            print(f"Perplexity Request Error: {e}")
            return ""
        except KeyError as e:
            self.last_error = f"Unexpected response format: missing {e}"
            print(f"Perplexity Response Format Error: {e}")
            return ""
        except Exception as e:
            self.last_error = str(e)
            print(f"Perplexity Error: {e}")
            return ""
    
    def get_platform_name(self) -> str:
        return "Perplexity"


class LLMClientFactory:
    """Factory to create LLM clients"""
    
    @staticmethod
    def create_client(platform: str) -> LLMClient:
        platform = platform.lower()
        
        if platform == "chatgpt":
            return ChatGPTClient()
        elif platform == "gemini":
            return GeminiClient()
        elif platform == "perplexity":
            return PerplexityClient()
        else:
            raise ValueError(f"Unknown platform: {platform}")
    
    @staticmethod
    def create_all_clients(config: dict) -> list:
        """Create clients for all enabled platforms"""
        clients = []
        platforms = config.get("platforms", {})
        
        if platforms.get("chatgpt", False):
            clients.append(ChatGPTClient())
        if platforms.get("gemini", False):
            clients.append(GeminiClient())
        if platforms.get("perplexity", False):
            clients.append(PerplexityClient())
        
        return clients