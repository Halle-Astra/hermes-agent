"""Debug call_llm return type."""
import sys
sys.path.insert(0, ".")
from agent.auxiliary_client import call_llm

raw = call_llm(
    task="continuation_guard",
    max_tokens=30,
    messages=[{"role": "user", "content": "Say hello in JSON: {\"greeting\": \"hello\"}"}],
)
print(f"type: {type(raw)}")
print(f"repr: {raw!r}")
if hasattr(raw, 'choices'):
    print(f"choices[0].message.content: {raw.choices[0].message.content!r}")
if hasattr(raw, 'content'):
    print(f"content: {raw.content!r}")
