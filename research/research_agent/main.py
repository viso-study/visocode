# main.py - Enhanced MathMentor with 3Blue1Brown-style explanations and icon generation (FIXED)

import json
import os

from adapter import KimiClientAdapter
from arxiv_tool import ArxivTool

# Import existing tools
from askclarification_tool import AskClarificationTool
from calc_tool import SympyTool
from code_analysis_tool import CodeAnalysisTool
from enhanced_final_answer_tool import Enhanced3Blue1BrownFinalAnswerTool

# Import new enhanced tools
from icon_generation_tool import IconGenerationTool
from multi_tool_agent import MultiToolAgent
from openai import OpenAI
from smolagents.agents import ChatMessage

# Load API key with fallback
try:
    with open("api_key_kimi.txt", "r", encoding="utf-8") as f:
        api_key = f.read().strip()
except FileNotFoundError:
    print("⚠️ api_key_kimi.txt not found. Using demo mode.")
    # Create a dummy file for demo
    api_key = "demo-key"  # This won't work but allows testing

# Enhanced system prompt
system_prompt = (
    "You are a Deep Research Agent - an AI tutor, code analyst, and educational content creator.\n"
    "CURRENT DATE: July 27, 2025\n\n"
    "You create 3Blue1Brown-style educational explanations with visual icons for complex topics.\n\n"
    "AVAILABLE TOOLS:\n"
    "  • ask_clarification: Ask follow-up questions if the user's request is ambiguous\n"
    "  • sympy: Perform mathematical computations and symbolic math\n"
    "  • arxiv_search: Search for latest research papers on technical topics\n"
    '    Usage: <tool name="arxiv_search">query="search terms"; max_results=5</tool>\n'
    "    Smart sorting: Automatically prioritizes recent papers or influential ones based on query\n"
    "  • code_analysis: Analyze code files and explain their functionality\n"
    '    Usage: <tool name="code_analysis">file_path="path/to/file"; question="your question"</tool>\n'
    "  • icon_generation: Generate educational icons for key concepts\n"
    '    Usage: <tool name="icon_generation">concepts="concept1, concept2"; context="explanation context"</tool>\n'
    "  • final_answer: Create comprehensive 3Blue1Brown-style educational explanations with icons\n\n"
    "CRITICAL WORKFLOW:\n"
    "1. If question is unclear → use ask_clarification\n"
    "2. For math problems → use sympy\n"
    "3. For research questions → use arxiv_search ONCE\n"
    "4. For code analysis → use code_analysis\n"
    "5. After getting ANY tool results → IMMEDIATELY call final_answer\n\n"
    "IMPORTANT: Call each tool only ONCE per question, then ALWAYS call final_answer to format the output properly.\n"
    "Do NOT repeat tool calls. After arxiv_search returns results, call final_answer immediately.\n"
)


