from __future__ import annotations

import ast
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "microct_analysis"


@pytest.fixture
def microct_src() -> Path:
    return SRC


@pytest.fixture
def compile_snippet():
    def _compile(snippet: str, *, filename: str = "<generated>") -> ast.AST:
        tree = ast.parse(snippet, filename=filename, mode="exec")
        compile(tree, filename, "exec")
        return tree

    return _compile
