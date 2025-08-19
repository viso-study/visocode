import json
import os
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class StepPlan:
    idx: int
    tool: str
    reason: str
    args: Optional[dict] = None


class GuardrailedMultiToolAgent:
    """
    Deterministic, safe pipeline with multiple Step-1 tools allowed.

      Step 0 — ask_clarification (only if crucial)
      Step 1 — Run a PRE-PLANNED set of analysis tools (0..n of):
               • code_analysis if a code path is present
               • sympy if the query looks like math (skip arxiv for trivial arithmetic)
               • arxiv_search ON by default for non-code, non-trivial-math queries
      Step 2 — final_answer (100–250 words + visual_brief)
      Step 3 — icon_generation decided AFTER final_answer based on:
               • user request (explicit visuals), OR
               • final JSON (non-empty visual_brief, or visual language in explanation)
    """

    def __init__(self, tools, model):
        self.tool_map = {t.name: t for t in tools}
        self.model = model

    # ---------------- Heuristics ----------------
    @staticmethod
    def _extract_code_path(text: str) -> Optional[str]:
        m = re.search(r"Please analyze the code file '([^']+)'", text)
        return m.group(1) if m else None

    @staticmethod
    def _looks_like_math(text: str) -> bool:
        math_keywords = [
            "integrate", "differentiate", "solve", "simplify", "limit", "series",
            "matrix", "determinant", "eigen", "gradient", "derivative", "converge", "proof"
        ]
        if any(k in text.lower() for k in math_keywords):
            return True
        return bool(re.search(r"[+\-/*^=]|∫|Σ|√|≈|≤|≥", text))

    @staticmethod
    def _extract_math_expr(text: str) -> Optional[str]:
        """
        Grab the longest mathy span from natural language (so SymPy doesn't choke).
        """
        m = re.findall(r"[0-9\.\s\+\-\*/\^\(\)]+", text)
        if not m:
            return None
        candidate = max(m, key=len).strip()
        return candidate if any(ch.isdigit() for ch in candidate) else None

    @staticmethod
    def _is_trivial_arithmetic(text: str) -> bool:
        """
        True for small arithmetic queries like '2+3', 'what is 7*8?', '(2+3)^2?'
        i.e., mostly digits/operators, <= ~30 chars after stripping boilerplate.
        """
        t = text.lower().strip()
        t = re.sub(r"^(what\s+is\s+|calculate\s+|compute\s+)", "", t)
        t = t.rstrip("?.! ")
        # If letters remain (beyond e, i, p), treat as non-trivial
        if re.search(r"[a-df-hj-oq-rt-vx-z]", t):  # allow e, i, p loosely
            return False
        return bool(re.fullmatch(r"[\d\s()+\-*/^.]+", t)) and len(t) <= 30

    @staticmethod
    def _wants_icons_from_user(text: str) -> bool:
        """
        Explicit user requests for visuals.
        """
        t = text.lower()
        keyword_triggers = [
            "icon", "icons", "diagram", "diagrams", "visual", "visuals",
            "animation", "illustration", "figure", "figures",
            "meme", "thumbnail", "sketch", "draw", "picture", "image", "graphic"
        ]
        if any(k in t for k in keyword_triggers):
            return True
        # Instructional phrasing like "explain with ___ / using ___ / show ___"
        if re.search(r"\b(explain|illustrate|visuali[sz]e|show|teach)\b.*\b(with|using)\b", t):
            return True
        if re.search(r"\bexplain\b\s+\bwith\b\s+\w+", t):
            return True
        return False

    @staticmethod
    def _wants_icons_from_final(payload: dict) -> bool:
        """
        Decide post hoc based on the final JSON: non-empty visual_brief, or
        clear visual language in the explanation.
        """
        if not payload:
            return False
        vb = payload.get("visual_brief", []) or []
        if isinstance(vb, list) and len(vb) > 0:
            return True
        expl = ((payload.get("explanation") or {}).get("content") or "").lower()
        visual_cues = [
            "imagine", "picture", "see", "visual", "diagram", "arrow", "number line",
            "area under", "vector", "slide", "stack", "highlight", "shade"
        ]
        return any(k in expl for k in visual_cues)

    @staticmethod
    def _needs_clarification(text: str) -> bool:
        """
        Ask for clarification ONLY if the input looks like gibberish
        (nonsense words, random chars, no clear math/code/natural question).
        """
        t = text.strip()

        # Too short to mean anything
        if len(t) < 3:
            return True

        # Heuristic: mostly symbols without context
        if re.fullmatch(r"[\W_]+", t):  # e.g. "!!!", "???", "///"
            return True

        # Looks like random gibberish (no vowels, weird character runs)
        if not re.search(r"[aeiouAEIOU]", t) and len(t) > 6:
            return True

        # If it's only one nonsense word like "asdkjh" or "qwertyuiop"
        if re.fullmatch(r"[a-zA-Z]{6,}", t) and not re.search(r"(math|code|explain|what|why|how)", t.lower()):
            return True

        return False


    @staticmethod
    def _needs_arxiv(text: str, is_math: bool, code_path: Optional[str], trivial_math: bool) -> bool:
        """
        Default ON for research/conceptual queries:
        - OFF if a code file was provided
        - OFF for trivial math (e.g., '2+3')
        - For non-trivial math proofs/theory requests, turn ON if theory keywords are present
        - For non-math, non-code, ON by default
        """
        if code_path:
            return False
        if trivial_math:
            return False
        if is_math:
            theory_triggers = ["proof", "theorem", "convergence", "bound", "rate", "lower bound", "upper bound"]
            return any(k in text.lower() for k in theory_triggers)
        # Non-math, non-code → ON by default
        return True

    # ---------------- Planning ----------------
    def _build_plan(self, user_input: str) -> List[StepPlan]:
        plan: List[StepPlan] = []
        i = 0

        code_path = self._extract_code_path(user_input)
        is_math = self._looks_like_math(user_input)
        trivial_math = self._is_trivial_arithmetic(user_input)
        wants_arxiv = self._needs_arxiv(user_input, is_math=is_math, code_path=code_path, trivial_math=trivial_math)
        wants_clar = self._needs_clarification(user_input)

        # Step 0: Clarification (only if crucial)
        if wants_clar:
            plan.append(StepPlan(
                idx=i, tool="ask_clarification",
                reason="If the question doesn't make any sense; ask exactly one concise question.",
                args={"prompt": user_input}
            ))
            i += 1

        # Step 1 tools (0..n)
        if code_path:
            plan.append(StepPlan(
                idx=i, tool="code_analysis",
                reason="Code file provided; analyze and answer the question.",
                args={"file_path": code_path, "question": user_input}
            ))
            i += 1

        if is_math:
            expr = self._extract_math_expr(user_input) or user_input
            plan.append(StepPlan(
                idx=i, tool="sympy",
                reason="Math-like query; verify/compute with SymPy.",
                args={"expression": expr}
            ))
            i += 1

        if wants_arxiv:
            plan.append(StepPlan(
                idx=i, tool="arxiv_search",
                reason="Research-style or conceptual query; fetch literature context from arXiv.",
                args={"query": user_input, "max_results": 5, "debug": False}
            ))
            i += 1

        # Step 2: final answer (100–250 words + visual_brief)
        plan.append(StepPlan(
            idx=i, tool="final_answer",
            reason="Synthesize 3Blue1Brown-style explanation (100–250 words) + visual_brief.",
            args={}
        ))
        i += 1

        # NOTE: We DO NOT pre-add icon_generation here; we decide after final_answer.

        # ---- Print ONE definitive plan (YES/NO per tool) ----
        print("\n🧭 EXECUTION PLAN (decided before running):")
        flags = {
            "ask_clarification": wants_clar,
            "code_analysis": bool(code_path),
            "sympy": bool(is_math),
            "arxiv_search": bool(wants_arxiv),
            "final_answer": True,
            "icon_generation": "TBD (decide after final_answer)",
        }
        for name, enabled in flags.items():
            if isinstance(enabled, str):
                mark = "❓"
                note = enabled
            else:
                mark = "✅" if enabled else "❌"
                note = ""
            print(f"  {mark} {name}" + (f" — {note}" if note else ""))

        print("\n📋 ORDERED STEPS:")
        for p in plan:
            print(f"  • {p.tool}: {p.reason}")
            if p.args:
                arg_preview = {k: (v if isinstance(v, (int, float, bool)) else str(v)) for k, v in p.args.items()}
                if arg_preview:
                    print(f"    args: {arg_preview}")

        return plan

    # ---------------- Runner ----------------
    def run(self, user_input: str) -> str:
        plan = self._build_plan(user_input)

        combined_result_snippets: List[str] = []
        final_payload = None

        for p in plan:
            tool = self.tool_map.get(p.tool)
            if not tool:
                return f"⚠️ Unknown tool '{p.tool}'. Available: {list(self.tool_map.keys())}"

            try:
                if p.tool == "ask_clarification":
                    followup = tool.forward(p.args["prompt"])
                    print("\n✅ Clarification check done." + (f" Needs: {followup}" if followup else " No extra info required."))
                    continue

                if p.tool == "code_analysis":
                    out = tool.forward(p.args["file_path"], p.args["question"])
                    print("\n💻 Code analysis output:\n" + str(out))
                    combined_result_snippets.append(f"[code_analysis]\n{out}")
                    continue

                if p.tool == "sympy":
                    out = tool.forward(p.args["expression"])
                    print("\n🔢 SymPy output:\n" + str(out))
                    combined_result_snippets.append(f"[sympy]\n{out}")
                    continue

                if p.tool == "arxiv_search":
                    out = tool.forward(p.args["query"], p.args["max_results"], p.args["debug"])
                    print("\n📚 ArXiv search output:\n" + str(out))
                    combined_result_snippets.append(f"[arxiv]\n{out}")
                    continue

                if p.tool == "final_answer":
                    fa = self.tool_map["final_answer"]
                    context_blob = "\n\n".join(combined_result_snippets).strip()
                    result_str = fa.forward(question=user_input, result=context_blob)
                    os.makedirs("output", exist_ok=True)
                    try:
                        final_payload = json.loads(result_str)
                    except Exception:
                        final_payload = {
                            "question": user_input,
                            "explanation": {"content": result_str},
                            "visual_brief": [],
                            "visual_assets": {"icons": []},
                        }
                    final_payload.setdefault("visual_brief", [])
                    final_payload.setdefault("visual_assets", {}).setdefault("icons", [])
                    with open("output/latest_explanation.json", "w", encoding="utf-8") as f:
                        f.write(json.dumps(final_payload, indent=2, ensure_ascii=False))
                    print("\n🧾 Final explanation (with visual_brief) created.")
                    print("\n🧾 Final JSON snapshot:\n" + json.dumps(final_payload, indent=2, ensure_ascii=False))

                    # -------- Decide icons AFTER final answer --------
                    user_wants = self._wants_icons_from_user(user_input)
                    final_wants = self._wants_icons_from_final(final_payload)
                    should_icons = user_wants or final_wants
                    print("\n🎛️ Icon decision:")
                    print(f"  • user_wants_icons: {user_wants}")
                    print(f"  • final_wants_icons: {final_wants}")
                    print(f"  • => will_run_icon_generation: {should_icons}")

                    if should_icons and "icon_generation" in self.tool_map:
                        tool = self.tool_map["icon_generation"]
                        vb = final_payload.get("visual_brief", []) or []
                        concepts_payload = json.dumps({"visual_brief": vb}, ensure_ascii=False) if vb else final_payload.get("explanation", {}).get("content", "")
                        context = final_payload.get("explanation", {}).get("content", "") or user_input
                        icons_json = tool.forward(concepts=concepts_payload, style=None, context=context)

                        print("\n🎨 Icon generation raw output:\n" + str(icons_json))

                        icons_payload = []
                        try:
                            data = json.loads(icons_json)
                            for icon in data.get("generated_icons", []):
                                icons_payload.append({"concept": icon.get("concept", ""), "path": icon.get("filename", "")})
                        except Exception:
                            pass
                        final_payload["visual_assets"]["icons"] = icons_payload
                        with open("output/latest_explanation.json", "w", encoding="utf-8") as f:
                            f.write(json.dumps(final_payload, indent=2, ensure_ascii=False))
                        print("\n🎨 Icons merged into output/latest_explanation.json")
                    continue

            except Exception as e:
                print(f"\n❌ Error in step '{p.tool}': {e}")
                combined_result_snippets.append(f"[{p.tool} ERROR] {e}")

        return json.dumps(final_payload or {
            "question": user_input,
            "explanation": {"content": "No explanation produced."},
            "visual_brief": [],
            "visual_assets": {"icons": []}
        }, ensure_ascii=False)
