# VisoCode

> ❓➡️ 📽️ VisoCode turns your questions into cinematic, expert-grade video explanations—powered by intelligent agents and rendered with Manim.

---
### 🧠 Overview

VisoCode is an **AI-powered explainer engine** that transforms questions into **expert-level animated videos** using a multi-agent pipeline. Whether you're curious about quantum mechanics or calculus, Visocode gives you not just an answer, but an explanation you can **see**.
---

### 🔄 How It Works

1. 🙋‍♂️ **You ask a question**
2. 🧠 **ResearchAgent** (powered by **Kimi-K2**) builds an expert explanation using:
   - 🔍 arXiv search
   - 🧮 math/calculation tools
   - 🖼️ icon generation
   - 🧾 structured metadata (sections, visuals, references)
3. 📤 The explanation and metadata are passed to a second agent...
4. 💻 **CodeAgent** (powered by **Gemini**) turns that explanation into:
   - 🎬 Writes frame-accurate Manim scene code
   - 📐 Converts math into LaTeX-rendered visuals
   - 🧩 Syncs icons, timing, and transitions for clarity
5. 🎞️ **Output**: A beautifully rendered, frame-accurate Manim video that explains the concept like a human expert would—with visual clarity.

---

### 🚀 Why VisoCode?

- ✨ **Visual-first learning**: Understand abstract topics through animation  
- 🔗 **Agent-powered pipeline**: Modular, explainable, and extendable  
- ⚡ **Fast, automated output**: From question to video in minutes  
- 🧠 **Expert-level clarity**: Built on cutting-edge AI tools

---

### 💡 Ideal For

- 👩‍💻 Developers learning advanced topics
- 🎓 Students reviewing abstract concepts
- 👨‍🏫 Teachers creating custom explainers
- 📹 YouTubers producing technical content

---

VisoCode isn’t just a tool. It’s a **thinking partner** and **video studio**—all rolled into one intelligent pipeline.

---

# Installation

1. Windows 11 (TODO: support other OS by isolating Windows-specific actions in some microservice)
2. [Git](https://git-scm.com/downloads)
3. [Python >=3.11.6, <3.12](https://www.python.org/downloads/release/python-3116/)
4. [VapourSynth R65](https://github.com/vapoursynth/vapoursynth/releases/tag/R65)
5. [uv](https://docs.astral.sh/uv/getting-started/installation/)
6. [Manim](https://docs.manim.community/en/stable/installation/uv.html)
   - Install a LaTeX distribution as well
7. [ffmpeg](https://ffmpeg.org/download.html)
   - Add executable to path
8. [tex-fmt](https://github.com/WGUNDERWOOD/tex-fmt)
   - Installation involves cargo, the Rust package manager
   - Make sure executable is in path
9. [VS Code](https://code.visualstudio.com/) or a fork like [Cursor](https://cursor.com/en)
10. Clone the repo
11. Open in VS Code
12. Install recommended extensions in `.vscode/extensions.json`
13. Create and populate `.env` following `.env.example`
14. ```console
    uv sync
    ```
15. Activate venv
