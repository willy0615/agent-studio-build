import re


def calculate(expression: str) -> str:
    """Safely evaluate mathematical expressions.

    Only allows numbers, operators (+-*/%), parentheses, and common math functions.
    """
    # Whitelist: digits, operators, parentheses, spaces, dots, commas
    allowed = re.compile(r'^[\d+\-*/%.()\s,eE]+$')
    expression = expression.strip()

    if not allowed.match(expression):
        return "Error: Only arithmetic expressions are allowed."

    try:
        # Use eval with restricted globals
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as e:
        return f"Error: {e}"
