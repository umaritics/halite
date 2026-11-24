from integrity.citations import has_open_marker, parse_citations


def test_id_in_parentheses():
    assert parse_citations("SUPPLEMENTAL REPORT FOR (ABC12345) found cracks") == ["ABC12345"]


def test_id_without_parentheses():
    assert parse_citations("SUPPLEMENTAL REPORT FOR ABC12345 found cracks") == ["ABC12345"]


def test_id_followed_by_colon_or_period():
    assert parse_citations("SUPPLEMENTAL REPORT FOR ABC12345: cracks") == ["ABC12345"]
    assert parse_citations("SUPPLEMENTAL REPORT FOR ABC12345. Cracks") == ["ABC12345"]


def test_lower_case_text_is_upper_cased():
    assert parse_citations("supplemental report for (abc12345)") == ["ABC12345"]


def test_two_citations_keep_order_and_drop_duplicates():
    text = "SUPPLEMENTAL REPORT FOR ZZZ999 and SUPPLEMENTAL REPORT FOR AAA111 and SUPPLEMENTAL REPORT FOR zzz999"
    assert parse_citations(text) == ["ZZZ999", "AAA111"]


def test_open_marker_alone_is_not_a_citation():
    text = "SUPPLEMENTAL REPORT WILL BE SUBMITTED"
    assert parse_citations(text) == []
    assert has_open_marker(text) is True


def test_short_id_is_not_a_citation():
    assert parse_citations("SUPPLEMENTAL REPORT FOR (AB123)") == []


def test_none_and_empty():
    assert parse_citations(None) == []
    assert parse_citations("") == []
    assert has_open_marker(None) is False
    assert has_open_marker("no marker here") is False
