#!/usr/bin/env python3
"""
backend/scripts/test_assistant.py
End-to-end test for /api/assistant/chat SSE endpoint.
Tests 5 sample questions, parses SSE events, verifies required event types.

Run standalone (no pytest):
    python backend/scripts/test_assistant.py

Requires backend running at http://localhost:8100
"""

from __future__ import annotations

import json
import sys
import urllib.request
from dataclasses import dataclass, field


BASE_URL = "http://localhost:8100"

TEST_CASES = [
    {
        "name": "Giấy phép xây dựng",
        "message": "Tôi muốn xây nhà 3 tầng ở Cầu Giấy, cần làm thủ tục gì?",
        "context": {"type": "portal"},
        "expect_event_types": {"text_delta", "done"},
    },
    {
        "name": "Lý lịch tư pháp",
        "message": "Xin lý lịch tư pháp cần những giấy tờ gì?",
        "context": {"type": "portal"},
        "expect_event_types": {"text_delta", "done"},
    },
    {
        "name": "Tra cứu hồ sơ",
        "message": "Tra cứu hồ sơ HS-20260414-ABC12345",
        "context": {"type": "portal"},
        "expect_event_types": {"text_delta", "done"},
    },
    {
        "name": "Giấy tờ cần thiết GCNQSDĐ",
        "message": "Hồ sơ đăng ký giấy chứng nhận quyền sử dụng đất gồm những gì?",
        "context": {"type": "portal"},
        "expect_event_types": {"text_delta", "done"},
    },
    {
        "name": "Quy trình cấp phép xây dựng",
        "message": "Quy trình xem xét cấp giấy phép xây dựng mất bao lâu?",
        "context": {"type": "submit", "ref": "1.004415"},
        "expect_event_types": {"text_delta", "done"},
    },
]


@dataclass
class TestResult:
    name: str
    passed: bool
    events_received: list[str] = field(default_factory=list)
    error: str | None = None
    session_id: str | None = None


def parse_sse(raw: bytes) -> list[dict]:
    """Parse SSE response bytes into list of JSON event dicts."""
    events = []
    for line in raw.decode("utf-8").splitlines():
        line = line.strip()
        if line.startswith("data: "):
            data_str = line[6:].strip()
            if data_str:
                try:
                    events.append(json.loads(data_str))
                except json.JSONDecodeError:
                    pass
    return events


