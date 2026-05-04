"""Processing output helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import nibabel as nib
import numpy as np
from numpy.typing import NDArray


def save_nifti(volume: NDArray[np.generic], path: Path, affine: NDArray[np.floating[Any]]) -> None:
    """Write a NIfTI-1 image, preserving spacing encoded in the affine."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = nib.Nifti1Image(np.asarray(volume), np.asarray(affine, dtype=np.float64))
    nib.save(image, str(output_path))


def save_provenance(metadata: dict[str, Any], path: Path) -> None:
    """Write pipeline provenance JSON using tmp-file + atomic replace."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=output_path.parent, delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)
        json.dump(metadata, tmp_file, indent=2, sort_keys=True)
        tmp_file.write("\n")
        tmp_file.flush()
        os.fsync(tmp_file.fileno())
    os.replace(tmp_path, output_path)
