# microct-analysis

Domain package for micro-CT preclinical imaging analysis workflows.

This package depends on `jupyter-workbench` for reusable notebook session management, execution, snapshots, and visualization workflows. It uses `mouse-ct` for the analysis pipeline, domain semantics, artifact descriptions, and structured explanation hooks.

## Dependency boundary

Use only public interfaces from dependencies. Do not import internal adapter, locking, transport, or notebook runtime implementation details. Domain helpers should compose public `jupyter_workbench` services with public `mouse_ct` pipeline, artifact, type, and explanation APIs.
