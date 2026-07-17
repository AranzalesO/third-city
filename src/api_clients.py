# src/api_clients.py

import os
import time
import random
from abc import ABC, abstractmethod
from openai import OpenAI
import google.generativeai as genai
import requests
from dotenv import load_dotenv

load_dotenv()


# Error fragments meaning "this will never succeed": no credit, bad key, or a
# free-tier daily cap that won't reset today. Retrying these is pure waste --
# every later call fails identically, and each failure costs ~20s of backoff.
# Deliberately excludes per-minute rate limits, which ARE worth retrying (note
# that transient limits also mention "billing details", so we can't match that).
FATAL_ERROR_PATTERNS = (
    'insufficient_quota',
    'invalid_api_key',
    'incorrect api key',
    'api key not valid',
    'api_key_invalid',
    'permission_denied',
    'prepayment credits are depleted',
    'generaterequestsperdayperproject',
    'http 401',
    'http 403',
    'unauthorized',
)


def _is_fatal_error(message: str) -> bool:
    """True if an error is permanent and the platform should stop trying."""
    text = (message or '').lower()
    return any(pattern in text for pattern in FATAL_ERROR_PATTERNS)


class LLMClient(ABC):
    """Abstract base class for LLM API clients"""

    MAX_TRANSIENT_RETRIES = 3

    def __init__(self):
        self.last_error = None
        # Once set, every further call on this client short-circuits instantly.
        self.fatal_error = None

    def _run_with_retry(self, call):
        """Run an API call, retrying transient failures with backoff.

        Permanent failures disable the client so a long campaign doesn't spend
        hours re-failing the same doomed request once per run.
        """
        if self.fatal_error:
            self.last_error = self.fatal_error
            return ""

        for attempt in range(self.MAX_TRANSIENT_RETRIES + 1):
            try:
                result = call()
                self.last_error = None
                return result
            except Exception as e:
                message = str(e)

                if _is_fatal_error(message):
                    self.fatal_error = message
                    self.last_error = message
                    print(f"{self.get_platform_name()} FATAL: {message[:200]}", flush=True)
                    return ""

                self.last_error = message
                if attempt >= self.MAX_TRANSIENT_RETRIES:
                    print(f"{self.get_platform_name()} Error: {message[:200]}", flush=True)
                    return ""

                # Transient (rate limit, network blip) - back off and retry.
                time.sleep(min(2 ** attempt, 8) + random.uniform(0, 0.5))

        return ""

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
        super().__init__()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        # max_retries=0: the SDK's own backoff silently burns ~20s per doomed
        # call. _run_with_retry decides what's worth retrying instead.
        self.client = OpenAI(api_key=self.api_key, max_retries=0)

    def query(self, prompt: str, system_prompt: str) -> str:
        def call():
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
            return response.output_text

        return self._run_with_retry(call)

    def get_platform_name(self) -> str:
        return "ChatGPT"



class GeminiClient(LLMClient):
    """Google Gemini API client"""
    
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash-lite"):
        super().__init__()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(self.model)

    def query(self, prompt: str, system_prompt: str) -> str:
        def call():
            # Combine system and user prompts
            full_prompt = f"{system_prompt}\n\nUser question: {prompt}"

            response = self.client.generate_content(full_prompt)

            # Check if response has text
            if hasattr(response, 'text') and response.text:
                return response.text

            print(f"Gemini: No text in response", flush=True)
            return ""

        return self._run_with_retry(call)

    def get_platform_name(self) -> str:
        return "Gemini"
        

class PerplexityClient(LLMClient):
    """Perplexity API client"""
    
    def __init__(self, api_key: str = None, model: str = "sonar"):
        super().__init__()
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.model = model
        self.base_url = "https://api.perplexity.ai/chat/completions"

    def query(self, prompt: str, system_prompt: str) -> str:
        def call():
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
                timeout=60
            )

            # Raise so _run_with_retry can decide: HTTP 401/403 is fatal,
            # 429/5xx is transient and worth a backoff retry.
            if response.status_code != 200:
                raise RuntimeError(
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )

            result = response.json()
            return result["choices"][0]["message"]["content"]

        return self._run_with_retry(call)

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