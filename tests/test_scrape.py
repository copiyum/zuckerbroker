from househunt import scrape


def test_parse_post_id_from_permalink():
    assert scrape.parse_post_id("https://www.facebook.com/groups/123/posts/456789/") == "456789"


def test_parse_post_id_permalink_query():
    href = "https://www.facebook.com/groups/123/permalink/987654/"
    assert scrape.parse_post_id(href) == "987654"


def test_parse_post_id_multiplace_id_param():
    href = "/groups/123/?multi_permalinks=111222&notif_id=1"
    assert scrape.parse_post_id(href) == "111222"


def test_parse_post_id_none_when_absent():
    assert scrape.parse_post_id("https://www.facebook.com/groups/123/") is None
