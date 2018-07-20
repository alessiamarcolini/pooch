"""
Test the Garage class.
"""
import os
from tempfile import TemporaryDirectory
import warnings

import pytest

from .. import Garage
from ..utils import file_hash
from .utils import garage_test_url, garage_test_registry, check_tiny_data


DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
REGISTRY = garage_test_registry()
BASEURL = garage_test_url()
REGISTRY_CORRUPTED = {
    # The same data file but I changed the hash manually to a wrong one
    "tiny-data.txt": "098h0894dba14b12085eacb204284b97e362f4f3e5a5807693cc90ef415c1b2d"
}


def test_garage_local():
    "Setup a garage that already has the local data and test the fetch."
    garage = Garage(path=DATA_DIR, base_url="some bogus URL", registry=REGISTRY)
    true = os.path.join(DATA_DIR, "tiny-data.txt")
    fname = garage.fetch("tiny-data.txt")
    assert true == fname
    check_tiny_data(fname)


def test_garage_update():
    "Setup a garage that already has the local data but the file is outdated"
    with TemporaryDirectory() as local_store:
        path = os.path.abspath(os.path.expanduser(local_store))
        # Create a dummy version of tiny-data.txt that is different from the one in the
        # remote storage
        true_path = os.path.join(path, "tiny-data.txt")
        with open(true_path, "w") as fin:
            fin.write("different data")
        # Setup a garage in a temp dir
        garage = Garage(path=path, base_url=BASEURL, registry=REGISTRY)
        # Check that the warning says that the file is being updated
        with warnings.catch_warnings(record=True) as warn:
            fname = garage.fetch("tiny-data.txt")
            assert len(warn) == 1
            assert issubclass(warn[-1].category, UserWarning)
            assert str(warn[-1].message).split()[0] == "Updating"
            assert str(warn[-1].message).split()[-1] == "'{}'.".format(path)
        # Check that the updated file has the right content
        assert true_path == fname
        check_tiny_data(fname)
        assert file_hash(fname) == REGISTRY["tiny-data.txt"]


def test_garage_corrupted():
    "Raise an exception if the hash of downloaded file doesn't match the registry"
    # Test the case where the file wasn't in the directory
    with TemporaryDirectory() as local_store:
        path = os.path.abspath(os.path.expanduser(local_store))
        garage = Garage(path=path, base_url=BASEURL, registry=REGISTRY_CORRUPTED)
        with warnings.catch_warnings(record=True) as warn:
            with pytest.raises(ValueError):
                garage.fetch("tiny-data.txt")
            assert len(warn) == 1
            assert issubclass(warn[-1].category, UserWarning)
            assert str(warn[-1].message).split()[0] == "Downloading"
            assert str(warn[-1].message).split()[-1] == "'{}'.".format(path)
    # and the case where the file exists but hash doesn't match
    garage = Garage(path=DATA_DIR, base_url=BASEURL, registry=REGISTRY_CORRUPTED)
    with warnings.catch_warnings(record=True) as warn:
        with pytest.raises(ValueError):
            garage.fetch("tiny-data.txt")
        assert len(warn) == 1
        assert issubclass(warn[-1].category, UserWarning)
        assert str(warn[-1].message).split()[0] == "Updating"
        assert str(warn[-1].message).split()[-1] == "'{}'.".format(DATA_DIR)


def test_garage_file_not_in_registry():
    "Should raise an exception if the file is not in the registry."
    garage = Garage(
        path="it shouldn't matter", base_url="this shouldn't either", registry=REGISTRY
    )
    with pytest.raises(ValueError):
        garage.fetch("this-file-does-not-exit.csv")


def test_garage_load_registry():
    "Loading the registry from a file should work"
    garage = Garage(path="", base_url="", registry={})
    garage.load_registry(os.path.join(DATA_DIR, "registry.txt"))
    assert garage.registry == REGISTRY


def test_garage_load_registry_invalid_line():
    "Should raise an exception when a line doesn't have two elements"
    garage = Garage(path="", base_url="", registry={})
    with pytest.raises(ValueError):
        garage.load_registry(os.path.join(DATA_DIR, "registry-invalid.txt"))
