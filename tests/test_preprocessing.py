import pytest

from app.services.preprocessing import normalize_input, normalize_lookup_key


def test_normalize_input():
    assert normalize_input("  Python  ") == "Python"
    assert normalize_input("Python    3.10") == "Python 3.10"
    assert normalize_input("  React   Native  ") == "React Native"
    assert normalize_input("C++") == "C++"
    assert normalize_input(".NET 8") == ".NET 8"


def test_normalize_lookup_key():
    assert normalize_lookup_key("  Python  ") == "python"
    assert normalize_lookup_key("PYTHON 3.10") == "python 3.10"
    assert normalize_lookup_key("React   Native") == "react native"
    assert normalize_lookup_key("C++") == "c++"


@pytest.mark.parametrize("value", [None, 123, [], {}])
def test_non_string_input_is_rejected(value):
    with pytest.raises(ValueError, match="must be a string"):
        normalize_input(value)
