import json
import sys

from app.vectorstore import query_policy_chunks
from app.routers_compliance import classify_context_with_llm
from app.agent_graph import analyze_and_rewrite


def handle_policy_search(params):
    matches = query_policy_chunks(
        query=params["query"],
        top_k=params.get("top_k", 5),
        filters=params.get("filters"),
    )

    # Make it JSON-safe
    return [
        {
            "score": m.score,
            "metadata": m.metadata,
        }
        for m in matches
    ]


def handle_context_classify(params):
    department, policy_type = classify_context_with_llm(params["text"])
    return {
        "department": department,
        "policy_type": policy_type.value if policy_type else None,
    }


def handle_compliance_analyze(params):
    # Reuse your existing logic by emulating graph state
    state = {
        "text": params["text"],
        "context_text": params.get("context_text", ""),
    }

    new_state = analyze_and_rewrite(state)
    return new_state["response"]


TOOLS = {
    "policy.search": handle_policy_search,
    "context.classify": handle_context_classify,
    "compliance.analyze": handle_compliance_analyze,
}


def handle_request(req):
    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params", {})

    if method not in TOOLS:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Unknown method {method}",
            },
        }

    try:
        result = TOOLS[method](params)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result,
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32000,
                "message": str(e),
            },
        }


def main():
    for line in sys.stdin:
        if not line.strip():
            continue

        req = json.loads(line)
        resp = handle_request(req)
        print(json.dumps(resp), flush=True)


if __name__ == "__main__":
    main()
