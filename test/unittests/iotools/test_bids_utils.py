from pathlib import Path
from string import Template
from typing import Optional, Union

import numpy as np
import pandas as pd
import pytest

from clinica.iotools.bids_utils import (
    StudyName,
    _write_bids_validator_config,
    _write_bidsignore,
    _write_readme,
)

MODALITY_AGNOSTIC_FILE_WRITERS = {
    #    "readme": _write_readme,
    "bids-validator": _write_bids_validator_config,
    "bidsignore": _write_bidsignore,
}


EXPECTED_MODALITY_AGNOSTIC_FILES = {
    "description": "dataset_description.json",
    "readme": "README",
    "bids-validator": ".bids-validator-config.json",
    "bidsignore": ".bidsignore",
}


EXPECTED_README_CONTENT = Template(
    (
        "This BIDS directory was generated with Clinica v$version.\n"
        "More information on $website\n"
        "\n"
        "Study: $study\n"
        "\n"
        "description\n\n"
        "Find more about it and about the data user agreement: link"
    )
)


@pytest.mark.parametrize(
    "study,study_id,expected",
    [
        (StudyName.ADNI, "001_S_0001", "sub-ADNI001S0001"),
        (StudyName.NIFD, "1_S_0001", "sub-NIFD1S0001"),
        (StudyName.AIBL, "10", "sub-AIBL10"),
        (StudyName.UKB, "0101001", "sub-UKB0101001"),
        (StudyName.GENFI, "MAPT009", "sub-MAPT009"),
        (StudyName.OASIS3, "OAS30001", "sub-OAS30001"),
        (StudyName.HABS, "P_INIBUB", "sub-HABSINIBUB"),
        (StudyName.OASIS, "OAS1_0001_MR1", "sub-OASIS10001"),
        (StudyName.IXI, "IXI001", "sub-IXI001"),
    ],
)
def test_study_to_bids_id_passing(study, study_id, expected):
    from clinica.iotools.bids_utils import bids_id_factory

    assert bids_id_factory(study).from_original_study_id(study_id) == expected


@pytest.mark.parametrize(
    "study,study_id",
    [
        (StudyName.ADNI, "001S0001"),
        (StudyName.ADNI, "001_X_0001"),
        (StudyName.ADNI, "foo_S_0001"),
        (StudyName.NIFD, "1S0001"),
        (StudyName.NIFD, "1_X_0001"),
        (StudyName.NIFD, "foo_S_0001"),
        (StudyName.AIBL, "10A"),
        (StudyName.UKB, "0101001A"),
        (StudyName.GENFI, "MAPT009?"),
        (StudyName.OASIS3, "OAS3_0001"),
        (StudyName.OASIS3, "OAS3001"),
        (StudyName.HABS, "PINIBUB"),
        (StudyName.HABS, "X_INIBUB"),
        (StudyName.HABS, "P_INIBUB?"),
        (StudyName.OASIS, "OAS10001MR1"),
        (StudyName.OASIS, "OAS1_0001_MRI1"),
        (StudyName.OASIS, "OAS1_001_MR1"),
        (StudyName.IXI, "IXI_001"),
        (StudyName.IXI, "IXI0001"),
    ],
)
def test_study_to_bids_id_value_error(study, study_id):
    from clinica.iotools.bids_utils import bids_id_factory

    with pytest.raises(ValueError):
        bids_id_factory(study).from_original_study_id(study_id)


@pytest.mark.parametrize(
    "study,source_id,bids_id",
    [
        (StudyName.ADNI, "001_S_0001", "sub-ADNI001S0001"),
        (StudyName.NIFD, "1_S_0001", "sub-NIFD1S0001"),
        (StudyName.AIBL, "10", "sub-AIBL10"),
        (StudyName.UKB, "0101001", "sub-UKB0101001"),
        (StudyName.GENFI, "MAPT009", "sub-MAPT009"),
        (StudyName.OASIS3, "OAS30001", "sub-OAS30001"),
        (StudyName.HABS, "P_INIBUB", "sub-HABSINIBUB"),
        (StudyName.OASIS, "OAS1_0001_MR1", "sub-OASIS10001"),
        (StudyName.IXI, "IXI001", "sub-IXI001"),
    ],
)
def test_bids_to_study(study, bids_id, source_id):
    from clinica.iotools.bids_utils import bids_id_factory

    assert bids_id_factory(study)(bids_id).to_original_study_id() == source_id


def create_participants_spec(tmp_path: Path) -> Path:
    spec_df = pd.DataFrame(
        {
            "BIDS CLINICA": [
                "participant_id",
                "alternative_id_1",
                "date_of_birth",
                "sex",
                "apoegen1",
            ],
            "ADNI": [np.nan, "PTID", np.nan, "PTGENDER", "APGEN1"],
            "ADNI location": [
                np.nan,
                "ADNIMERGE.csv",
                np.nan,
                "ADNIMERGE.csv",
                "APOERES.csv",
            ],
            "OASIS": [np.nan, "ID", np.nan, "M/F", np.nan],
            "OASIS location": [
                np.nan,
                "oasis_cross-sectional-5708aa0a98d82080.xlsx",
                np.nan,
                "oasis_cross-sectional-5708aa0a98d82080.xlsx",
                np.nan,
            ],
        }
    )
    spec_df.to_csv(tmp_path / "participant.tsv", sep="\t", index=False)

    return tmp_path


