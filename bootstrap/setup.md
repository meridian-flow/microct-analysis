# microct-analysis bootstrap

This package requires the local `jupyter-workbench` and `mouse-ct` packages. Visualization helpers also require the `pyvista` and `trame` stack provided through those dependencies.

Run these checks after creating or updating the environment:

```bash
python -c "from jupyter_workbench import SessionService, ExecutionService, SnapshotService; print('workbench ok')"
python -c "import mouse_ct; print('mouse-ct ok')"
python -c "import pyvista, trame; print('viz ok')"
```

If any check fails, stop before running notebooks or skills. Install or link the missing package, then rerun all checks. Do not continue with partial bootstrap state because later notebook failures may look like analysis bugs instead of environment problems.
