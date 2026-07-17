from agent_yhzh.services.learning import normalize_learning_key


def test_normalize_learning_key_handles_chinese_punctuation() -> None:
    assert normalize_learning_key("  怎么发布内容？ ") == "怎么发布内容"


def test_normalize_learning_key_collapses_whitespace() -> None:
    assert normalize_learning_key("How   does this work?") == "how does this work"
