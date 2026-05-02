"""Domain helpers for micro-CT analysis using jupyter-workbench."""

# Public-interface-only dependency rule:
# This package may import from:
#   - jupyter_workbench (public services, DTOs, ports)
#   - mouse_ct (public domain types, pipeline, artifacts, explanations)
# Generated kernel exec code may use full jupyter_workbench internals since it
# runs inside the workbench kernel. microct_analysis MODULE-LEVEL imports must
# stick to the public surface. It must NOT import from:
#   - jupyter_workbench.adapters.* (internal adapter implementations)
#   - jupyter_workbench.core.session_lock (internal locking)
#   - jupyter_client, nbformat, or other transport libraries directly
