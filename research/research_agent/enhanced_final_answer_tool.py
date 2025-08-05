import json

from smolagents import Tool
from smolagents.agents import ChatMessage


class Enhanced3Blue1BrownFinalAnswerTool(Tool):
    name = "final_answer"
    description = (
        "Generate a concise educational explanation with 1-2 animal icons for animation. "
        "Outputs JSON with the explanation and icon metadata."
    )
    inputs = {
        "question": {"type": "string", "description": "The user's original question"},
        "result": {"type": "string", "description": "The raw analysis output"},
        "generate_icons": {
            "type": "boolean",
            "description": "Whether to generate animal icons",
            "nullable": True,
            "default": True,
        },
    }
    output_type = "string"

    def __init__(self, model, icon_tool=None):
        super().__init__()
        self.model = model
        self.icon_tool = icon_tool

    def forward(self, question: str, result: str, generate_icons: bool = True) -> str:
        try:
            # 1) System prompt for concise explanation
            system = ChatMessage(
                role="system",
                content=(
                    "You are an expert educator. Provide a very brief, intuitive explanation in plain language. "
                    "Use no more than 4 sentences total. Focus on the core insight and avoid technical jargon."
                ),
            )
            # 2) User prompt with question and analysis
            user_msg = ChatMessage(
                role="user",
                content=(
                    f"QUESTION: {question}\n"
                    f"ANALYSIS: {result}\n\n"
                    "Give a succinct explanation without equations."
                ),
            )
            resp = self.model([system, user_msg])
            explanation = resp.content.strip()

            # 3) Build result JSON
            final_output = {
                "question": question,
                "explanation": {"content": explanation},
                "visual_assets": {"icons": []},
                "metadata": {"note": "Up to 2 animal metaphors"},
            }

            # 4) Optionally generate up to 2 animal icons
            if generate_icons and self.icon_tool:
                concept_sys = ChatMessage(
                    role="system",
                    content="From the explanation, extract up to 2 simple metaphoric concepts that are explicitly mentioned or clearly implied. These should be concrete things like animals, tools, forces, or objects that help visualize the explanation. List by common name only.",
                )
                concept_user = ChatMessage(role="user", content=explanation)
                concept_resp = self.model([concept_sys, concept_user])
                animals = [a.strip() for a in concept_resp.content.split(",")][:2]
                if animals:
                    icon_json = self.icon_tool.forward(
                        concepts=",".join(animals),
                        style="flat minimalist animal icons, educational style",
                        context=f"Explanation for: {question}",
                    )
                    try:
                        data = json.loads(icon_json)
                        for icon in data.get("generated_icons", []):
                            final_output["visual_assets"]["icons"].append(
                                {"animal": icon["concept"], "path": icon["filename"]}
                            )
                    except json.JSONDecodeError:
                        pass

            return json.dumps(final_output, indent=2, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})
