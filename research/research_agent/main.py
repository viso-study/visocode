# main.py — Guardrailed pipeline (concise, icons after answer)

import json
import os

from adapter import KimiClientAdapter
from arxiv_tool import ArxivTool
from askclarification_tool import AskClarificationTool
from calc_tool import SympyTool
from code_analysis_tool import CodeAnalysisTool
from enhanced_final_answer_tool import Enhanced3Blue1BrownFinalAnswerTool
from icon_generation_tool import IconGenerationTool
from multi_tool_agent import GuardrailedMultiToolAgent
from openai import OpenAI

# Load API key (Kimi)
try:
    with open("api_key_kimi.txt", "r", encoding="utf-8") as f:
        api_key = f.read().strip()
except FileNotFoundError:
    print("⚠️ api_key_kimi.txt not found. Using demo mode.")
    api_key = "demo-key"

system_prompt = (
    "You are a *guardrailed* research agent.\n"
    "Follow this pipeline strictly:\n"
    "  Step 0: ask_clarification (only if crucial details are missing)\n"
    "  Step 1: run a planned set of analysis tools (code_analysis? sympy? arxiv_search?)\n"
    "  Step 2: final_answer (concise JSON + visual_brief; no icons)\n"
    "  Step 3: if visuals were requested, run icon_generation based on visual_brief + explanation and merge\n"
    "Constraints: One pass, no tool loops. Keep outputs concise; prefer clarity over flair.\n"
)

# Adapter
try:
    kimi = OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1")
    adapter = KimiClientAdapter(kimi, system_prompt=system_prompt)
    print("✅ API client initialized")
except Exception as e:
    print(f"⚠️ API init failed: {e}")
    class MockAdapter:
        def __init__(self, system_prompt): self.system_prompt = system_prompt
        def __call__(self, messages, **kw):
            class Msg: content = "{\"explanation\":{\"content\":\"A short, clear explanation based on the provided results.\"},\"visual_brief\":[{\"concept\":\"Core Idea\",\"caption\":\"Simple visual to highlight the main relationship.\"}]}"
            return Msg()
    adapter = MockAdapter(system_prompt)

# Tools
clar = AskClarificationTool(adapter)
calc = SympyTool()
arxiv = ArxivTool(adapter)
code = CodeAnalysisTool(adapter)
icons = IconGenerationTool()
final = Enhanced3Blue1BrownFinalAnswerTool(adapter)

# Agent
agent = GuardrailedMultiToolAgent([clar, calc, arxiv, code, icons, final], adapter)


def display_welcome():
    print("🤖 Guardrailed Research Agent")
    print("=" * 60)
    print("Pipeline: ask_clarification → [code_analysis? + sympy? + arxiv_search?] → final_answer(+visual_brief) → [icon_generation?]")
    print("Plan is printed first. JSON saved to ./output/latest_explanation.json")

def main():
    display_welcome()
    while True:
        q = input("\n💭 Enter your question (or 'quit'): ")
        if q.strip().lower() in {"quit", "exit", "q"}:
            print("👋 Bye!")
            break

        code_file = input("📁 Optional code file path (Enter to skip): ").strip()
        if code_file:
            if (code_file.startswith('"') and code_file.endswith('"')) or (code_file.startswith("'") and code_file.endswith("'")):
                code_file = code_file[1:-1]
            code_file = os.path.normpath(code_file)
            if os.path.exists(code_file):
                q = f"Please analyze the code file '{code_file}' and answer this question: {q}"
            else:
                print(f"⚠️ File not found: {code_file}. Continuing without code.")

        print("\n🔄 Processing...")
        try:
            result = agent.run(q)
            try:
                if result.strip().startswith('{'):
                    obj = json.loads(result)
                    print("\n🧾 FINAL (concise)")
                    print("=" * 40)
                    print(obj.get("explanation", {}).get("content", ""))

                    vb = obj.get("visual_brief", []) or []
                    if vb:
                        print("\n📝 Visual brief:")
                        for x in vb:
                            print(f" • {x.get('concept','')}: {x.get('caption','')}")

                    ic = obj.get("visual_assets", {}).get("icons", [])
                    if ic:
                        print(f"\n🎨 Icons: {len(ic)}")
                        for i in ic:
                            print(f" • {i.get('concept')}: {i.get('path')}")
                else:
                    print(result)
            except Exception:
                print(result)
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
