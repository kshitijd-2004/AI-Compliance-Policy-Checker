from typing import Optional, List, Any
from typing_extensions import TypedDict

from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import OpenAI
from langgraph.graph import StateGraph, END

from app import schemas
from app.models import PolicyType
from app.vectorstore import query_policy_chunks


# ---------- Settings for LLM ----------

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
    # input
    text: str
    department: Optional[str]
    policy_type: Optional[PolicyType]
    top_k: int

    # intermediate
    matches: List[Any]
    context_text: str

    # final output (as plain dict so it’s JSON-able)
    response: dict


# ---------- Node 1: retrieve policies from Pinecone ----------

def retrieve_policies(state: ComplianceState) -> ComplianceState:
    text = state["text"]
    department = state.get("department")
    policy_type = state.get("policy_type")
    top_k = state.get("top_k", 5)

    # Build filters same as before
    filters: dict[str, Any] = {}
    if department:
        filters["department"] = department
    if policy_type:
        # Stored as string in metadata
        filters["policy_type"] = policy_type.value

    matches = query_policy_chunks(
        query=text,
        top_k=top_k,
        filters=filters or None,
    )

    # Build context snippets (assumes query_policy_chunks returns Pinecone matches
    # with .metadata; if yours returns just IDs, adapt this to fetch from DB).
    context_snippets: List[str] = []
    for m in matches:
        meta = getattr(m, "metadata", None) or m.get("metadata", {})
        snippet = (
            f"[doc_id={meta.get('document_id')}, "
            f"chunk_id={meta.get('chunk_id')}] "
            f"{meta.get('text', '')}"
        )
        context_snippets.append(snippet)

    context_text = "\n\n".join(context_snippets)

    return {
        **state,
        "matches": matches,
        "context_text": context_text,
    }


# ---------- Node 2: analyze + rewrite via LLM ----------

def analyze_and_rewrite(state: ComplianceState) -> ComplianceState:
    text = state["text"]
    context_text = state.get("context_text", "")

    # If no context, still try to answer but likely "NONE" risk
    prompt = f"""
You are a compliance assistant. Given:

1) The user's text (draft message)
2) Relevant policy excerpts (may be empty)

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

    # Parse into your existing Pydantic schema, then dump back to plain dict
    resp_model = schemas.ComplianceCheckResponse.model_validate_json(raw_json)
    resp_dict = resp_model.model_dump()

    return {
        **state,
        "response": resp_dict,
    }


# ---------- Build & export the graph ----------

def build_compliance_graph():
    graph = StateGraph(ComplianceState)

    graph.add_node("retrieve_policies", retrieve_policies)
    graph.add_node("analyze_and_rewrite", analyze_and_rewrite)

    graph.set_entry_point("retrieve_policies")
    graph.add_edge("retrieve_policies", "analyze_and_rewrite")
    graph.add_edge("analyze_and_rewrite", END)

    return graph.compile()


# Single compiled app you can import elsewhere
compliance_app = build_compliance_graph()
