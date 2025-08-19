import json
import re

from smolagents.agents import ChatMessage


class MultiToolAgent:
    """
    Enhanced orchestrator for educational content creation with 3Blue1Brown-style explanations.
    Manages tool selection, execution, and creates comprehensive educational outputs.
    """

    def __init__(self, tools, model):
        self.tool_map = {t.name: t for t in tools}
        self.model = model

    def run(self, user_input: str) -> str:
        original_question = user_input
        last_output = None
        tool_execution_history = []

        while True:
            # Build context for planning
            if last_output is None:
                context = original_question
            else:
                context = (
                    f"QUESTION:\n{original_question}\n\n"
                    f"PREVIOUS_OUTPUT:\n{last_output}\n\n"
                    f"TOOL_HISTORY: {', '.join(tool_execution_history)}\n\n"
                    f"NEXT STEP: You have received tool results. You MUST now call final_answer to generate the main JSON."
                )

            # Get planning decision
            plan_msg = self.model([ChatMessage(role="user", content=context)])
            plan = plan_msg.content.strip()
            print(f"\n🔍 Plan:\n{plan}")

            # Parse tool invocation
            tool_match = re.search(
                r'<tool name="([^\"]+)">(.*?)</tool>', plan, re.DOTALL
            )
            if not tool_match:
                # Fallback: save raw content and exit
                fallback = {"content": plan}
                for fname in [
                    "latest_explanation.json",
                    "latest_explanation_backup.json",
                ]:
                    try:
                        with open(fname, "w", encoding="utf-8") as f:
                            json.dump(fallback, f, indent=2, ensure_ascii=False)
                        print(f"\n📁 Fallback JSON saved to '{fname}'")
                    except Exception as e:
                        print(f"\n⚠️ Failed to save fallback JSON to {fname}: {e}")
                return plan

            tool_name, args = tool_match.group(1), tool_match.group(2).strip()

            # Prevent loops: one-off tools only once
            one_off_tools = [
                "arxiv_search",
                "sympy",
                "code_analysis",
                "final_answer",
                "icon_generation",
            ]
            if (
                last_output
                and tool_name in one_off_tools
                and tool_name in tool_execution_history
            ):
                # After final_answer, force icon_generation
                if tool_name == "final_answer":
                    print("⚠️ After final_answer, forcing icon_generation")
                    tool_name = "icon_generation"
                    # Pass the JSON string for icons input
                    args = last_output
                else:
                    print(
                        f"⚠️ Preventing loop: {tool_name} already called, forcing final_answer"
                    )
                    tool_name = "final_answer"
                    args = plan

            if tool_name not in self.tool_map:
                return f"⚠️ Unknown tool '{tool_name}'. Available: {list(self.tool_map.keys())}"

            tool = self.tool_map[tool_name]
            tool_execution_history.append(tool_name)

            try:
                # Clarification
                if tool_name == "ask_clarification":
                    followup = tool.forward(original_question)
                    print(f"\n🤔 Clarification: {followup}")
                    if followup:
                        extra = input(f"{followup} ")
                        original_question += f" {extra}"
                    last_output = None
                    continue

                # Math
                elif tool_name == "sympy":
                    result = tool.forward(args)
                    print(f"\n🔢 Math calculation:\n{result}")
                    last_output = result
                    continue

                # Research
                elif tool_name == "arxiv_search":
                    q_m = re.search(r'query="([^"]+)"', args)
                    r_m = re.search(r"max_results=(\d+)", args)
                    query = q_m.group(1) if q_m else args
                    max_r = int(r_m.group(1)) if r_m else 5
                    result = tool.forward(query, max_r, False)
                    print(f"\n📋 Research results:\n{result[:200]}...")
                    last_output = result
                    continue

                # Code analysis
                elif tool_name == "code_analysis":
                    fp = re.search(r'file_path="([^"]+)"', args)
                    qs = re.search(r'question="([^"]+)"', args)
                    if fp and qs:
                        file_path, question = fp.group(1), qs.group(1)
                    else:
                        parts = args.split(";", 1)
                        file_path = parts[0].strip().strip('"')
                        question = parts[1].strip().strip('"') if len(parts) > 1 else ""
                    result = tool.forward(file_path, question)
                    print(f"\n💻 Code analysis complete:\n{result[:200]}...")
                    last_output = result
                    continue

                # Icon generation
                elif tool_name == "icon_generation":
                    # If args look like JSON, extract content for icons
                    try:
                        data = json.loads(args)
                        title = data.get("title", "")
                        style = data.get("visual_style")
                        context = data.get("content", "")
                        concepts = data.get("content", "")
                    except Exception:
                        # Fallback to raw string
                        title = context = concepts = args
                        style = None
                    icon_data = tool.forward(concepts, style, context)
                    print(f"\n🎨 Icons generated: {icon_data[:100]}...")
                    last_output = icon_data
                    # If forced after final_answer, assemble final JSON here
                    if "final_answer" in tool_execution_history:
                        # load previous output
                        prev_json = json.loads(
                            tool_execution_history and json.dumps(data)
                        )
                        prev_json["icons"] = icon_data
                        final = json.dumps(prev_json, ensure_ascii=False)
                        # Save both JSON files
                        for fname in [
                            "latest_explanation.json",
                            "latest_explanation_backup.json",
                        ]:
                            try:
                                with open(fname, "w", encoding="utf-8") as f:
                                    f.write(final)
                                print(f"\n📁 Final JSON saved to '{fname}'")
                            except Exception as e:
                                print(f"\n⚠️ Failed to save final JSON to {fname}: {e}")
                        return final
                    continue

                # Final answer: produce JSON without icons yet
                elif tool_name == "final_answer":
                    # Extract fields
                    ttl = re.search(r'title="([^"]+)"', args)
                    vst = re.search(r'visual_style="([^"]+)"', args)
                    cnt = re.search(r'content="""(.*?)"""', args, re.DOTALL)
                    output = {
                        "title": ttl.group(1) if ttl else "",
                        "visual_style": vst.group(1) if vst else None,
                        "content": cnt.group(1).strip() if cnt else "",
                    }
                    partial = json.dumps(output, ensure_ascii=False)
                    last_output = partial
                    print(f"\n📝 Partial JSON generated (no icons): {partial[:100]}...")
                    continue

                else:
                    return f"⚠️ Tool '{tool_name}' not implemented."

            except Exception as exc:
                err = f"Error in {tool_name}: {exc}"
                print(f"\n❌ {err}")
                last_output = last_output + f"\n\n{err}" if last_output else err
                continue

    def get_available_tools(self):
        return list(self.tool_map.keys())

    def get_tool_descriptions(self):
        return {
            name: getattr(tool, "description", "")
            for name, tool in self.tool_map.items()
        }
