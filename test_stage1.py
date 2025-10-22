# test_stage1.py

from src.api_clients import ChatGPTClient, GeminiClient, PerplexityClient

def test_all_platforms():
    print("Testing API integrations...\n")
    
    test_prompt = "Which EV brands offer the longest driving range?"
    system_prompt = "Answer as a UK consumer in incognito mode. Keep answers factual and neutral."
    
    # Test ChatGPT
    print("1. Testing ChatGPT...")
    chatgpt = ChatGPTClient()
    response = chatgpt.query(test_prompt, system_prompt)
    print(f"✓ ChatGPT Response ({len(response)} chars): {response[:100]}...\n")
    
    # Test Gemini
    print("2. Testing Gemini...")
    gemini = GeminiClient()
    response = gemini.query(test_prompt, system_prompt)
    print(f"✓ Gemini Response ({len(response)} chars): {response[:100]}...\n")
    
    # Test Perplexity
    print("3. Testing Perplexity...")
    perplexity = PerplexityClient()
    response = perplexity.query(test_prompt, system_prompt)
    print(f"✓ Perplexity Response ({len(response)} chars): {response[:100]}...\n")
    
    print("✅ All platforms tested successfully!")

if __name__ == "__main__":
    test_all_platforms()