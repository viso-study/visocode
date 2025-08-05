# adapter.py  (updated)

from openai import OpenAI
from smolagents.agents import ChatMessage


class KimiClientAdapter:
    def __init__(self, kimi_client: OpenAI, system_prompt: str = None):
        self.kimi = kimi_client
        self.system_prompt = system_prompt

    def _to_openai_format(self, messages):
        # OpenAI only accepts "system", "user", and "assistant"
        converted = []
        for msg in messages:
            if msg.role == "tool":
                # Represent tool outputs as if the assistant said them
                converted.append({"role": "assistant", "content": msg.content})
            elif msg.role in {"system", "user"}:
                converted.append({"role": msg.role, "content": msg.content})
            # drop any other roles

        # Only prepend the global system_prompt if there is no explicit system message
        has_system = any(msg.role == "system" for msg in messages)
        if self.system_prompt and not has_system:
            converted.insert(0, {"role": "system", "content": self.system_prompt})

        return converted

    def generate(self, messages, **kwargs):
        openai_messages = self._to_openai_format(messages)
        response = self.kimi.chat.completions.create(
            model="kimi-k2-0711-preview",
            messages=openai_messages,
            stream=True,
            **{k: v for k, v in kwargs.items() if k in {"temperature", "max_tokens"}},
        )
        collected = []
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                collected.append(delta.content)
                print(delta.content, end="", flush=True)
        full_text = "".join(collected)
        return ChatMessage(role="assistant", content=full_text)

    __call__ = generate
