import os
from dotenv import load_dotenv
load_dotenv()

from cerebras.cloud.sdk import Cerebras

api_key = os.getenv("CEREBRAS_API_KEY", "")
print("CEREBRAS_API_KEY present:", bool(api_key))

models_to_test = ["llama3.1-8b", "llama-3.3-70b", "gpt-oss-120b", "llama3.1-70b"]

client = Cerebras(api_key=api_key)

for model in models_to_test:
    try:
        print(f"\nTesting model: {model}...")
        resp = client.chat.completions.create(
            messages=[{"role": "user", "content": "Why is wafer-scale computing faster?"}],
            model=model,
        )
        content = resp.choices[0].message.content
        print(f"SUCCESS ({model}): {content[:100]}...")
    except Exception as e:
        print(f"FAILED ({model}): {e}")
