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
    context = "\n\n".join(f"[{i+1}] {c.text}" for i,c in enumerate(chunks))
    prompt = ("You are SkillBridge AR, a manufacturing training assistant. Answer ONLY from the context. "
              "If the context does not contain the answer, say 'I could not verify this in the uploaded material. Ask an expert.' "
              "Do not invent safety procedures, values, torque settings or machine states. Keep answer concise.\n\n"
              f"CONTEXT:\n{context}\n\nQUESTION: {question}")
    answer = ollama(prompt) if context else None
    if not context:
        answer = "I could not verify this in the uploaded material. Upload a relevant manual or video, or ask an expert."
    elif not answer:
        # No LLM installed? Safely quote retrieved evidence rather than fabricate a generated answer.
        answer = "I found these relevant passages in the uploaded material. Please review the cited source before acting:\n\n" + "\n\n".join(f"• {c.text[:650]}" for c in chunks[:3])
    return {"answer": answer, "sources": sources, "grounded": bool(context)}

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
