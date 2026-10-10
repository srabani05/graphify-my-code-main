"""Smoke test: extract -> build -> query over the sample repos."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = ROOT / ".venv" / "bin" / "python"
DATA = ROOT / ".test-data"
DB = ROOT / ".test.kuzu"


def run(*args):
    r = subprocess.run([str(PY), "-m", "codegraph.cli", *args],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        print("CMD FAILED:", args)
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
        sys.exit(1)
    return r.stdout


def main():
    shutil.rmtree(DATA, ignore_errors=True)
    shutil.rmtree(DB, ignore_errors=True)
    (ROOT / ".test.kuzu.unresolved.jsonl").unlink(missing_ok=True)

    print("== extract ==")
    run("extract", "--repos", str(ROOT / "tests/sample/javarepo"),
        str(ROOT / "tests/sample/pyrepo"), "--out", str(DATA), "--workers", "2")
    print("== build ==")
    out = run("build", "--data", str(DATA), "--db", str(DB))
    counts = json.loads(out)
    print(json.dumps(counts, indent=2))
    assert counts["entities"] > 10, counts
    assert counts["CALLS"] >= 4, counts  # cross-file calls must resolve

    print("== query: callers of PaymentService.charge ==")
    out = run("query", "callers", "com.example.service.PaymentService.charge",
              "--db", str(DB), "--depth", "1")
    callers = json.loads(out)
    print(json.dumps(callers, indent=2))
    assert any("OrderService.processOrder" in c["qualified"] for c in callers), callers

    print("== query: trace OrderService.processOrder -> PaymentService.charge ==")
    out = run("query", "trace", "com.example.service.OrderService.processOrder",
              "com.example.service.PaymentService.charge", "--db", str(DB))
    print(out.strip())
    assert "PaymentService.charge" in out

    print("== query: impact of Validator.check ==")
    out = run("query", "impact", "com.example.util.Validator.check",
              "--db", str(DB), "--depth", "3")
    assert "OrderService" in out, out

    print("== query: python cross-module call ==")
    out = run("query", "callers", "billing.pricing.calc_total", "--db", str(DB))
    assert "shop.cart.Cart.checkout" in out, out

    print("== context ==")
    out = run("context", "com.example.service.OrderService.processOrder", "--db", str(DB))
    assert "payments.charge" in out and "```" in out, out[:500]
    print(out[:400])

    print("== spring: endpoints ==")
    out = run("cypher", "MATCH (e:Entity) WHERE e.kind='endpoint' "
              "RETURN e.qualified AS ep ORDER BY ep", "--db", str(DB))
    print(out.strip())
    assert "POST /api/orders" in out and "GET /api/orders/{id}" in out, out

    print("== mybatis: tables ==")
    out = run("cypher", "MATCH (t:Entity) WHERE t.kind='table' "
              "RETURN t.qualified AS tbl", "--db", str(DB))
    assert "orders" in out, out

    print("== jms: queue flow ==")
    out = run("cypher", "MATCH (m:Entity)-[:SENDS]->(q:Entity {kind:'queue'}) "
              "RETURN m.qualified AS sender, q.qualified AS q", "--db", str(DB))
    assert "OrderController.create" in out and "order.events" in out, out
    out = run("cypher", "MATCH (m:Entity)-[:LISTENS]->(q:Entity {kind:'queue'}) "
              "RETURN m.qualified AS listener, q.qualified AS q", "--db", str(DB))
    assert "OrderEvents.onOrderEvent" in out, out

    print("\nSMOKE OK")


if __name__ == "__main__":
    main()
