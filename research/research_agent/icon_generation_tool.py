import json
import os
from io import BytesIO

import requests
from PIL import Image
from smolagents import Tool


class IconGenerationTool(Tool):
    name = "icon_generation"
    description = (
        "Generate simple, clear educational icons using FLUX models for visual explanations. "
        "Creates relevant icons with a transparent background, no text or math symbols, "
        "suitable for 3Blue1Brown-style animations."
    )
    inputs = {
        "concepts": {
            "type": "string",
            "description": "Comma-separated key concepts or objects to generate icons for (e.g., 'neural network, data flow, algorithm')",
        },
        "model_id": {
            "type": "string",
            "description": "FLUX model ID to use (e.g., 'MusePublic/489_ckpt_FLUX_1')",
            "nullable": True,
            "default": "MusePublic/489_ckpt_FLUX_1",
        },
        "style": {
            "type": "string",
            "description": "Visual style overrides; if not provided, uses a clear, flat minimalist style on transparent background",
            "nullable": True,
            "default": None,
        },
        "context": {
            "type": "string",
            "description": "Context about what the icons will be used for (helps generate more relevant icons)",
            "nullable": True,
            "default": "",
        },
        "image_url": {
            "type": "string",
            "description": "Optional source image URL for editing; if provided, payload will include this key",
            "nullable": True,
            "default": None,
        },
    }
    output_type = "string"

    def __init__(self, api_key: str = None):
        super().__init__()
        self.api_key = api_key or os.getenv(
            "FLUX_API_KEY", "ms-967187ee-26d4-47ec-9cc2-a91dd846846e"
        )
        # Updated model and endpoint URL:
        self.base_url = "https://api-inference.modelscope.cn/v1/images/generations"
        self.default_model = "MusePublic/489_ckpt_FLUX_1"

        os.makedirs("icons", exist_ok=True)

    def forward(
        self,
        concepts: str,
        model_id: str = None,
        style: str = None,
        context: str = "",
        image_url: str = None,
    ) -> str:
        """
        Generate simple educational icons for the given concepts.
        Returns JSON with concept-icon mappings and file paths.
        """
        model_to_use = model_id or self.default_model
        if not style:
            style = (
                "flat minimalist style, simple and clear icons, transparent background, "
                "no text or math symbols, suitable for educational animation"
            )

        concept_list = [c.strip() for c in concepts.split(",") if c.strip()]
        generated_icons = []
        icon_paths = []
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for idx, concept in enumerate(concept_list, start=1):
            prompt_text = (
                f"Create a simple, clear icon representing '{concept}'. "
                f"Style: {style}. "
                f"Background: transparent. "
                f"Context: {context}. "
                f"No text, no mathematical symbols."
            )
            payload = {"model": model_to_use, "prompt": prompt_text}
            if image_url:
                payload["image_url"] = image_url

            try:
                # mirror user’s working pattern with ensure_ascii=False and utf-8 encoding
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                resp = requests.post(
                    self.base_url, data=data, headers=headers, timeout=120
                )
                resp.raise_for_status()
                images = resp.json().get("images", [])
                if not images:
                    print(f"❌ No images returned for '{concept}' using {model_to_use}")
                    continue

                img_url = images[0].get("url")
                img_resp = requests.get(img_url, timeout=30)
                img_resp.raise_for_status()
                image = Image.open(BytesIO(img_resp.content)).convert("RGBA")

                safe_name = "".join(
                    ch for ch in concept if ch.isalnum() or ch in (" ", "-", "_")
                ).rstrip()
                filename = f"icons/{safe_name.replace(' ', '_')}_icon_{idx}.png"
                image.save(filename, format="PNG")

                generated_icons.append(
                    {
                        "concept": concept,
                        "filename": filename,
                        "model": model_to_use,
                        "prompt": prompt_text,
                    }
                )
                icon_paths.append(filename)
                print(
                    f"✅ Icon for '{concept}' saved to {filename} (model: {model_to_use})"
                )

            except Exception as err:
                print(f"❌ Error for '{concept}' with {model_to_use}: {err}")
                continue

        result = {
            "generated_icons": generated_icons,
            "icon_paths": icon_paths,
            "total_generated": len(generated_icons),
            "model_used": model_to_use,
        }
        return json.dumps(result, indent=2)
