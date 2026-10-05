from app.services.preprocessing import (
    normalize_input,
    normalize_lookup_key,
    extract_version,
)


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


def test_extract_version():
    assert extract_version("Python 3.10") == ("Python", "3.10")
    assert extract_version("Java 17") == ("Java", "17")
    assert extract_version("React 18") == ("React", "18")
    assert extract_version("PostgreSQL 15") == ("PostgreSQL", "15")
    assert extract_version(".NET 8") == (".NET", "8")


def test_extract_multi_part_version():
    assert extract_version("Python 3.10.2") == ("Python", "3.10.2")


def test_no_version():
    assert extract_version("Python") == ("Python", None)
    assert extract_version("React Native") == ("React Native", None)


def test_version_with_v_prefix():
    assert extract_version("Python v3.10") == ("Python", "3.10")