# Enhanced Multi-Tool Agent with fixed logic
class FixedMultiToolAgent(MultiToolAgent):
    def __init__(self, tools, model):
        super().__init__(tools, model)
        self.tool_called = set()  # Track which tools have been called

    def run(self, user_input: str) -> str:
        original_question = user_input
        last_output = None
        tool_execution_history = []
        self.tool_called = set()  # Reset for new question

        while True:
            # Build context for planning
            if last_output is None:
                context = original_question
            else:
                context = (
                    f"QUESTION:\n{original_question}\n\n"
                    f"PREVIOUS_OUTPUT:\n{last_output}\n\n"
                    f"TOOL_HISTORY: {', '.join(tool_execution_history)}\n\n"
                    f"NEXT STEP: You have received tool results. You MUST now call final_answer to create a comprehensive 3Blue1Brown-style educational explanation."
                )

            # Get planning decision from LLM
            try:
                plan_msg = self.model([ChatMessage(role="user", content=context)])
                plan = plan_msg.content.strip()
                print(f"\n🔍 Plan:\n{plan}")
            except Exception as e:
                print(f"❌ Error getting plan: {e}")
                return f"Error: Could not generate plan. {e}"

            # Parse tool invocation
            import re

            tool_match = re.search(
                r'<tool name="([^"]+)">(.*?)</tool>', plan, re.DOTALL
            )
            if not tool_match:
                # No tool found, return the plan as final answer
                return plan

            tool_name, args = tool_match.group(1), tool_match.group(2).strip()

            if tool_name not in self.tool_map:
                return f"⚠️ Unknown tool '{tool_name}'. Available tools: {list(self.tool_map.keys())}"

            # Prevent infinite loops - if we've already used a research tool, force final_answer
            if (
                last_output
                and tool_name in ["arxiv_search", "sympy", "code_analysis"]
                and tool_name in self.tool_called
            ):
                print(
                    f"⚠️ Preventing loop: {tool_name} already called, forcing final_answer"
                )
                tool_name = "final_answer"
                args = "generate_icons=true"

            tool = self.tool_map[tool_name]
            tool_execution_history.append(tool_name)
            self.tool_called.add(tool_name)

            # Execute the appropriate tool
            try:
                if tool_name == "ask_clarification":
                    followup = tool.forward(original_question)
                    print(f"\n🤔 Clarification: {followup}")
                    if followup:
                        extra = input(f"{followup} ")
                        original_question = f"{original_question} {extra}"
                    last_output = None
                    continue

                elif tool_name == "sympy":
                    result = tool.forward(args)
                    print(f"\n🔢 Math calculation:\n{result}")
                    last_output = result
                    continue

                elif tool_name == "arxiv_search":
                    # Parse arxiv arguments
                    query_match = re.search(r'query="([^"]+)"', args)
                    max_results_match = re.search(r"max_results=(\d+)", args)

                    query = query_match.group(1) if query_match else args
                    max_results = (
                        int(max_results_match.group(1)) if max_results_match else 5
                    )

                    result = tool.forward(query, max_results, False)
                    print("\n📋 Research results:")
                    print("=" * 60)
                    print(result)
                    print("=" * 60)
                    last_output = result
                    continue

                elif tool_name == "code_analysis":
                    # Parse code analysis arguments
                    file_path_match = re.search(r'file_path="([^"]+)"', args)
                    question_match = re.search(r'question="([^"]+)"', args)

                    if file_path_match and question_match:
                        file_path = file_path_match.group(1)
                        question = question_match.group(1)
                    else:
                        # Fallback parsing
                        parts = args.split(";", 1)
                        if len(parts) >= 2:
                            file_path = parts[0].strip().strip('"')
                            question = parts[1].strip().strip('"')
                        else:
                            return '⚠️ Invalid code_analysis format. Use: file_path="path"; question="question"'

                    result = tool.forward(file_path, question)
                    print("\n💻 Code analysis complete:")
                    print("=" * 60)
                    print(result)
                    print("=" * 60)
                    last_output = result
                    continue

                elif tool_name == "icon_generation":
                    # Parse icon generation arguments
                    concepts_match = re.search(r'concepts="([^"]+)"', args)
                    style_match = re.search(r'style="([^"]+)"', args)
                    context_match = re.search(r'context="([^"]+)"', args)

                    concepts = concepts_match.group(1) if concepts_match else args
                    style = style_match.group(1) if style_match else None
                    context = context_match.group(1) if context_match else ""

                    result = tool.forward(concepts, style, context)
                    print("\n🎨 Icons generated:")
                    print("=" * 40)
                    print(result)
                    print("=" * 40)
                    last_output = result
                    continue

                elif tool_name == "final_answer":
                    # Enhanced final answer with 3Blue1Brown style and icons
                    generate_icons_match = re.search(
                        r"generate_icons=(true|false)", args, re.IGNORECASE
                    )
                    generate_icons = True  # Default to True
                    if generate_icons_match:
                        generate_icons = generate_icons_match.group(1).lower() == "true"

                    result = tool.forward(
                        original_question, last_output, generate_icons
                    )

                    # Save the result to a file for easy access
                    try:
                        # Create output directory if it doesn't exist
                        os.makedirs("output", exist_ok=True)

                        with open(
                            "output/latest_explanation.json", "w", encoding="utf-8"
                        ) as f:
                            if result.strip().startswith("{"):
                                # Pretty print JSON
                                parsed = json.loads(result)
                                json.dump(parsed, f, indent=2, ensure_ascii=False)
                            else:
                                f.write(result)
                        print(
                            "\n📁 Explanation saved to 'output/latest_explanation.json'"
                        )
                    except Exception as e:
                        print(f"\n⚠️ Could not save to file: {e}")

                    return result

                else:
                    return f"⚠️ Tool '{tool_name}' not implemented in enhanced agent."

            except Exception as e:
                error_msg = f"Error executing {tool_name}: {str(e)}"
                print(f"\n❌ {error_msg}")

                # Try to continue with error information
                if last_output is None:
                    last_output = error_msg
                else:
                    last_output += f"\n\nError in {tool_name}: {str(e)}"
                continue


# Initialize clients and adapters
try:
    kimi = OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1")
    adapter = KimiClientAdapter(kimi, system_prompt=system_prompt)
    print("✅ API client initialized successfully")
