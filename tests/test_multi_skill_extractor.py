"""Regression tests for general multi-skill extraction behavior."""

import pytest
from app.services.multi_skill_extractor import MultiSkillExtractor

@pytest.fixture
def extractor():
    alias_map = {"python": {1},"py": {1},"machine learning": {2},"ml": {2},"data analytics": {3},"microsoft excel": {4},"excel": {4},"weights & biases": {5},"go": {6}}
    canonical_map = {1: "Python",2: "Machine Learning",3: "Data Analytics",4: "Microsoft Excel",5: "Weights & Biases",6: "Go"}
    return MultiSkillExtractor(alias_map=alias_map, canonical_map=canonical_map)

def test_extract_two_skills_from_sentence(extractor):
    assert extractor.extract("Python for Machine Learning") == ["Python", "Machine Learning"]
def test_extract_skills_connected_by_with(extractor):
    assert extractor.extract("Data Analytics with Microsoft Excel") == ["Data Analytics", "Microsoft Excel"]
def test_whole_catalogue_skill_is_not_split(extractor):
    assert extractor.extract("Weights & Biases") == ["Weights & Biases"]
def test_proficiency_word_is_removed(extractor):
    assert extractor.extract("Machine Learning beginner") == ["Machine Learning"]
def test_ordinary_sentence_does_not_match_go(extractor):
    assert extractor.extract("I want to go to the market") == ["I want to go to the market"]
def test_python_and_go_are_both_extracted(extractor):
    assert extractor.extract("Python and Go") == ["Python", "Go"]
def test_version_stays_attached_to_skill(extractor):
    assert extractor.extract("Python 3.12") == ["Python 3.12"]
def test_version_and_another_skill(extractor):
    assert extractor.extract("Python 3.12 and Machine Learning") == ["Python 3.12", "Machine Learning"]
def test_duplicate_aliases_are_deduplicated(extractor):
    assert extractor.extract("Python, Py, Python") == ["Python"]
def test_single_skill_remains_intact(extractor):
    assert extractor.extract("Python") == ["Python"]
def test_unknown_input_is_preserved(extractor):
    assert extractor.extract("Specialized enterprise platform") == ["Specialized enterprise platform"]
def test_empty_input_returns_empty_list(extractor):
    assert extractor.extract("") == []
def test_whitespace_input_returns_empty_list(extractor):
    assert extractor.extract("   ") == []
def test_ambiguous_go_alone_is_preserved(extractor):
    assert extractor.extract("go") == ["go"]

def test_version_attaches_to_skill_before_it(extractor):
    assert extractor.extract("Machine Learning with Python 3.12") == ["Machine Learning", "Python 3.12"]
def test_version_in_middle(extractor):
    assert extractor.extract("Python 3.12 for Machine Learning") == ["Python 3.12", "Machine Learning"]
def test_source_order_with_unknown_text(extractor):
    assert extractor.extract("FooTool with Python") == ["FooTool", "Python"]
def test_unknown_between_skills_stays_separate(extractor):
    assert extractor.extract("Python FooTool Machine Learning") == ["Python", "FooTool", "Machine Learning"]
def test_short_aliases_in_a_list(extractor):
    assert extractor.extract("py and ml") == ["py", "ml"]
def test_only_filler_is_preserved(extractor):
    assert extractor.extract("programming") == ["programming"]
def test_punctuation_is_cleaned(extractor):
    assert extractor.extract("• Python (advanced)") == ["Python"]

def test_ambiguous_alias_with_version_in_sentence(extractor):
    assert extractor.extract("Advanced experience in Py 3.12 for Machine Learning") == ["Py 3.12", "Machine Learning"]
def test_longer_phrase_with_two_versions(extractor):
    assert extractor.extract("Machine learning projects using Py 3.12 and Python 3.10") == ["Machine learning", "Py 3.12", "Python 3.10"]

def test_compound_skill_stays_whole(extractor):
    assert extractor.extract("Python Pipelines") == ["Python Pipelines"]
def test_parenthesised_list_is_split(extractor):
    assert extractor.extract("Python (Machine Learning, Excel)") == ["Python", "Machine Learning", "Excel"]
def test_parenthesised_version_stays_with_skill(extractor):
    assert extractor.extract("Python (3.12)") == ["Python 3.12"]
def test_acronym_in_parentheses_is_dropped(extractor):
    assert extractor.extract("Data Warehouse Platform (dwp)") == ["Data Warehouse Platform"]
def test_label_before_colon(extractor):
    assert extractor.extract("Languages: Python") == ["Python"]

def test_single_short_abbreviation_in_parentheses_is_dropped(extractor):
    assert extractor.extract("Python (qp)") == ["Python"]
def test_short_items_in_a_list_are_kept(extractor):
    assert extractor.extract("Python (Machine Learning, qp)") == ["Python", "Machine Learning", "qp"]
def test_version_list_in_parentheses_stays_with_skill(extractor):
    assert extractor.extract("Python (2+, 9, 11)") == ["Python 2+, 9, 11"]
