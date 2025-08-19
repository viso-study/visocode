import json

from smolagents import Tool
from smolagents.agents import ChatMessage


class Enhanced3Blue1BrownFinalAnswerTool(Tool):
    name = "final_answer"
    description = (
        "Create a concise final JSON answer (2–4 sentences) and a small visual_brief (1–3 icon ideas). "
        "Takes prior tool output; no icon generation here."
    )
    inputs = {
        "question": {"type": "string", "description": "The user's original question"},
        "result": {"type": "string", "description": "Concatenated results from previous tools"},
    }
    output_type = "string"

    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, question: str, result: str) -> str:
        system = ChatMessage(
            role="system",
            content=(
                "You are a precise educator channeling a 3Blue1Brown explanation style.\n"
                "- Write a self-contained explanation in 100–250 words.\n"
                "- Lead with the core idea, then build intuition using 1–2 concrete visual cues "
                "(e.g., 'imagine sliding along the curve', 'area under the graph', 'vectors rotating').\n"
                "- Use stepwise reasoning, tiny examples, and invariants; bring in equations only when they anchor the intuition.\n"
                "- Avoid fluff and flowery metaphors; keep visuals geometric and operational.\n"
                "- After the explanation, propose a minimal visual plan: 1–3 concise icon ideas with short captions suitable as thumbnails/diagram elements.\n"
            ),
        )

        user = ChatMessage(
            role="user",
            content=(
                f"QUESTION:\n{question}\n\n"
                f"CONTEXT FROM TOOLS:\n{result}\n\n"
                "Respond strictly as JSON with keys:\n"
                "  - explanation.content  (100–250 words, naturally weaving visual intuition; define any jargon briefly)\n"
                "  - visual_brief         (array of 1–3 items, each {concept, caption} for icons/diagrams)\n"
                "Guidelines:\n"
                "  • Prioritize geometric/graph insight; keep algebra minimal but precise.\n"
                "  • Use a tiny concrete example if it clarifies the main idea.\n"
                "  • Keep the visual_brief practical for icon generation (short, specific, no prose blocks).\n"
            ),
        )
        resp = self.model([system, user])
        raw = (resp.content or "").strip()

        # Try to parse JSON straight from the model (robust fallback below)
        explanation = ""
        visual_brief = []

        try:
            obj = json.loads(raw)
            explanation = (obj.get("explanation", {}) or {}).get("content", "") or ""
            vb = obj.get("visual_brief", []) or []
            if isinstance(vb, list):
                visual_brief = [
                    {"concept": (x.get("concept") or "").strip(), "caption": (x.get("caption") or "").strip()}
                    for x in vb if isinstance(x, dict)
                ]
        except Exception:
            # Fallback: treat model output as plain text; take first 2–4 sentences,
            # plus a tiny heuristic for bullet lines as concepts.
            explanation = raw.split("\n\n")[0]
            # Simple extraction of lines starting with '-', '*', or numbered
            lines = [ln.strip("-* ").strip() for ln in raw.splitlines() if ln.strip().startswith(("-", "*"))]
            for ln in lines[:3]:
                visual_brief.append({"concept": ln.split(":")[0][:40], "caption": (":".join(ln.split(":")[1:]) or ln)[:80]})

        out = {
            "question": question,
            "explanation": {"content": explanation},
            "visual_brief": visual_brief[:3],
            "visual_assets": {"icons": []},
        }
        return json.dumps(out, ensure_ascii=False)
