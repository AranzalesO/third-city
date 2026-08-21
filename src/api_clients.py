# src/api_clients.py

import os
import time
import random
from abc import ABC, abstractmethod
from openai import OpenAI
import google.generativeai as genai
import anthropic
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
    'api key is invalid',
    'permission_denied',
    'permission_error',
    'prepayment credits are depleted',
    'generaterequestsperdayperproject',
    # Perplexity surfaces auth failures as "HTTP 401: ..."; the OpenAI and
    # Anthropic SDKs use "Error code: 401 - ...". Both spellings are needed.
    'http 401',
    'http 403',
    'error code: 401',
    'error code: 403',
    'authentication_error',
    # Raised SDK-side (no HTTP call) when no key is configured at all -- e.g. a
    # deploy that shipped before its API key env var was set.
    'could not resolve authentication method',
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


class ClaudeClient(LLMClient):
    """Anthropic Claude API client"""

    def __init__(self, api_key: str = None, model: str = "claude-sonnet-5"):
        super().__init__()
        # ANTHROPIC_API_KEY is the SDK's own standard name. CLAUDE_API_KEY is
        # accepted as a fallback so a deployment still holding the older name
        # (e.g. an unmigrated Render env var) keeps working.
        self.api_key = (api_key or os.getenv("ANTHROPIC_API_KEY")
                        or os.getenv("CLAUDE_API_KEY"))
        self.model = model
        # max_retries=0 for the same reason as ChatGPT: _run_with_retry decides
        # what's worth retrying, so the SDK's silent backoff can't burn ~20s per
        # doomed call on a permanently failing key.
        self.client = anthropic.Anthropic(api_key=self.api_key, max_retries=0)

    def query(self, prompt: str, system_prompt: str) -> str:
        def call():
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
                # Simple consumer Q&A -- low effort keeps thinking (and spend)
                # minimal. Thinking is left on: disabling it on Opus 5 risks the
                # model writing a tool call into visible text instead of calling
                # the search tool, which would silently cost us the sources.
                output_config={"effort": "low"},
                # Real web search, so Claude cites live sources like ChatGPT and
                # Perplexity do rather than recalling URLs from training data.
                # This variant runs code execution internally -- do NOT also
                # declare a code_execution tool.
                tools=[{
                    "type": "web_search_20260209",
                    "name": "web_search",
                    "max_uses": 3,
                }],
            )

            # A safety refusal returns HTTP 200 with no usable answer. Surface it
            # as an error rather than letting it look like an empty response.
            if response.stop_reason == "refusal":
                details = getattr(response, "stop_details", None)
                category = getattr(details, "category", None) or "unspecified"
                raise RuntimeError(f"Model refused to answer (category: {category})")

            return self._extract_text_with_sources(response)

        return self._run_with_retry(call)

    @staticmethod
    def _extract_text_with_sources(response) -> str:
        """Join the answer text and append the URLs the search actually used.

        Claude returns cited URLs in structured web_search_tool_result blocks,
        NOT inside the answer text (verified against the live API). The analyzer
        scrapes domains out of the response string, so without this the whole
        'Source(s) Cited' column would be blank for Claude even though the
        search ran.
        """
        text_parts = []
        urls = []

        def remember(url):
            if url and url not in urls:
                urls.append(url)

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
                # Citations may also carry URLs depending on the response.
                for citation in (getattr(block, "citations", None) or []):
                    remember(getattr(citation, "url", None))
            elif block.type == "web_search_tool_result":
                content = block.content
                # Success -> list of results; error -> a single error object.
                if isinstance(content, list):
                    for result in content:
                        remember(getattr(result, "url", None))

        text = "".join(text_parts).strip()

        if urls:
            text += "\n\nSources: " + " ".join(urls)

        return text

    def get_platform_name(self) -> str:
        return "Claude"


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
        elif platform == "claude":
            return ClaudeClient()
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
        if platforms.get("claude", False):
            clients.append(ClaudeClient())

        return clients