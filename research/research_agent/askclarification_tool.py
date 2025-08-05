# askclarification_tool.py

from smolagents import Tool
from smolagents.agents import ChatMessage


class AskClarificationTool(Tool):
    name = "ask_clarification"
    description = (
        "Examine the user's request and, if any crucial details are missing for you to proceed safely "
        "or accurately, generate a single, concise follow‑up question. "
        "If the request is already clear enough, return an empty string."
    )
    inputs = {
        "prompt": {
            "type": "string",
            "description": "The user's original request or previous agent message",
        }
    }
    output_type = "string"

    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, prompt: str) -> str:
        system = ChatMessage(
            role="system",
            content=(
                "You are ClarifyBot. Your job is to spot missing information in the user's request "
                "that would prevent you from giving a correct, safe, or helpful response. "
                "If you detect anything ambiguous or underspecified, ask exactly one follow‑up question "
                "to obtain that detail. Otherwise reply with an empty string."
            ),
        )
        user = ChatMessage(role="user", content=prompt)

        # Invoke your adapter/model quietly
        clarification = self.model(
            [system, user], temperature=0.3, stream=True, echo=False
        )

        return clarification.content.strip()
