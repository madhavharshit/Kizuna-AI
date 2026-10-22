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

def verification_refusal(response_language: str = "en") -> str:
    if response_language == "ja":
        return (
            "取得した資料では要求された技術情報を確認できませんでした。"
            "実際の承認済み手順書を確認するか、責任者に確認してください。"
            "値を推測しないでください。"
        )

    return (
        "I could not verify the requested technical information in the "
        "retrieved material. Check the actual approved procedure or ask "
        "the responsible supervisor. Do not guess the value."
    )

def grounded_answer(
    question: str,
    chunks: list,
    sources: list,
    response_language: str = "en",
):
    response_language = (
    "ja" if response_language == "ja" else "en"
    )
    language_name = (
    "Japanese" if response_language == "ja" else "English"
    )
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
            "answer": verification_refusal(response_language),
            "sources": [],
            "grounded": False
        }

    # Technical parameters that must not be guessed.
    critical_terms = [
        "torque", "トルク",
        "rpm", "回転数",
        "pressure", "圧力",
        "temperature", "温度",
        "voltage", "電圧",
        "current", "電流",
        "tolerance", "公差",
        "clearance", "クリアランス",
        "calibration", "校正",
        "operating limit", "運転限界",
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
            "answer": verification_refusal(response_language),
            "sources": sources,
            "grounded": False
        }

    if response_language == "ja":
        language_instruction = (
            "出力言語は日本語です。"
            "回答は自然で分かりやすい日本語だけで書いてください。"
            "英語の文章やフレーズを回答に混ぜないでください。"
            "英語の根拠資料は、日本語で要約してください。"
            "Step 1などの見出しを説明するのではなく、"
            "実際に行う作業内容を具体的に答えてください。"
        )
    else:
        language_instruction = (
            "Write the entire answer in clear, natural English. "
            "Do not mix in Japanese sentences. "
            "Explain the actual action, not merely a step label."
        )

    prompt = (
        "You are SkillBridge AR, a manufacturing training assistant.\n"
        f"{language_instruction}\n"
        "Use only the supplied evidence. "
        "Answer the user's actual question directly. "
        "Never invent technical values or safety instructions. "
        "If the evidence does not answer the question, say you cannot verify it. "
        "Keep the answer concise.\n\n"
        f"EVIDENCE:\n{context}\n\n"
        f"QUESTION: {question}\n\n"
        f"Write the final answer in {language_name}."
    )

    answer = ollama(prompt)

    if answer and response_language == "ja":
        cleanup_prompt = (
            "次の回答を、根拠資料に基づいて、"
            "自然で簡潔な日本語に書き直してください。\n"
            "英語の文章を混ぜないでください。"
            "質問に対する具体的な答えを直接述べてください。"
            "根拠にない情報を追加してはいけません。"
            "技術的な意味や安全上の注意を変更してはいけません。\n\n"
            f"質問:\n{question}\n\n"
            f"根拠資料:\n{context}\n\n"
            f"書き直す回答:\n{answer}\n\n"
            "日本語の回答本文だけを出力してください。"
        )

        cleaned_answer = ollama(cleanup_prompt)

        if cleaned_answer:
            answer = cleaned_answer.strip()

    if not answer:
        # Safe fallback if the local language model is unavailable.
        cleaned_passages = [
            re.sub(r"\s+", " ", c.text).strip()[:500]
            for c in chunks[:2]
        ]

        if response_language == "ja":
            fallback_message = (
                "ローカルAIモデルを利用できないため、"
                "回答を生成できませんでした。"
                "以下の資料を確認してください。"
            )
        else:
            fallback_message = (
                "I could not generate a complete answer because "
                "the local AI model is unavailable. "
                "Please review the retrieved source passages."
            )

        answer = (
            fallback_message
            + "\n\n"
            + "\n\n".join(cleaned_passages)
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

def draft_procedure(
    source_name: str,
    excerpts: list[dict],
    output_language: str = "en",
):
    language_name = (
        "Japanese" if output_language == "ja" else "English"
    )
    context = "\n".join(f"[{e['source_ref']}] {e['text']}" for e in excerpts)
    prompt = (f"Write all user-facing SOP field values in {language_name}. "
            "Keep JSON keys exactly in English: title, description, tools, "
            "warnings, steps, instruction, timestamp, source_ref. "
            "Translate the values of title, description, tools, warnings, and "
            "steps[].instruction into the requested language. "
            "Keep source_ref, filenames and timestamps unchanged. "
            "Use ONLY the source evidence; do not invent machine settings, "
            "operating limits, tools or safety claims. "
            "Unknown items must be listed in warnings as "
            "'Expert confirmation required'. "
            "Return valid JSON only.")
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
