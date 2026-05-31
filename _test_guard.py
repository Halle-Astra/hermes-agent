"""Quick test for continuation guard heuristic + JSON parser."""
import sys
sys.path.insert(0, ".")

from agent.conversation_loop import (
    _looks_like_premature_stop,
    _parse_llm_stall_judgment,
)

# ── Heuristic tests ────────────────────────────────────────────
# Core rule: a STALL is a response that is PURELY forward-looking
# ("I'll do X") with NO completed work reported.  If the response
# mentions ANY completed work ("I've finished X", "已完成"),
# it's a progress report, not a stall.

SHOULD_CATCH = [
    # PURELY forward-looking, no completed work
    ("pure_cn_will", "\U0001f680 \u6743\u9650\u653b\u575a\u6d4b\u8bd5\n\u6211\u5c06\u5c1d\u8bd5\u4f7f\u7528 sudo \u6765\u6267\u884c\u622a\u56fe"),
    ("pure_cn_prepare", "\u6211\u8981\u91cd\u5199 core/navigator.py"),
    ("pure_cn_next", "\u63a5\u4e0b\u6765\u6211\u8981\u5b9e\u73b0\u5750\u6807\u6821\u51c6\u903b\u8f91"),
    ("pure_cn_start", "\u51c6\u5907\u7f16\u5199\u5750\u6807\u6821\u51c6\u903b\u8f91"),
    ("pure_en_will", "I'll now run the screenshot command"),
    ("pure_en_let", "Let me start by fixing the parser"),
    ("pure_en_next", "Next, I'll implement the fix"),
    ("pure_en_starting", "Starting the refactoring process"),
    # Plan section with no completion
    ("plan_no_completion", "blah\n" * 10 + "\U0001f680 \u7acb\u5373\u884c\u52a8\n\u6211\u5c06\u91cd\u5199\u9a71\u52a8\u7a0b\u5e8f"),
]

SHOULD_NOT_CATCH = [
    # === Progress reports: completed work + next steps ===
    # These have completion language, so NOT a stall
    ("progress_cn", "\u6211\u5df2\u7ecf\u5b8c\u6210\u4e86 core/navigator.py \u7684\u91cd\u6784\u3002\n\u63a5\u4e0b\u6765\u6211\u8981\u5b9e\u73b0\u5750\u6807\u6821\u51c6\u903b\u8f91"),
    ("progress_en", "I've fixed the bug.\nNext, I'll update the tests"),
    ("progress_done_next", "Done with analysis.\nLet me start by fixing the parser"),
    ("progress_mixed", "\u5de5\u5177\u8fd4\u56de\u4e86\u7ed3\u679c\u3002\u95ee\u9898\u51fa\u5728\u6743\u9650\u914d\u7f6e\u4e0a\u3002"),
    # Real-world sample from user's log
    ("real_sample", "\u6211\u5df2\u7ecf\u5b8c\u6210\u4e86 core/navigator.py \u7684\u5f7b\u5e95\u91cd\u6784\u3002\n"
     "\u8fd9\u4e00\u6b21\uff0c\u6211\u4e0d\u662f\u5728\u201c\u4fee\u8865\u201d\u65e7\u4ee3\u7801\uff0c\u800c\u662f\u5728\u6839\u636e desktop-real-mouse-workflow \u6280\u80fd\u91cd\u65b0\u6784\u5efa\u3002\n"
     "\U0001f680 \u6838\u5fc3\u8fdb\u5316\u70b9\n"
     "\u6211\u5c06\u7acb\u5373\u5b9e\u73b0 real-mouse-coordinate-calibration \u903b\u8f91"),
    # === Genuine final answers ===
    ("final_en", "The answer is 42."),
    ("final_cn_summary", "\u603b\u7ed3\uff1a\u8fd9\u4e2a\u95ee\u9898\u662f\u7531\u4e8e\u6743\u9650\u4e0d\u8db3\u5bfc\u81f4\u7684\u3002"),
    ("final_done", "Done! The file has been updated."),
    ("final_cannot", "I cannot access the display server."),
    ("final_sorry", "\u62b1\u6b49\uff0c\u6211\u65e0\u6cd5\u5b8c\u6210\u8fd9\u4e2a\u4efb\u52a1\u3002"),
    ("final_ive_fixed", "I've fixed the bug and updated the tests."),
    ("final_cn_done", "\u5df2\u7ecf\u901a\u8fc7\u4fee\u6539 config \u89e3\u51b3\u4e86\u8fd9\u4e2a\u95ee\u9898\u3002"),
    ("long_summary", "Detailed analysis.\n" * 20 + "In summary, the root cause is X."),
    ("greeting", "Hello! How can I help you today?"),
    ("post_tool_en_done", "I've checked the output. Everything looks good now."),
    ("post_tool_the_issue", "The issue is in the config file, line 42."),
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
