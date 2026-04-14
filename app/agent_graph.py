from __future__ import annotations

import json
from typing import Any

from typing_extensions import TypedDict
from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import OpenAI
from langgraph.graph import StateGraph, END

from app import schemas
from app.models import PolicyType
from app.vectorstore import query_policy_chunks


# ---------- Settings ----------

class LLMSettings(BaseSettings):
    OPENAI_API_KEY: str

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
    )


llm_settings = LLMSettings()
llm_client = OpenAI(api_key=llm_settings.OPENAI_API_KEY)


# ---------- Graph state ----------

class ComplianceState(TypedDict, total=False):
    text: str
    department: str | None
    policy_type: PolicyType | None
    top_k: int

    # set by classify node
    inferred_department: str | None
    inferred_policy_type: PolicyType | None

    # set by retrieve node
    matches: list[Any]
    context_text: str

    # final output
    response: dict[str, Any]


# ---------- Node 1: classify content ----------

def classify_content(state: ComplianceState) -> ComplianceState:
    """Use the LLM to infer department and policy_type when not supplied."""
    department = state.get("department")
    policy_type = state.get("policy_type")

    if department and policy_type:
        return {
            **state,
            "inferred_department": department,
            "inferred_policy_type": policy_type,
        }

    prompt = f"""You are a classifier for an AI compliance system.

Given a piece of text, infer:
- which department it most likely belongs to (e.g. "Sales", "Support", "HR", "Legal", "Marketing")
- which policy_type applies, from this fixed list:
  ["confidentiality", "external_communication", "data_privacy", "security", "hr"]

If you are unsure about a field, set it to null.

Return ONLY a JSON object:
{{
  "department": "<department or null>",
  "policy_type": "<policy_type or null>"
}}

Text:
\"\"\"{state['text']}\"\"\""""

    completion = llm_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You classify text into department and policy_type for compliance checks."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    data = json.loads(completion.choices[0].message.content or "{}")

    inferred_dept = department or data.get("department")
    inferred_pt_str = data.get("policy_type") if not policy_type else None
    inferred_pt: PolicyType | None = policy_type
    if inferred_pt_str and not inferred_pt:
        try:
            inferred_pt = PolicyType(inferred_pt_str)
        except ValueError:
            inferred_pt = None

    return {
        **state,
        "inferred_department": inferred_dept,
        "inferred_policy_type": inferred_pt,
    }


# ---------- Node 2: retrieve policies from Pinecone ----------

def retrieve_policies(state: ComplianceState) -> ComplianceState:
    text = state["text"]
    department = state.get("inferred_department") or state.get("department")
    policy_type = state.get("inferred_policy_type") or state.get("policy_type")
    top_k = state.get("top_k", 5)

    filters: dict[str, Any] = {}
    if department:
        filters["department"] = department
    if policy_type:
        filters["policy_type"] = policy_type.value if isinstance(policy_type, PolicyType) else policy_type

    matches = query_policy_chunks(
        query=text,
        top_k=top_k,
        filters=filters or None,
    )

    context_snippets: list[str] = []
    for m in matches:
        meta = getattr(m, "metadata", None) or m.get("metadata", {})
        snippet = (
            f"[doc_id={meta.get('document_id')}, "
            f"chunk_id={meta.get('chunk_id')}] "
            f"{meta.get('text', '')}"
        )
        context_snippets.append(snippet)

    return {
        **state,
        "matches": matches,
        "context_text": "\n\n".join(context_snippets),
    }


# ---------- Routing: skip LLM if no context retrieved ----------

def route_after_retrieval(state: ComplianceState) -> str:
    """Conditional edge: if retrieval found no matches, skip the LLM call."""
    if state.get("matches"):
        return "analyze_and_rewrite"
    return "no_context_response"


# ---------- Node 3a: analyze + rewrite via LLM ----------

def analyze_and_rewrite(state: ComplianceState) -> ComplianceState:
    text = state["text"]
    context_text = state.get("context_text", "")

    prompt = f"""You are a compliance assistant. Given:

1) The user's text (draft message)
2) Relevant policy excerpts

Decide:
- overall_risk: one of ["NONE", "LOW", "MEDIUM", "HIGH"]
- issues: list (possibly empty) of:
  - type (e.g. "Confidentiality", "External Communication", "Data Privacy")
  - policy_reference (if you can infer it from the excerpt, otherwise null)
  - excerpt (the risky part of the user text)
  - explanation (why it is a problem)

Then propose a fully rewritten version of the text that is compliant.

Return ONLY a JSON object with this structure:

{{
  "overall_risk": "LOW",
  "issues": [
    {{
      "type": "Confidentiality",
      "policy_reference": "Security Policy §3.2",
      "excerpt": "some text from the user message",
      "explanation": "short explanation"
    }}
  ],
  "suggested_text": "rewritten compliant text"
}}

User text:
\"\"\"{text}\"\"\"

Policy context:
\"\"\"{context_text}\"\"\""""

    completion = llm_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a strict compliance reviewer."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    raw_json = completion.choices[0].message.content
    resp_model = schemas.ComplianceCheckResponse.model_validate_json(raw_json or "{}")

    return {
        **state,
        "response": resp_model.model_dump(),
    }


# ---------- Node 3b: no-context fallback ----------

def no_context_response(state: ComplianceState) -> ComplianceState:
    """When no policy chunks match, return a clean result without calling the LLM."""
    resp = schemas.ComplianceCheckResponse(
        overall_risk="NONE",
        issues=[],
        suggested_text=None,
    )
    return {
        **state,
        "response": resp.model_dump(),
    }


# ---------- Build & export the graph ----------

def build_compliance_graph():
    graph = StateGraph(ComplianceState)

    graph.add_node("classify_content", classify_content)
    graph.add_node("retrieve_policies", retrieve_policies)
    graph.add_node("analyze_and_rewrite", analyze_and_rewrite)
    graph.add_node("no_context_response", no_context_response)

    graph.set_entry_point("classify_content")
    graph.add_edge("classify_content", "retrieve_policies")

    graph.add_conditional_edges(
        "retrieve_policies",
        route_after_retrieval,
        {
            "analyze_and_rewrite": "analyze_and_rewrite",
            "no_context_response": "no_context_response",
        },
    )

    graph.add_edge("analyze_and_rewrite", END)
    graph.add_edge("no_context_response", END)

    return graph.compile()


compliance_app = build_compliance_graph()
