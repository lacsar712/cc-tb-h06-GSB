from rules import weigh


def test_weigh_passes_on_high_score():
    verdict, note, score = weigh(8, 8, 7)
    assert score == 7.8
    assert verdict == "通过"
    assert note == "加权分达到放行线"


def test_weigh_passes_exactly_on_threshold():
    verdict, note, score = weigh(7, 7, 7)
    assert score == 7.0
    assert verdict == "通过"


def test_weigh_fails_on_low_score():
    # 夏茶-C 种子分：0.3*5 + 0.5*4 + 0.2*6 = 4.7
    verdict, note, score = weigh(5, 4, 6)
    assert score == 4.7
    assert verdict == "不通过"
    assert note == "加权分低于放行线"
