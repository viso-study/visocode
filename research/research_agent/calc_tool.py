# calc_tool.py

import sympy as sp
from smolagents import Tool


class SympyTool(Tool):
    name = "sympy"
    description = (
        "Evaluate a single-line SymPy expression.  \n"
        "- **Syntax**: a valid SymPy expression string (no imports or Python statements).  \n"
        "- **Examples**:  \n"
        "    • `integrate(x**2, (x,0,1))`  \n"
        "    • `(u-5).subs(u,3)`  \n"
        "    • `solve(x**2 - 2, x)`  \n"
        "- **Output**: returns LaTeX‑formatted input and result."
    )
    inputs = {
        "expression": {
            "type": "string",
            "description": (
                "Exactly one SymPy expression, as a string.  \n"
                "Do not include imports, symbol definitions, or Python control flow.  \n"
                "For substitutions use either:\n"
                "  • `(expr).subs(var, value)`  \n"
                "  • `subs(expr, var, value)`\n"
                "Examples: `(u-5).subs(u,3)`, `subs(x**2, x, 4)`."
            ),
        }
    }
    output_type = "string"

    def forward(self, expression: str) -> str:
        x, y, z, u = sp.symbols("x y z u")
        try:
            expr = sp.sympify(expression)
        except (sp.SympifyError, TypeError):
            return (
                "Error: could not parse expression. "
                "Use a single‑line SymPy string, e.g., `integrate(x**2, (x,0,1))`."
            )

        result = expr.doit() if hasattr(expr, "doit") else expr
        latex_in = sp.latex(expr)
        latex_out = sp.latex(result)
        return f"Input: $$ {latex_in} $$\nResult: $$ {latex_out} $$"
