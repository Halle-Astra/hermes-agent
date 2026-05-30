"""Test LLM continuation_guard call against the real model."""
import sys
sys.path.insert(0, ".")
from agent.auxiliary_client import call_llm, extract_content_or_reasoning
from agent.conversation_loop import _parse_llm_stall_judgment

TAIL_STALLED = (
    "\U0001f9ea \u4e0b\u4e00\u6b65\uff1a\u5750\u6807\u5bf9\u9f50\u4e0e\u89c6\u89c9\u95ed\u73af\u9a8c\u8bc1\n"
    "\u6211\u5c06\u7acb\u5373\u5b9e\u73b0 real-mouse-coordinate-calibration \u903b\u8f91\n"
    "(\u51c6\u5907\u7f16\u5199\u5750\u6807\u6821\u51c6\u903b\u8f91...)"
)

TAIL_DONE = (
    "\u603b\u7ed3\uff1a\u95ee\u9898\u7684\u6839\u672c\u539f\u56e0\u662f\u6743\u9650\u914d\u7f6e\u9519\u8bef\u3002\n"
    "\u5df2\u7ecf\u901a\u8fc7\u4fee\u6539 /etc/sudoers \u89e3\u51b3\u4e86\u8fd9\u4e2a\u95ee\u9898\u3002"
)

PROMPT_TEMPLATE = (
    'An AI coding agent just returned the following text as its '
    'COMPLETE output for this turn.  The agent has tools (terminal, '
    'file editor, search, etc.) but used NONE of them \u2014 it only '
    'produced this text.\n\n'
    '---AGENT OUTPUT (tail)---\n'
    '{tail}\n'
    '---END---\n\n'
    'Does the output end by announcing an action the agent is about '
    'to take (e.g. "Starting execution...", "(\u5f00\u59cb\u91cd\u5199...)", '
    '"I\'ll now run X", "\u51c6\u5907\u7f16\u5199...") WITHOUT actually doing it?\n\n'
    'Respond with ONLY a JSON object, nothing else:\n'
    '{{"stalled": true}}  \u2014 if the agent announced actions but stopped\n'
    '{{"stalled": false}} \u2014 if this is a genuine completed response\n'
)

for label, tail, expected in [
    ("STALLED", TAIL_STALLED, True),
    ("DONE", TAIL_DONE, False),
]:
    prompt = PROMPT_TEMPLATE.format(tail=tail)
    print(f"\n{'='*60}")
    print(f"Test: {label} (expected stalled={expected})")
    print(f"{'='*60}")

    for attempt in range(3):
        try:
            resp = call_llm(
                task="continuation_guard",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )
            content = extract_content_or_reasoning(resp)
            parsed = _parse_llm_stall_judgment(content)
            status = "PASS" if parsed == expected else "FAIL"
            print(f"  Attempt {attempt+1}: raw={content!r}  parsed={parsed}  [{status}]")
        except Exception as exc:
            print(f"  Attempt {attempt+1}: ERROR: {exc}")
