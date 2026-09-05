import os
from dotenv import load_dotenv
load_dotenv()

from openrouter import OpenRouter

api_key = os.getenv("OPENROUTER_API_KEY", "")
print("OPENROUTER_API_KEY present:", bool(api_key))

models_to_test = ["openrouter/free", "anthropic/claude-3.5-haiku", "meta-llama/llama-3.3-70b-instruct"]

client = OpenRouter(api_key=api_key)

for model in models_to_test:
    try:
        print(f"\nTesting model: {model}...")
        resp = client.chat.send(
            messages=[{"role": "user", "content": "Why is wafer-scale computing faster?"}],
            model=model,
        )
        content = resp.choices[0].message.content
        print(f"SUCCESS ({model}): {content[:100]}...")
    except Exception as e:
        print(f"FAILED ({model}): {e}")
