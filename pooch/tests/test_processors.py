"""
Test the processor hooks
"""
from pathlib import Path

try:
    from tempfile import TemporaryDirectory
except ImportError:
    from backports.tempfile import TemporaryDirectory
import warnings

import pytest

from .. import Pooch
from ..processors import Unzip, Untar, ExtractorProcessor

from .utils import pooch_test_url, pooch_test_registry, check_tiny_data


REGISTRY = pooch_test_registry()
BASEURL = pooch_test_url()


def test_extractprocessor_fails():
    "The base class should be used and should fail when passed to fecth"
    with TemporaryDirectory() as local_store:
        # Setup a pooch in a temp dir
        pup = Pooch(path=Path(local_store), base_url=BASEURL, registry=REGISTRY)
        processor = ExtractorProcessor()
        with pytest.raises(NotImplementedError) as exception:
            pup.fetch("tiny-data.tar.gz", processor=processor)
        assert "'suffix'" in exception.value.args[0]
        processor.suffix = "tar.gz"
        with pytest.raises(NotImplementedError) as exception:
            pup.fetch("tiny-data.tar.gz", processor=processor)
        assert not exception.value.args


@pytest.mark.parametrize(
    "proc_cls,ext", [(Unzip, ".zip"), (Untar, ".tar.gz")], ids=["Unzip", "Untar"]
)
def test_processors(proc_cls, ext):
    "Setup a post-download hook and make sure it's only executed when downloading"
    processor = proc_cls(members=["tiny-data.txt"])
    suffix = proc_cls.suffix
    extract_dir = "tiny-data" + ext + suffix
    with TemporaryDirectory() as local_store:
        path = Path(local_store)
        true_path = str(path / extract_dir / "tiny-data.txt")
        # Setup a pooch in a temp dir
        pup = Pooch(path=path, base_url=BASEURL, registry=REGISTRY)
        # Check the warnings when downloading and from the processor
        with warnings.catch_warnings(record=True) as warn:
            fnames = pup.fetch("tiny-data" + ext, processor=processor)
            fname = fnames[0]
            assert len(fnames) == 1
            assert len(warn) == 2
            assert all(issubclass(w.category, UserWarning) for w in warn)
            assert str(warn[-2].message).split()[0] == "Downloading"
            assert str(warn[-1].message).startswith("Extracting 'tiny-data.txt'")
        assert fname == true_path
        check_tiny_data(fname)
        # Check that processor doesn't execute when not downloading
        with warnings.catch_warnings(record=True) as warn:
            fnames = pup.fetch("tiny-data" + ext, processor=processor)
            fname = fnames[0]
            assert len(fnames) == 1
            assert not warn
        assert fname == true_path
        check_tiny_data(fname)


@pytest.mark.parametrize(
    "proc_cls,ext,msg",
    [(Unzip, ".zip", "Unzipping"), (Untar, ".tar.gz", "Untarring")],
    ids=["Unzip", "Untar"],
)
def test_processor_multiplefiles(proc_cls, ext, msg):
    "Setup a processor to unzip/untar a file and return multiple fnames"
    processor = proc_cls()
    suffix = proc_cls.suffix
    extract_dir = "store" + ext + suffix
    with TemporaryDirectory() as local_store:
        path = Path(local_store)
        true_paths = {
            str(path / extract_dir / "store" / "tiny-data.txt"),
            str(path / extract_dir / "store" / "subdir" / "tiny-data.txt"),
        }
        # Setup a pooch in a temp dir
        pup = Pooch(path=path, base_url=BASEURL, registry=REGISTRY)
        # Check the warnings when downloading and from the processor
        with warnings.catch_warnings(record=True) as warn:
            fnames = pup.fetch("store" + ext, processor=processor)
            assert len(warn) == 2
            assert all(issubclass(w.category, UserWarning) for w in warn)
            assert str(warn[-2].message).split()[0] == "Downloading"
            assert str(warn[-1].message).startswith("{} contents".format(msg))
            assert len(fnames) == 2
            assert true_paths == set(fnames)
            for fname in fnames:
                check_tiny_data(fname)
        # Check that processor doesn't execute when not downloading
        with warnings.catch_warnings(record=True) as warn:
            fnames = pup.fetch("store" + ext, processor=processor)
            assert not warn
            assert len(fnames) == 2
            assert true_paths == set(fnames)
            for fname in fnames:
                check_tiny_data(fname)