def create_clinical_data(
    tmp_path: Path, study_name: StudyName, adni_genotype: Optional[bool] = False
) -> Path:
    clinical_path = tmp_path / "clinical_data"
    clinical_path.mkdir()

    if study_name == StudyName.ADNI:
        df_adnimerge = pd.DataFrame(
            {
                "PTID": [
                    "001_S_0001",
                    "001_S_0002",
                    "001_S_0003",
                    "001_S_0004",
                    "001_S_0005",
                    "001_S_0006",
                ],
                "PTGENDER": ["Male", "Female", "Male", "Female", "Female", None],
                "AGE": ["40", "50", "60", "70", "80", None],
            }
        )

        df_apoeres = pd.DataFrame(
            {
                "APGEN1": ["3", "3", "3", "3", None, "3"],
                "GEN2": ["2", "2", "2", "2", None, "2"],
            }
        )

        if adni_genotype:
            df_apoeres = pd.DataFrame(
                {
                    "GENOTYPE": ["3/2", "3/2", "3/2", "3/2", None, "3/2"],
                    "GEN2": ["2", "2", "2", "2", None, "2"],
                }
            )

        df_adnimerge.to_csv(clinical_path / "ADNIMERGE.csv", index=False)
        df_apoeres.to_csv(clinical_path / "APOERES.csv", index=False)

    if study_name == StudyName.OASIS:
        df_oasis = pd.DataFrame(
            {
                "ID": [
                    "OAS1_0001_MR1",
                    "OAS1_0002_MR1",
                    "OAS1_0003_MR1",
                    "OAS1_0004_MR1",
                    "OAS1_0004_MR2",
                ],
                "M/F": ["F", "M", "F", "M", "M"],
                "Age": ["45", "50", "55", "60", "60"],
            }
        )
        df_oasis.to_excel(
            clinical_path / "oasis_cross-sectional-5708aa0a98d82080.xlsx", index=False
        )
    return clinical_path


@pytest.mark.parametrize(
    "study_name, bids_ids, expected, adni_genotype",
    [
        (
            StudyName.OASIS,
            ["sub-OASIS10001"],
            pd.DataFrame(
                {
                    "participant_id": ["sub-OASIS10001"],
                    "alternative_id_1": ["OAS1_0001_MR1"],
                    "sex": ["F"],
                }
            ),
            False,
        ),
        (
            StudyName.ADNI,
            ["sub-ADNI001S0001"],
            pd.DataFrame(
                {
                    "participant_id": ["sub-ADNI001S0001"],
                    "alternative_id_1": ["001_S_0001"],
                    "sex": ["Male"],
                    "apoegen1": ["3"],
                }
            ),
            True,
        ),
        (
            StudyName.OASIS,
            ["sub-OASIS10002", "sub-OASIS10004", "sub-OASIS10007"],
            pd.DataFrame(
                {
                    "participant_id": ["sub-OASIS10002", "sub-OASIS10004"],
                    "alternative_id_1": ["OAS1_0002_MR1", "OAS1_0004_MR1"],
                    "sex": ["M", "M"],
                }
            ),
            False,
        ),
        (
            StudyName.ADNI,
            ["sub-ADNI001S0005"],
            pd.DataFrame(
                {
                    "participant_id": ["sub-ADNI001S0005"],
                    "alternative_id_1": ["001_S_0005"],
                    "sex": ["Female"],
                    "apoegen1": ["n/a"],
                }
            ),
            False,
        ),
        (
            StudyName.ADNI,
            ["sub-ADNI001S0006"],
            pd.DataFrame(
                {
                    "participant_id": ["sub-ADNI001S0006"],
                    "alternative_id_1": ["001_S_0006"],
                    "sex": ["n/a"],
                    "apoegen1": [3.0],
                }
            ),
            False,
        ),
    ],
)
def test_create_participants_df(
    tmp_path, bids_ids, expected, study_name, adni_genotype
):
    from clinica.iotools.bids_utils import create_participants_df

    assert (
        create_participants_df(
            study_name,
            clinical_specifications_folder=create_participants_spec(tmp_path),
            clinical_data_dir=create_clinical_data(tmp_path, study_name, adni_genotype),
            bids_ids=bids_ids,
        )
        .reset_index(drop=True)
        .equals(expected)
    )


def test_get_bids_subjs_list(tmp_path):
    from clinica.iotools.bids_utils import get_bids_subjs_list

    (tmp_path / "file").touch()
    (tmp_path / "sub-03").touch()
    (tmp_path / "folder").mkdir()

    for sub in ("sub-01", "sub-02", "sub-16"):
        (tmp_path / sub).mkdir()

    assert set(get_bids_subjs_list(tmp_path)) == {"sub-01", "sub-02", "sub-16"}


