from pathlib import Path

import numpy as np
import pytest
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from microct_analysis.processing.dicom import LoadError, load_dicom


def _write_slice(path: Path, *, instance: int, z: float, value: int) -> None:
    file_meta = FileMetaDataset()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.MediaStorageSOPClassUID = generate_uid()
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.ImplementationClassUID = generate_uid()

    dataset = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    dataset.SOPClassUID = file_meta.MediaStorageSOPClassUID
    dataset.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    dataset.Modality = "CT"
    dataset.Manufacturer = "Synthetic"
    dataset.ManufacturerModelName = "UnitTest"
    dataset.AcquisitionDate = "20260504"
    dataset.InstanceNumber = instance
    dataset.ImagePositionPatient = [10.0, 20.0, z]
    dataset.PixelSpacing = [0.2, 0.3]
    dataset.SliceThickness = 0.5
    dataset.Rows = 2
    dataset.Columns = 3
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = "MONOCHROME2"
    dataset.BitsAllocated = 16
    dataset.BitsStored = 16
    dataset.HighBit = 15
    dataset.PixelRepresentation = 0
    dataset.RescaleSlope = 2
    dataset.RescaleIntercept = -10
    pixels = np.full((2, 3), value, dtype=np.uint16)
    dataset.PixelData = pixels.tobytes()
    dataset.save_as(path, write_like_original=False)


def test_load_dicom_sorts_by_instance_and_converts_to_float32(tmp_path):
    _write_slice(tmp_path / "slice_2.dcm", instance=2, z=1.0, value=20)
    _write_slice(tmp_path / "slice_1.dcm", instance=1, z=0.5, value=10)

    volume = load_dicom(tmp_path)

    assert volume.data.shape == (2, 2, 3)
    assert volume.data.dtype == np.float32
    assert np.all(volume.data[0] == 10.0)  # 10 * slope 2 + intercept -10
    assert np.all(volume.data[1] == 30.0)
    assert volume.spacing == (0.5, 0.2, 0.3)
    np.testing.assert_allclose(np.diag(volume.affine)[:3], [0.3, 0.2, 0.5])
    np.testing.assert_allclose(volume.affine[:3, 3], [10.0, 20.0, 0.5])
    assert volume.provenance == {
        "manufacturer": "Synthetic",
        "model": "UnitTest",
        "acquisition_date": "20260504",
        "slice_count": 2,
    }


def test_load_dicom_raises_on_empty_directory(tmp_path):
    with pytest.raises(LoadError):
        load_dicom(tmp_path)


def test_load_dicom_raises_on_missing_directory(tmp_path):
    with pytest.raises(LoadError):
        load_dicom(tmp_path / "missing")
