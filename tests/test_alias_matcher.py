from app.services.alias_matcher import AliasMatcher
from app.services.catalogue_loader import load_alias_map


def test_real_alias_catalogue():
    alias_map = load_alias_map("skill_catalogue.xlsx")

    matcher = AliasMatcher(alias_map)

    # Check that known aliases are present
    assert matcher.match("python") is not None
    assert matcher.match("py") is not None
    assert matcher.match("reactjs") is not None
    assert matcher.match("postgres") is not None
    assert matcher.match("k8s") is not None


def test_unknown_skill():
    alias_map = load_alias_map("skill_catalogue.xlsx")

    matcher = AliasMatcher(alias_map)

    # Unknown skills should not match anything
    assert matcher.match("this_is_not_a_real_skill") is None
    
def test_input_normalization():
    alias_map = load_alias_map("skill_catalogue.xlsx")

    matcher = AliasMatcher(alias_map)

    assert matcher.match(" Python ") == matcher.match("python")
    assert matcher.match("PYTHON") == matcher.match("python")
    assert matcher.match("  ReactJS  ") == matcher.match("reactjs")