except Exception as e:
    print(f"⚠️ API client initialization failed: {e}")
    print("Running in demo mode - some features may not work")

    # Create a mock adapter for testing
    class MockAdapter:
        def __init__(self):
            self.system_prompt = system_prompt

        def __call__(self, messages):
            class MockMsg:
                content = '<tool name="final_answer">generate_icons=false</tool>'

            return MockMsg()

    adapter = MockAdapter()

# Initialize tools
clar = AskClarificationTool(adapter)
calc = SympyTool()
arxiv = ArxivTool(adapter)
code = CodeAnalysisTool(adapter)
icon_gen = IconGenerationTool()  # Uses default API key, can be customized
final = Enhanced3Blue1BrownFinalAnswerTool(adapter, icon_tool=icon_gen)

# Create enhanced agent with fixed logic
agent = FixedMultiToolAgent([clar, calc, arxiv, code, icon_gen, final], adapter)


def display_welcome():
    print("🤖 Research Agent")
    print("=" * 60)
    print("🎨 FEATURES (ALL FIXED):")
    print("  • 3Blue1Brown-style educational explanations (~300 words)")
    print("  • Smart contextual icon generation (not animal-obsessed)")
    print("  • FIXED: Complete ArXiv article display (all papers shown)")
    print("  • FIXED: JSON saved to ./output/ folder (organized)")
    print("  • FIXED: Loop prevention (no infinite arxiv searches)")
    print("  • Deep educational insights beyond simple answers")
    print("\n📋 CAPABILITIES:")
    print("  • Math: 'integrate x^2 from 0 to 1'")
    print("  • Research: 'latest breakthroughs in quantum computing'")
    print("  • Code Analysis: 'explain how this algorithm works' + file path")
    print("  • Educational Explanations: Any topic you want to understand deeply")
    print("=" * 60)
    print("\n💡 TIP: All outputs include visual icons and are formatted for animation!")
    print("   File paths can be quoted or unquoted: C:\\path\\to\\file.py")
    print("\n📁 Generated content will be saved in:")
    print("   • Icons: ./icons/ folder")
    print("   • JSON explanations: ./output/ folder")


def main():
    display_welcome()

    while True:
        # Get user input
        q = input("\n💭 Enter your question (or 'quit'): ")
        if q.strip().lower() in {"quit", "exit", "q"}:
            print("👋 Thanks for using MathMentor Enhanced!")
            break

        # Optional code file for analysis
        code_file = input("📁 Code file path (optional, press Enter to skip): ").strip()

        # Process input
        if code_file:
            # Clean up file path
            if (code_file.startswith('"') and code_file.endswith('"')) or (
                code_file.startswith("'") and code_file.endswith("'")
            ):
                code_file = code_file[1:-1]

            code_file = os.path.normpath(code_file)

            if os.path.exists(code_file):
                print(f"✅ Found code file: {code_file}")
                combined_input = f"Please analyze the code file '{code_file}' and answer this question: {q}"
            else:
                print(f"⚠️ File not found: {code_file}")
                response = input("Continue without code analysis? (y/n): ")
                if response.lower().startswith("n"):
                    continue
                combined_input = q
        else:
            combined_input = q

        # Run the enhanced agent
        try:
            print("\n🔄 Processing your request...")
            result = agent.run(combined_input)

            # Try to parse and display the JSON result nicely
            try:
                if result.strip().startswith("{"):
                    parsed_result = json.loads(result)
                    print("\n🎆 ENHANCED EDUCATIONAL EXPLANATION:")
                    print("=" * 50)

                    # Display the explanation
                    explanation = parsed_result.get("explanation", {})
                    print(f"🎨 Style: {explanation.get('style', 'Educational')}")
                    print(
                        f"\n📝 Content:\n{explanation.get('content', 'No content available')}"
                    )

                    # Display visual assets info
                    visual_assets = parsed_result.get("visual_assets", {})
                    icons = visual_assets.get("icons", [])
                    if icons:
                        print(f"\n🎨 Generated {len(icons)} educational icons:")
                        for icon in icons:
                            concept = icon.get("concept", "Unknown")
                            path = icon.get("path", "No path")
                            print(f"  • {concept}: {path}")

                    # Display animation notes
                    animation_notes = parsed_result.get("animation_notes", {})
                    print(
                        f"\n🎥 Animation Guide: {animation_notes.get('style_guide', 'N/A')}"
                    )

                    print("\n📄 Full JSON saved for animation generation!")
                else:
                    print(f"\n🤖 Research Agent:\n{result}")

            except json.JSONDecodeError:
                print(f"\n🤖 Research Agent Enhanced:\n{result}")

        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please try rephrasing your question or check your input.")


if __name__ == "__main__":
    main()
