import json, re
import requests
from .config import OLLAMA_URL, OLLAMA_MODEL

def ollama(prompt: str, json_mode: bool=False):
    """Uses local Ollama for zero API cost. Returns None if Ollama/model is unavailable."""
    try:
        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
        if json_mode: payload["format"] = "json"
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception:
        return None

def grounded_answer(question: str, chunks: list, sources: list):
    """
    Answer from uploaded sources only.
    Refuse specific technical questions when the required
    parameter is not present in the retrieved evidence.
    """

    context = "\n\n".join(
        re.sub(r"\s+", " ", c.text).strip()
        for c in chunks
    ).strip()

    # No source evidence was retrieved.
    if not context:
        return {
            "answer": (
                "I could not verify this in the uploaded material. "
                "Please upload a relevant manual or ask an expert."
            ),
            "sources": [],
            "grounded": False
        }

    # Technical parameters that must not be guessed.
    critical_terms = [
        "torque", "rpm", "pressure", "temperature",
        "voltage", "current", "tolerance", "clearance",
        "speed", "force", "power", "frequency",
        "calibration", "operating limit"
    ]

    # If a question asks for a specific parameter that
    # does not appear in the retrieved evidence, refuse.
    requested_terms = [
        term for term in critical_terms
        if re.search(r"\b" + re.escape(term) + r"\b",
                     question, re.IGNORECASE)
    ]

    missing_terms = [
        term for term in requested_terms
        if not re.search(r"\b" + re.escape(term) + r"\b",
                         context, re.IGNORECASE)
    ]

    if missing_terms:
        return {
            "answer": (
                "I could not verify the requested technical value "
                f"({', '.join(missing_terms)}) in the retrieved material. "
                "The uploaded sample manual states that it does not "
                "define machine-specific settings. Consult the actual "
                "approved procedure or ask the responsible supervisor. "
                "Do not guess the value."
            ),
            "sources": sources,
            "grounded": False
        }

    prompt = (
        "You are SkillBridge AR, a manufacturing training assistant. "
        "Answer ONLY using the supplied evidence. "
        "If the answer is missing, say you could not verify it. "
        "Never invent technical values or safety instructions. "
        "Keep the answer concise.\n\n"
        f"EVIDENCE:\n{context}\n\n"
        f"QUESTION: {question}"
    )

    answer = ollama(prompt)

    if not answer:
        # Safe fallback if the local language model is unavailable.
        cleaned_passages = [
            re.sub(r"\s+", " ", c.text).strip()[:500]
            for c in chunks[:2]
        ]

        answer = (
            "I could not generate a complete answer because the "
            "local AI model is unavailable. Retrieved source passages "
            "are provided for manual review."
            "\n\n" + "\n\n".join(cleaned_passages)
        )

    return {
        "answer": answer,
        "sources": sources,
        "grounded": True
    }

def fallback_steps(text: str, limit=8):
    # Conservative draft extraction. Human approval is still required before publishing.
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    cleaned = [s.strip(" -•\t") for s in sentences if len(s.strip()) > 25]
    return [{"instruction": s[:320], "timestamp": None, "source_ref": None} for s in cleaned[:limit]] or [{"instruction": "Review the original source and enter a verified step.", "timestamp": None, "source_ref": None}]

def draft_procedure(source_name: str, excerpts: list[dict]):
    context = "\n".join(f"[{e['source_ref']}] {e['text']}" for e in excerpts)
    prompt = ("Create a DRAFT manufacturing SOP using ONLY the evidence below. Do not invent machine settings, "
              "limits, tools, or safety claims. Unknown items must be listed in warnings as 'Expert confirmation required'. "
              "Return JSON with keys title, description, tools (array), warnings (array), steps (array of objects with instruction, timestamp, source_ref). "
              "Each step must cite a source_ref. The result is a draft requiring human review.\n\n"
              f"SOURCE: {source_name}\nEVIDENCE:\n{context}")
    raw = ollama(prompt, json_mode=True)
    if raw:
        try:
            obj = json.loads(raw)
            if isinstance(obj.get("steps"), list) and obj["steps"]:
                obj.setdefault("title", f"Draft procedure — {source_name}")
                obj.setdefault("description", "AI-generated draft. Expert validation required.")
                obj.setdefault("tools", [])
                obj.setdefault("warnings", [])
                for i, step in enumerate(obj["steps"]):
                    step.setdefault("timestamp", None)
                    step.setdefault("source_ref", excerpts[min(i, len(excerpts)-1)]["source_ref"] if excerpts else source_name)
                if not obj["warnings"]: obj["warnings"] = ["Expert confirmation required for safety, tools and operating limits."]
                return obj
        except Exception: pass
    joined = "\n".join(e["text"] for e in excerpts)
    steps = fallback_steps(joined)
    for i, step in enumerate(steps):
        ref = excerpts[min(i, len(excerpts)-1)] if excerpts else {"timestamp":None,"source_ref":source_name}
        step["timestamp"] = ref.get("timestamp")
        step["source_ref"] = ref.get("source_ref", source_name)
    return {"title": f"Draft procedure — {source_name}", "description": "Conservative draft from source text. Expert validation required.", "tools": [], "warnings": ["AI draft is not an approved safety procedure.", "Expert must verify all steps, tools, values and cautions."], "steps": steps}
