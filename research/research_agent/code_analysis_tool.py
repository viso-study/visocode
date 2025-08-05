# code_analysis_tool.py - FIXED VERSION

import os

from smolagents import Tool
from smolagents.agents import ChatMessage


class CodeAnalysisTool(Tool):
    name = "code_analysis"
    description = (
        "Analyze code from a file path and answer questions about it. "
        "Reads the code, understands its structure, functionality, and provides detailed explanations."
    )
    inputs = {
        "file_path": {
            "type": "string",
            "description": "Path to the code file to analyze (e.g., 'path/to/script.py')",
        },
        "question": {
            "type": "string",
            "description": "Specific question about the code (e.g., 'How does this function work?', 'What does this algorithm do?')",
        },
    }
    output_type = "string"

    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, file_path: str, question: str) -> str:
        """
        Analyze code from file and answer question about it.
        """
        try:
            # Clean and normalize the file path
            # Remove surrounding quotes if present
            if (file_path.startswith('"') and file_path.endswith('"')) or (
                file_path.startswith("'") and file_path.endswith("'")
            ):
                file_path = file_path[1:-1]

            # Normalize the path for the current OS
            file_path = os.path.normpath(file_path)

            # Read the code file
            if not os.path.exists(file_path):
                abs_path = os.path.abspath(file_path)
                return f"Error: File '{file_path}' not found.\nLooked for: {abs_path}\nPlease check the file path."

            # Try to read the file with different encodings (common on Windows)
            encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]
            code_content = None
            used_encoding = None

            for encoding in encodings:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        code_content = f.read()
                        used_encoding = encoding
                        break
                except UnicodeDecodeError:
                    continue

            if code_content is None:
                return f"Error: Could not read file '{file_path}'. File may be binary or use an unsupported encoding."

            if not code_content.strip():
                return f"Error: File '{file_path}' is empty."

            # Detect file type/language
            file_extension = os.path.splitext(file_path)[1].lower()
            language_map = {
                ".py": "Python",
                ".js": "JavaScript",
                ".ts": "TypeScript",
                ".java": "Java",
                ".cpp": "C++",
                ".c": "C",
                ".cs": "C#",
                ".go": "Go",
                ".rs": "Rust",
                ".php": "PHP",
                ".rb": "Ruby",
                ".swift": "Swift",
                ".kt": "Kotlin",
                ".scala": "Scala",
                ".r": "R",
                ".m": "MATLAB",
                ".sql": "SQL",
                ".sh": "Shell Script",
                ".html": "HTML",
                ".css": "CSS",
            }

            detected_language = language_map.get(file_extension, "Unknown")

            # Create system prompt for code analysis
            system = ChatMessage(
                role="system",
                content=(
                    "You are an expert code analyst and educator. "
                    "Analyze the provided code thoroughly and answer the user's question with clear, "
                    "detailed explanations. Focus on:\n"
                    "- Code functionality and logic\n"
                    "- Algorithm explanations\n"
                    "- Best practices and potential improvements\n"
                    "- Educational insights about the code concepts\n"
                    "- Step-by-step breakdowns when helpful\n"
                    "Always provide concrete examples and be pedagogical in your explanations."
                ),
            )

            # Create analysis prompt
            analysis_prompt = (
                f"FILE: {file_path}\n"
                f"LANGUAGE: {detected_language}\n"
                f"FILE SIZE: {len(code_content)} characters\n"
                f"ENCODING: {used_encoding}\n\n"
                f"CODE CONTENT:\n"
                f"```{detected_language.lower()}\n"
                f"{code_content}\n"
                f"```\n\n"
                f"USER QUESTION: {question}\n\n"
                f"Please analyze this {detected_language} code and answer the question thoroughly. "
                f"Provide educational explanations that help understand both the specific code "
                f"and the underlying concepts."
            )

            user = ChatMessage(role="user", content=analysis_prompt)

            # Get analysis from the model
            response = self.model([system, user])

            # Format the response with metadata
            formatted_response = (
                f"📁 FILE ANALYSIS: {os.path.basename(file_path)}\n"
                f"🔤 LANGUAGE: {detected_language}\n"
                f"📏 SIZE: {len(code_content)} characters\n"
                f"🔤 ENCODING: {used_encoding}\n\n"
                f"❓ QUESTION: {question}\n\n"
                f"🧠 ANALYSIS:\n{response.content.strip()}"
            )

            return formatted_response

        except Exception as e:
            return f"Error analyzing code: {str(e)}"


# Example usage:
# <tool name="code_analysis">file_path="example.py"; question="How does this sorting algorithm work?"</tool>
