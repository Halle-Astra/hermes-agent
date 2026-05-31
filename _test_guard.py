"""Quick test for continuation guard heuristic + JSON parser."""
import sys
sys.path.insert(0, ".")

from agent.conversation_loop import (
    _looks_like_premature_stop,
    _parse_llm_stall_judgment,
)

# ── Heuristic tests ────────────────────────────────────────────
# Only Tier 1 (tail-end) patterns are active.  The guard runs at
# every turn-end regardless of whether tools were called earlier.

SHOULD_CATCH = [
    # Tail: trailing ellipsis
    ("short_en_trailing", "Let me try running the test..."),
    # Tail: parenthetical action marker
    ("short_cn_paren", "\U0001f680 \u7acb\u5373\u6267\u884c\uff1a\u6743\u9650\u653b\u575a\u6d4b\u8bd5\n\u6211\u5c06\u5c1d\u8bd5\u4f7f\u7528 sudo \u6765\u6267\u884c\u622a\u56fe\u3002\n(\u5f00\u59cb\u6267\u884c...)"),
    # Long + tail marker
    ("long_cn_sample1", "\u770b\u5b8c\u8fd9\u4e2a Skill\u3002\n" * 3 + "(\u5f00\u59cb\u91cd\u5199\u6838\u5fc3\u9a71\u52a8...)"),
    ("long_cn_sample2", "\u6211\u5df2\u7ecf\u5b8c\u6210\u4e86 core/navigator.py \u7684\u5f7b\u5e95\u91cd\u6784\u3002\n" * 5 + "(\u51c6\u5907\u7f16\u5199\u5750\u6807\u6821\u51c6\u903b\u8f91...)"),
    # Plan section + action tail
    ("plan_tail", "blah blah\n\n\U0001f680 \u7acb\u5373\u884c\u52a8\uff1a\u91cd\u5199 core\n\u6211\u5c06\u6267\u884c\u91cd\u5199\u3002\n(\u5f00\u59cb\u91cd\u5199...)"),
    # EN trailing ellipsis
    ("en_next_steps", "I've analyzed the codebase.\n\nNext Steps:\n1. Fix the parser\n\nLet me start by fixing the parser..."),
    # EN parenthetical
    ("en_paren", "I'll now fix the bug.\n(Starting execution...)"),
    # Post-tool stall (model used tools earlier, still stalls at end)
    ("post_tool_stall", "\u5de5\u5177\u8c03\u7528\u5b8c\u6210\uff0c\u63a5\u4e0b\u6765\u6211\u8981\u7ee7\u7eed\u3002\n(\u5f00\u59cb\u4e0b\u4e00\u6b65\u64cd\u4f5c...)"),
]

SHOULD_NOT_CATCH = [
    ("final_en_1", "The answer is 42."),
    ("final_cn_1", "\u603b\u7ed3\uff1a\u8fd9\u4e2a\u95ee\u9898\u662f\u7531\u4e8e\u6743\u9650\u4e0d\u8db3\u5bfc\u81f4\u7684\u3002"),
    ("final_done", "Done! The file has been updated."),
    ("final_cannot", "I cannot access the display server."),
    ("final_sorry", "\u62b1\u6b49\uff0c\u6211\u65e0\u6cd5\u5b8c\u6210\u8fd9\u4e2a\u4efb\u52a1\u3002"),
    ("long_analysis", "Detailed analysis.\n" * 20 + "In summary, the root cause is X."),
    ("greeting", "Hello! How can I help you today?"),
    # Post-tool normal conclusions (NO tail marker)
    ("post_tool_summary", "\u5de5\u5177\u8fd4\u56de\u4e86\u7ed3\u679c\uff0c\u6211\u6765\u5206\u6790\u4e00\u4e0b\u3002\u95ee\u9898\u51fa\u5728\u6743\u9650\u914d\u7f6e\u4e0a\u3002"),
    ("post_tool_en", "I'll analyze the results. The issue is in the config."),
    ("post_tool_done", "I've checked the output. Everything looks good now."),
    # Short action language WITHOUT tail marker (legitimate narration)
    ("narration_cn", "\u6211\u5c06\u6267\u884c\u8fd9\u4e2a\u547d\u4ee4\u6765\u68c0\u67e5\u72b6\u6001"),
    ("narration_en", "I'll now run the screenshot command"),
]

print("=== SHOULD CATCH (expect True) ===")
all_ok = True
for name, text in SHOULD_CATCH:
    result = _looks_like_premature_stop(text, True)
    status = "PASS" if result else "FAIL"
    if not result:
        all_ok = False
    print(f"  [{status}] {name}: {result}")

print("\n=== SHOULD NOT CATCH (expect False) ===")
for name, text in SHOULD_NOT_CATCH:
    result = _looks_like_premature_stop(text, True)
    status = "PASS" if not result else "FAIL"
    if result:
        all_ok = False
    print(f"  [{status}] {name}: {result}")

# ── JSON parser tests ──────────────────────────────────────────
print("\n=== JSON PARSER ===")
PARSER_CASES = [
    ('{"stalled": true}', True),
    ('{"stalled": false}', False),
    ('Sure! {"stalled": true}', True),
    ('"stalled": true', True),
    ('stalled: false', False),
    ('YES', True),
    ('NO', False),
    ('', False),
    ('random gibberish xyz', False),
    ('```json\n{"stalled": true}\n```', True),
    ('**stalled**: true', True),
]

for raw, expected in PARSER_CASES:
    result = _parse_llm_stall_judgment(raw)
    status = "PASS" if result == expected else "FAIL"
    if result != expected:
        all_ok = False
    display = raw[:50].replace('\n', '\\n')
    print(f"  [{status}] {display!r} -> {result} (expected {expected})")

print(f"\n{'ALL TESTS PASSED' if all_ok else 'SOME TESTS FAILED'}")
sys.exit(0 if all_ok else 1)
