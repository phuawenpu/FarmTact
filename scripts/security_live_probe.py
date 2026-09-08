"""Bounded, unauthenticated release probes; never submit a valid inference job."""
import json
from pathlib import Path

import httpx


def main():
    report = {"status": "RUNNING", "base_url": "https://farmtact.fly.dev", "checks": [], "valid_inference_jobs_submitted": 0}

    def check(name, passed, **evidence):
        report["checks"].append({"name": name, "pass": bool(passed), **evidence})
        if not passed:
            raise AssertionError(name)

    try:
        with httpx.Client(base_url=report["base_url"], timeout=30, follow_redirects=False) as client:
            check("Fly health is available", client.get("/api/v1/health").status_code == 200)
            for path in ("/openapi.json", "/docs", "/redoc", "/v1/chat/completions", "/api/v1/deepseek"):
                response = client.get(path)
                check(f"No public schema or generic provider proxy at {path}", response.status_code == 404)
            response = client.post("/api/v1/imports", json={}, headers={"Origin": "https://untrusted.invalid"})
            check("Cross-origin writes are rejected", response.status_code == 403)
            statuses = []
            # Rotate caller-supplied IP and cookies: neither is a trusted identity.
            for index in range(7):
                response = client.post(
                    "/api/v1/conversations/nonexistent-security-probe/messages",
                    json={"content": "Unauthenticated security probe; no job may be created."},
                    headers={"X-Forwarded-For": f"203.0.113.{index + 1}", "Cookie": f"farmtact_session=invalid-probe-{index}"},
                )
                statuses.append(response.status_code)
            check("Rotating XFF and invalid cookies cannot evade the AI IP limit", statuses == [401] * 6 + [429], statuses=statuses)
            check("Rate denial includes a bounded Retry-After", 1 <= int(response.headers.get("Retry-After", "0")) <= 60)
            response = client.post(
                "/api/v1/conversations/nonexistent-security-probe/messages",
                json={"content": "No job may be created."},
                headers={"Fly-Client-IP": "198.51.100.42", "X-Forwarded-For": "198.51.100.42"},
            )
            check("Forging Fly client identity cannot reopen the allowance", response.status_code in {400, 429}, status=response.status_code)
            check("Read-only health remains available after AI throttling", client.get("/api/v1/health").status_code == 200)
        report["status"] = "PASS"
    except Exception as error:
        report["status"] = "FAIL"
        report["error"] = type(error).__name__ + ": " + str(error)
        raise
    finally:
        Path("reports/security_live_probe.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))


if __name__ == "__main__":
    main()
