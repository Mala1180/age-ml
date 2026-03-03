import re
from itertools import product
from typing import Dict, Any, Iterator


def extract_python_code(text: str) -> str:
    blocks = re.findall(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    if blocks:
        return "\n\n".join(blocks).strip()
    return text.strip()


def grid_search_exploration(
    hyperparameters: Dict[str, Any],
) -> Iterator[Dict[str, Any]]:
    keys = hyperparameters.keys()
    values = hyperparameters.values()
    for combination in product(*values):
        yield dict(zip(keys, combination))
