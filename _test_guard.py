"""Quick test for continuation guard heuristic + JSON parser."""
import sys
sys.path.insert(0, ".")

from agent.conversation_loop import (
    _looks_like_premature_stop,
    _parse_llm_stall_judgment,
)

# ── Heuristic tests ────────────────────────────────────────────

SHOULD_CATCH = [
    # Original short samples (no tool context)
    ("short_en_1", "I'll now run the screenshot command", False),
    ("short_en_2", "Let me try running the test...", False),
    # Chinese short (no tool context)
    ("short_cn_1", "\U0001f680 \u7acb\u5373\u6267\u884c\uff1a\u6743\u9650\u653b\u575a\u6d4b\u8bd5\n\u6211\u5c06\u5c1d\u8bd5\u4f7f\u7528 sudo \u6765\u6267\u884c\u622a\u56fe\u3002\n(\u5f00\u59cb\u6267\u884c...)", False),
    # Long sample 1 - ends with action marker (tail catch)
    ("long_cn_sample1", "\u770b\u5b8c\u8fd9\u4e2a Skill\uff0c\u6211\u611f\u5230\u4e00\u79cd\u5f3a\u70c8\u7684\u3001\u751a\u81f3\u6709\u4e9b\u7f9e\u6127\u7684\u201c\u8ba4\u77e5\u51b2\u51fb\u201d\u3002\n" * 3 + "\U0001f680 \u7ec8\u6781\u91cd\u6784\u8ba1\u5212\n\u6211\u5c06\u4e0d\u518d\u7f16\u5199\u4efb\u4f55\u201c\u5c1d\u8bd5\u6027\u201d\u7684\u4ee3\u7801\u3002\n(\u5f00\u59cb\u91cd\u5199\u6838\u5fc3\u9a71\u52a8...)", False),
    # Long sample 2 - ends with action marker (tail catch)
    ("long_cn_sample2", "\u6211\u5df2\u7ecf\u5b8c\u6210\u4e86 core/navigator.py \u7684\u5f7b\u5e95\u91cd\u6784\u3002\n" * 5 + "\U0001f9ea \u4e0b\u4e00\u6b65\uff1a\u5750\u6807\u5bf9\u9f50\u4e0e\u89c6\u89c9\u95ed\u73af\u9a8c\u8bc1\n\u6211\u5c06\u7acb\u5373\u5b9e\u73b0 real-mouse-coordinate-calibration \u903b\u8f91\n(\u51c6\u5907\u7f16\u5199\u5750\u6807\u6821\u51c6\u903b\u8f91...)", False),
    # Plan section + action tail (tail catch, even after tool)
    ("plan_tail_after_tool", "blah blah analysis...\n\n\U0001f680 \u7acb\u5373\u884c\u52a8\uff1a\u91cd\u5199 core/navigator.py\n\u6211\u5c06\u76f4\u63a5\u6309\u7167\u89c4\u8303\u7f16\u5199\u9a71\u52a8\u7a0b\u5e8f\u3002\n(\u5f00\u59cb\u91cd\u5199...)", True),
    # EN trailing ellipsis
    ("en_trailing", "I've analyzed the codebase.\n\nNext Steps:\n1. Fix the parser\n2. Update tests\n\nLet me start by fixing the parser...", False),
    # Short with specific action verb (not after tool)
    ("short_cn_specific", "\u6211\u5c06\u6267\u884c\u8fd9\u4e2a\u547d\u4ee4\u6765\u68c0\u67e5\u72b6\u6001", False),
]

SHOULD_NOT_CATCH = [
    # Genuine final answers
    ("final_en_1", "The answer is 42.", False),
    ("final_cn_1", "\u603b\u7ed3\uff1a\u8fd9\u4e2a\u95ee\u9898\u662f\u7531\u4e8e\u6743\u9650\u4e0d\u8db3\u5bfc\u81f4\u7684\u3002", False),
    ("final_done", "Done! The file has been updated.", False),
    ("final_cannot", "I cannot access the display server because the DISPLAY variable is not set.", False),
    ("final_sorry", "\u62b1\u6b49\uff0c\u6211\u65e0\u6cd5\u5b8c\u6210\u8fd9\u4e2a\u4efb\u52a1\u3002", False),
    # Long genuine analysis (no action tail)
    ("long_analysis", "This is a detailed analysis of the problem.\n" * 20 + "In summary, the root cause is X and the fix is Y.", False),
    # Short response with no action
    ("greeting", "Hello! How can I help you today?", False),
    # POST-TOOL conversational responses (the key false positive cases)
    ("post_tool_cn_1", "\u6211\u6765\u5206\u6790\u4e00\u4e0b\u8fd9\u4e2a\u7ed3\u679c\uff0c\u770b\u8d77\u6765\u95ee\u9898\u51fa\u5728\u6743\u9650\u914d\u7f6e\u4e0a\u3002", True),
    ("post_tool_cn_2", "\u597d\u7684\uff0c\u6211\u8981\u68c0\u67e5\u4e00\u4e0b\u8fd4\u56de\u7684\u65e5\u5fd7\u4fe1\u606f\u3002", True),
    ("post_tool_cn_3", "\u63a5\u4e0b\u6765\u6211\u4f1a\u5904\u7406\u8fd9\u4e2a\u9519\u8bef\u3002", True),
    ("post_tool_en_1", "Let me check the output from the command.", True),
    ("post_tool_en_2", "I'll analyze these results now.", True),
]

print("=== SHOULD CATCH (expect True) ===")
all_ok = True
for name, text, prev_tool in SHOULD_CATCH:
    result = _looks_like_premature_stop(text, True, prev_was_tool=prev_tool)
    status = "PASS" if result else "FAIL"
    if not result:
        all_ok = False
    print(f"  [{status}] {name} (prev_tool={prev_tool}): {result}")

print("\n=== SHOULD NOT CATCH (expect False) ===")
for name, text, prev_tool in SHOULD_NOT_CATCH:
    result = _looks_like_premature_stop(text, True, prev_was_tool=prev_tool)
    status = "PASS" if not result else "FAIL"
    if result:
        all_ok = False
    print(f"  [{status}] {name} (prev_tool={prev_tool}): {result}")

# ── JSON parser tests ──────────────────────────────────────────
print("\n=== JSON PARSER (expect correct bool) ===")
PARSER_CASES = [
    ('{"stalled": true}', True),
    ('{"stalled": false}', False),
    ('{"stalled":true}', True),
    ('Sure! {"stalled": true}', True),
    ('The answer is {"stalled": false}.', False),
    ('"stalled": true', True),
    ('stalled = true', True),
    ('stalled: false', False),
    ('YES', True),
    ('NO', False),
    ('True', True),
    ('False', False),
    ('I think the answer is YES because...', True),
    ('', False),
    ('random gibberish xyz', False),
    # Weak model outputs
    ('```json\n{"stalled": true}\n```', True),
    ('Based on my analysis, {"stalled": true} is the answer.', True),
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
