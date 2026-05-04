"""
Quick live pipeline test script.
Registers a throwaway user, creates campaign + product, starts a pipeline run,
and streams the SSE output logging each agent_complete event.
"""
import json
import sys
import time
import httpx

BASE = "http://localhost:8000"
EMAIL = f"pipetest_{int(time.time())}@test.com"
PASSWORD = "testpass123"


def main():
    with httpx.Client(timeout=300) as c:
        # 1. Register
        c.post(f"{BASE}/auth/register", json={"email": EMAIL, "password": PASSWORD})

        # 2. Login
        r = c.post(f"{BASE}/auth/login", data={"username": EMAIL, "password": PASSWORD})
        r.raise_for_status()
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Create campaign
        r = c.post(f"{BASE}/campaigns", json={"name": "PipelineTest"}, headers=headers)
        r.raise_for_status()
        campaign_id = r.json()["id"]

        # 4. Create product with description
        product_payload = {
            "name": "VitaGreens Pro",
            "description": (
                "VitaGreens Pro is a premium all-in-one superfood powder packed with 50+ superfoods, "
                "adaptogens, and probiotics. It boosts energy, immunity, and gut health with no artificial "
                "flavors, vegan, gluten-free. Designed for ambitious professionals aged 25-45 who want "
                "peak performance from a clean, convenient daily supplement. "
                "Unit cost: $18.00."
            ),
            "unit_cost_usd": 18.0,
        }
        r = c.post(
            f"{BASE}/campaigns/{campaign_id}/products",
            json=product_payload,
            headers=headers,
        )
        r.raise_for_status()
        product_id = r.json()["id"]

        print(f"Campaign: {campaign_id}")
        print(f"Product:  {product_id}")
        print("Starting pipeline...")

        # 5. Start generation and stream SSE
        gen_payload = {
            "campaign_id": campaign_id,
            "product_id": product_id,
            "target_channel": "meta",
        }

        agent_results: dict[str, dict] = {}
        start = time.monotonic()

        with c.stream(
            "POST",
            f"{BASE}/generate",
            json=gen_payload,
            headers={**headers, "Accept": "text/event-stream"},
        ) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if not raw_line.startswith("data:"):
                    continue
                payload_str = raw_line[5:].strip()
                try:
                    payload = json.loads(payload_str)
                except json.JSONDecodeError:
                    continue

                event_type = payload.get("event", "?")
                agent = payload.get("agent", "?")
                data = payload.get("data", {})
                elapsed = time.monotonic() - start

                if event_type == "agent_complete":
                    # data may be empty dict for zero-output agents
                    out_len = len(json.dumps(data)) if data else 0
                    progress = payload.get("progress", "?")
                    total = payload.get("total", "?")
                    print(
                        f"  [{elapsed:5.1f}s] COMPLETE  {agent:<40}  data_len={out_len}  "
                        f"progress={progress}/{total}"
                    )
                    agent_results[agent] = {"out_len": out_len, "elapsed": elapsed}

                elif event_type in ("done", "pipeline_complete"):
                    print(f"\n  [{elapsed:5.1f}s] {event_type.upper()}")

                elif event_type == "error":
                    msg = data.get("message", str(data))
                    print(f"  [{elapsed:5.1f}s] ERROR  agent={agent}: {msg}")

                elif event_type == "started":
                    ad_id = payload.get("advertisement_id", "?")
                    print(f"  [{elapsed:5.1f}s] STARTED  ad={ad_id}")

        # Summary
        print("\n=== Summary ===")
        zero_out = [(a, v) for a, v in agent_results.items() if v["out_len"] == 0]
        if zero_out:
            print("ZERO OUTPUT agents:")
            for a, v in zero_out:
                print(f"  - {a}  in={v['in']}")
        else:
            print("All agents produced output.")

        print(f"\nAgents completed: {len(agent_results)}")


if __name__ == "__main__":
    main()
