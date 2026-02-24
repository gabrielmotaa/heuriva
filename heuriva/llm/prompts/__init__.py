from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_prompt(filename: str) -> str:
    filepath = PROMPTS_DIR / filename
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


HEURISTIC_ANALYSIS_PROMPT = load_prompt("heuristic_analysis.txt")
EXECUTIVE_SUMMARY_PROMPT = load_prompt("executive_summary.txt")