def run_chat(
    message: str, context: dict, session_id: str | None = None
) -> tuple[list[dict], str | None]:
    """POST to /api/assistant/chat and collect all SSE events."""
    payload = json.dumps(
        {
            "message": message,
            "context": context,
            "session_id": session_id,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/api/assistant/chat",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()

    events = parse_sse(raw)
    new_session_id = None
    for e in events:
        if e.get("type") == "session":
            new_session_id = e.get("session_id")
            break

    return events, new_session_id


def run_test(tc: dict) -> TestResult:
    result = TestResult(name=tc["name"], passed=False)
    try:
        events, session_id = run_chat(tc["message"], tc["context"])
        result.session_id = session_id
        result.events_received = [e.get("type", "unknown") for e in events]

        event_types_got = set(result.events_received)
        missing = tc["expect_event_types"] - event_types_got

        if missing:
            result.error = f"Missing expected event types: {missing}. Got: {event_types_got}"
            return result

        # Verify done event has content
        done_events = [e for e in events if e.get("type") == "done"]
        if not done_events:
            result.error = "No 'done' event received"
            return result

        done = done_events[-1]
        if not done.get("content") and not done.get("message_id"):
            result.error = "Done event missing content/message_id"
            return result

        result.passed = True
        return result

    except Exception as e:
        result.error = str(e)
        return result


def run_intent_test() -> TestResult:
    result = TestResult(name="Intent Classification", passed=False)
    try:
        payload = json.dumps(
            {"text": "Xây nhà mới 3 tầng cần giấy tờ gì?"},
            ensure_ascii=False,
        ).encode("utf-8")

        req = urllib.request.Request(
            f"{BASE_URL}/api/assistant/intent",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        if "explanation" not in data:
            result.error = f"Missing 'explanation' in response: {data}"
            return result

        result.passed = True
        result.events_received = [f"confidence={data.get('primary_confidence', 0):.2f}"]
        return result

    except Exception as e:
        result.error = str(e)
        return result


def run_law_chunk_test() -> TestResult:
    """Smoke-test GET /api/search/law/chunk/{chunk_id} with a fake UUID.

    Expects either:
      - 404 JSON with detail "Không tìm thấy điều khoản"  (no seed data)
      - 200 JSON with chunk_id, law_id, content fields     (seed data present)
    Either outcome proves the endpoint is wired and reachable.
    """
    result = TestResult(name="LawChunk endpoint smoke test", passed=False)
    fake_id = "00000000-0000-0000-0000-000000000001"
    url = f"{BASE_URL}/api/search/law/chunk/{fake_id}"

    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        # 200 → seed data present, validate fields
        required_fields = {"chunk_id", "law_id", "content", "article_number"}
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            result.error = f"200 response missing fields: {missing_fields}"
            return result
        result.events_received = [f"chunk_id={data.get('chunk_id', '')[:8]}..."]
        result.passed = True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            body = json.loads(e.read())
            if body.get("detail") == "Không tìm thấy điều khoản":
                result.events_received = ["404 with correct Vietnamese message"]
                result.passed = True
            else:
                result.error = f"404 but wrong detail: {body}"
        else:
            result.error = f"HTTP {e.code}: {e.reason}"
    except Exception as exc:
        result.error = str(exc)

    return result


def main():
    print(f"Testing assistant API at {BASE_URL}\n")
    print("=" * 60)

    results: list[TestResult] = []

    # Test law chunk endpoint (new smoke test)
    print("Running law chunk endpoint smoke test...")
    r = run_law_chunk_test()
    results.append(r)
    status = "PASS" if r.passed else "FAIL"
    print(f"  [{status}] {r.name}")
    if r.events_received:
        print(f"         {r.events_received}")
    if r.error:
        print(f"         ERROR: {r.error}")

    print()

    # Test intent endpoint first (quick smoke test)
    print("Running intent classification test...")
    r = run_intent_test()
    results.append(r)
    status = "PASS" if r.passed else "FAIL"
    print(f"  [{status}] {r.name}")
    if r.events_received:
        print(f"         {r.events_received}")
    if r.error:
        print(f"         ERROR: {r.error}")

    # Test chat SSE
    session_id = None
    for tc in TEST_CASES:
        print(f"\nRunning: {tc['name']}...")
        # Reuse session for continuity test (first 3 share session)
        if tc == TEST_CASES[0]:
            tc_result = run_test(tc)
            session_id = tc_result.session_id
        elif tc in TEST_CASES[1:3] and session_id:
            tc_copy = {**tc}
            r2 = TestResult(name=tc["name"], passed=False)
            try:
                events, _ = run_chat(tc["message"], tc["context"], session_id)
                r2.events_received = [e.get("type", "?") for e in events]
                event_types_got = set(r2.events_received)
                missing = tc["expect_event_types"] - event_types_got
                r2.passed = not missing
                if missing:
                    r2.error = f"Missing: {missing}"
            except Exception as e:
                r2.error = str(e)
            tc_result = r2
        else:
            tc_result = run_test(tc)

        results.append(tc_result)
        status = "PASS" if tc_result.passed else "FAIL"
        print(f"  [{status}] {tc_result.name}")
        print(f"         Events: {tc_result.events_received[:8]}")
        if tc_result.error:
            print(f"         ERROR: {tc_result.error}")

    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"Results: {passed}/{total} passed")

    if passed < total:
        print("\nFailed tests:")
        for r in results:
            if not r.passed:
                print(f"  - {r.name}: {r.error}")
        sys.exit(1)
    else:
        print("All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
