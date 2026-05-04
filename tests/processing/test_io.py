import json
from typing import cast

import nibabel as nib
import numpy as np

from microct_analysis.processing.io import save_nifti, save_provenance


def test_save_nifti_writes_readable_image_with_affine(tmp_path):
    volume = np.arange(24, dtype=np.float32).reshape((2, 3, 4))
    affine = np.diag([0.01, 0.02, 0.03, 1.0])
    output = tmp_path / "label.nii.gz"

    save_nifti(volume, output, affine)

    loaded = cast(nib.Nifti1Image, nib.load(output))
    np.testing.assert_allclose(loaded.get_fdata(dtype=np.float32), volume)
    assert loaded.affine is not None
    np.testing.assert_allclose(loaded.affine, affine)
    assert tuple(loaded.header.get_zooms()[:3]) == (0.01, 0.02, 0.03)


def test_save_provenance_writes_json_atomically(tmp_path):
    output = tmp_path / "nested" / "provenance.json"
    metadata = {"scanner": "scanco", "slice_count": 42, "steps": ["load", "filter"]}

    save_provenance(metadata, output)

    assert json.loads(output.read_text(encoding="utf-8")) == metadata
    assert not list(output.parent.glob("*.tmp"))
