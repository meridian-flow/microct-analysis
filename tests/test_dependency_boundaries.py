from __future__ import annotations

import ast
from pathlib import Path


DISALLOWED_PREFIXES = (
    "jupyter_workbench.adapters",
    "jupyter_workbench.core",
    "jupyter_client",
    "nbformat",
)

FORBIDDEN_MOUSE_CT_PREFIXES = (
    "mouse_ct.picker",
    "mouse_ct.seed_editor",
    "mouse_ct.cli",
    "mouse_ct.qc",
)

ALLOWED_STAGE_MOUSE_CT_IMPORTS = {
    "mouse_ct.io.dicom_load",
    "mouse_ct.io.calibration",
    "mouse_ct.io.resample",
    "mouse_ct.processing.preprocess",
    "mouse_ct.processing.threshold",
    "mouse_ct.processing.markers",
    "mouse_ct.processing.watershed",
    "mouse_ct.types",
    "mouse_ct.profiles",
    "mouse_ct.io.output",
    "mouse_ct.verify.sanity",
}

ALLOWED_CORE_MODULES = {
    "microct_analysis.__init__",
    "microct_analysis.domain.__init__",
    "microct_analysis.domain.artifact_contracts",
    "microct_analysis.domain.confidence",
    "microct_analysis.notebook_tasks.__init__",
    "microct_analysis.notebook_tasks.cleanup",
    "microct_analysis.workflows.__init__",
    "microct_analysis.workflows.explain",
    "microct_analysis.workflows.feedback",
    "microct_analysis.workflows.loading",
    "microct_analysis.workflows.review",
    "microct_analysis.workflows.schema",
}


def _iter_python_modules(src_root: Path):
    for path in sorted(src_root.rglob("*.py")):
        yield path, ".".join(path.relative_to(src_root.parent).with_suffix("").parts)


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    return imports


def test_module_scope_imports_stay_on_public_interfaces(microct_src: Path) -> None:
    discovered_modules = set()
    violations: dict[str, list[str]] = {}

    for path, module_name in _iter_python_modules(microct_src):
        discovered_modules.add(module_name)
        bad = [name for name in _imports(path) if name.startswith(DISALLOWED_PREFIXES)]
        if bad:
            violations[module_name] = bad

    assert ALLOWED_CORE_MODULES <= discovered_modules
    assert violations == {}


def test_stage_drivers_use_only_public_mouse_ct_surface(microct_src: Path) -> None:
    stage_root = microct_src / "stages"
    violations: dict[str, list[str]] = {}

    for path in sorted(stage_root.glob("*.py")):
        bad: list[str] = []
        for name in _imports(path):
            if name.startswith(FORBIDDEN_MOUSE_CT_PREFIXES):
                bad.append(name)
            elif name.startswith("mouse_ct") and name not in ALLOWED_STAGE_MOUSE_CT_IMPORTS:
                bad.append(name)
        if bad:
            violations[path.name] = bad

    assert violations == {}
