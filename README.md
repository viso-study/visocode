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
