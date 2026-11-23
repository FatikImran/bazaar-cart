"""Exercise the deployed grader endpoints against the seeded catalog."""
import argparse
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


def run_case(url, case, run_id):
    payload = {
        "user_id": f"{run_id}-{case['user']}",
        "thread_id": case["thread"],
        "message": case["message"],
    }
    request = Request(f"{url}/chat", data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json"})
    start = time.monotonic()
    try:
        with urlopen(request, timeout=65) as response:
            data = json.load(response)
        reply = data["reply"].casefold()
        names = {call["name"] for call in data["tool_calls"]}
        tokens = data["tokens"]
        passed = (all(term.casefold() in reply for term in case.get("contains", []))
                  and case.get("tool", "") in names | {""}
                  and case.get("forbid_tool") not in names
                  and set(tokens) == {"in", "out"}
                  and all(type(value) is int and value >= 0 for value in tokens.values()))
        return {"id": case["id"], "passed": passed, "reply": data["reply"],
                "tools": sorted(names), "tokens": tokens, "seconds": round(time.monotonic() - start, 2)}
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
        return {"id": case["id"], "passed": False, "error": str(exc)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Live agent API URL")
    url = parser.parse_args().base_url.rstrip("/")
    with urlopen(f"{url}/health", timeout=65) as response:
        if response.read() != b"ok":
            raise SystemExit("Health check failed")
    spec = json.loads((Path(__file__).parent / "tests.json").read_text())
    run_id = uuid4().hex
    results = [run_case(url, case, run_id) for case in spec["cases"] + spec["safety_cases"]]
    passed = sum(result["passed"] for result in results)
    report = {"passed": passed, "total": len(results), "cases": results}
    Path("benchmark-results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for result in results:
        print(f"{result['id']}: {'PASS' if result['passed'] else 'FAIL'}")
    print(f"{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