@pytest.mark.parametrize(
    "input_string,expected",
    [
        ("foo", "foo"),
        ("foo_bar", "foobar"),
        ("foo bar", "foobar"),
        ("foo bar_baz", "foobarbaz"),
        ("foo-ba_r baz", "foobarbaz"),
    ],
)
def test_remove_space_and_symbols(input_string, expected):
    from clinica.iotools.bids_utils import remove_space_and_symbols

    assert remove_space_and_symbols(input_string) == expected


@pytest.mark.parametrize("compress", [True, False])
@pytest.mark.parametrize("sidecar", [True, False])
def test_build_dcm2niix_command(tmp_path, compress, sidecar):
    from clinica.iotools.bids_utils import _build_dcm2niix_command

    compress_flag = "y" if compress else "n"
    sidecar_flag = "y" if sidecar else "n"
    expected = ["dcm2niix", "-w", "0", "-f", "fmt", "-o", str(tmp_path / "out")]
    if compress:
        expected += ["-9"]
    expected += ["-z", compress_flag, "-b", sidecar_flag]
    if sidecar:
        expected += ["-ba", "y"]
    expected += [str(tmp_path / "in")]
    assert (
        _build_dcm2niix_command(
            tmp_path / "in",
            tmp_path / "out",
            "fmt",
            compress=compress,
            bids_sidecar=sidecar,
        )
        == expected
    )


def _validate_file_and_content(file: Path, expected_content: str) -> None:
    assert file.exists()
    assert file.read_text() == expected_content


@pytest.fixture
def expected_description_content(
    study_name: StudyName,
    bids_version: Union[None, str],
) -> str:
    import json

    from clinica.utils.bids import BIDS_VERSION

    expected_version = BIDS_VERSION if bids_version is None else bids_version
    desc_dict = {
        "Name": study_name.value,
        "BIDSVersion": str(expected_version),
        "DatasetType": "raw",
    }
    return json.dumps(desc_dict, indent=4)


@pytest.mark.parametrize("study_name", StudyName)
@pytest.mark.parametrize("bids_version", [None, "1.6.0", "1.7.0"])
def test_write_bids_dataset_description(
    tmp_path,
    study_name,
    bids_version,
    expected_description_content,
):
    """Test function `_write_bids_dataset_description`.

    .. note::
        Tested independently for convenience since it takes
        a different set of input parameters.

    """
    from clinica.iotools.bids_utils import _write_bids_dataset_description

    _write_bids_dataset_description(study_name, tmp_path, bids_version=bids_version)
    _validate_file_and_content(
        tmp_path / EXPECTED_MODALITY_AGNOSTIC_FILES["description"],
        expected_description_content,
    )


def expected_validator_content() -> str:
    import json

    from clinica.iotools.bids_utils import BIDS_VALIDATOR_CONFIG

    return json.dumps(BIDS_VALIDATOR_CONFIG, indent=4)


@pytest.fixture
def expected_content(name: str, study_name: StudyName) -> str:
    if name == "readme":
        return get_expected_readme_content(study_name)
    elif name == "bids-validator":
        return expected_validator_content()
    return "\n".join(["swi/", "conversion_info/"])


@pytest.mark.parametrize("study_name", StudyName)
@pytest.mark.parametrize("name,writer", MODALITY_AGNOSTIC_FILE_WRITERS.items())
def test_modality_agnostic_file_writers(
    tmp_path, study_name, name, writer, expected_content
):
    """Test helper functions of the function `write_modality_agnostic_files`."""
    writer(tmp_path)
    _validate_file_and_content(
        tmp_path / EXPECTED_MODALITY_AGNOSTIC_FILES[name], expected_content
    )


def test_write_modality_agnostic_files(tmp_path):
    """Test function `write_modality_agnostic_files`."""
    import os

    from clinica.iotools.bids_utils import write_modality_agnostic_files

    data_dict = {"link": "", "desc": ""}
    assert len(os.listdir(tmp_path)) == 0
    write_modality_agnostic_files(StudyName.ADNI, data_dict, tmp_path)
    files = os.listdir(tmp_path)
    assert len(files) == 4
    for _, v in EXPECTED_MODALITY_AGNOSTIC_FILES.items():
        assert v in files


@pytest.mark.parametrize("study_name", StudyName)
@pytest.mark.parametrize("bids_version", ["1.7.0"])
def test_write_bids_readme(
    tmp_path,
    study_name: StudyName,
    bids_version,
):
    """Test function `_write_bids_readme`.

    .. note::
        Tested independently for convenience since it takes
        a different set of input parameters.

    """

    data_dict = {"link": "link", "desc": "description"}
    _write_readme(study_name=study_name, data_dict=data_dict, bids_dir=tmp_path)
    _validate_file_and_content(
        file=tmp_path / EXPECTED_MODALITY_AGNOSTIC_FILES["readme"],
        expected_content=get_expected_readme_content(study_name),
    )


def get_expected_readme_content(study_name: StudyName) -> str:
    import clinica

    return EXPECTED_README_CONTENT.safe_substitute(
        version=clinica.__version__,
        website="https://www.clinica.run",
        study=study_name.value,
    )
