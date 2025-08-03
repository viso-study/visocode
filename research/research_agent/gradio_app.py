# gradio_app.py

import gradio as gr
import os
import sys
import threading
import queue

# Ensure we can import your main.py and its functions
sys.path.insert(0, os.path.dirname(__file__))
from main import agent, display_welcome

# --- Custom CSS to shrink fonts and tighten layout ---
custom_css = """
/* Smaller font for all textareas and inputs */
textarea, input {
    font-size: 13px !important;
    line-height: 1.2 !important;
}

/* Tighter padding inside textboxes */
.gradio-textbox textarea, .gradio-textbox input {
    padding: 4px 6px !important;
}

/* Smaller buttons */
button {
    font-size: 13px !important;
    padding: 4px 8px !important;
}

/* Reduce overall container padding */
.gradio-container {
    padding: 8px !important;
}
"""

def gradio_stream(question, file_path=""):
    # Thread-safe queue for printed chunks
    q = queue.Queue()

    # Custom stdout catcher to enqueue all print() output
    class StdoutCatcher:
        def write(self, txt):
            if txt:
                q.put(txt)
        def flush(self):
            pass

    # Monkey-patch stdout so every print goes into our queue
    old_stdout = sys.stdout
    sys.stdout = StdoutCatcher()

    def worker():
        try:
            # 1) Print the welcome banner
            display_welcome()

            # 2) Mirror main.py’s code-path logic for optional file
            combined = question
            fp = file_path.strip()
            if fp:
                if (fp.startswith("'") and fp.endswith("'")) or (fp.startswith('"') and fp.endswith('"')):
                    fp = fp[1:-1]
                fp = os.path.normpath(fp)
                if os.path.exists(fp):
                    print(f"✅ Found code file: {fp}")
                    combined = f"Please analyze the code file '{fp}' and answer this question: {question}"
                else:
                    print(f"⚠️ File not found: {fp}. Continuing without code.")
            print("\n🔄 Processing your request...")

            # 3) Run the agent; every print inside goes to our queue
            agent.run(combined)
        finally:
            # Signal completion by sending None, then restore stdout
            q.put(None)
            sys.stdout = old_stdout

    # Start the agent in a background thread
    threading.Thread(target=worker, daemon=True).start()

    # Accumulate and yield the full console output as it grows
    output = ""
    while True:
        chunk = q.get()
        if chunk is None:
            break
        output += chunk
        yield output

# Build the Gradio interface with custom CSS
demo = gr.Interface(
    fn=gradio_stream,
    inputs=[
        gr.Textbox(label="💭 Enter your question", lines=2),
        gr.Textbox(label="📁 Optional code file path", lines=1),
    ],
    outputs=gr.Textbox(label="📘 Console Output", lines=25),
    title="Deep Research Agent",
    description="All console logs (welcome banner, plans, tool output, final answers) will stream and accumulate below.",
    css=custom_css,
    allow_flagging="never"
)

# Enable the generator-based streaming
demo = demo.queue()

if __name__ == "__main__":
    demo.launch()
