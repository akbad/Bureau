from concierge.classifier.fuzzy_commands import match_command_verb


class TestFuzzyCommandMatch:
    def test_exact_match(self):
        assert match_command_verb("pause the fitness probe") == "pause"

    def test_typo_match(self):
        assert match_command_verb("pase the fitness probe") == "pause"

    def test_no_match(self):
        assert match_command_verb("what should I eat for dinner") is None

    def test_multi_word_verb(self):
        assert match_command_verb("set up a weekly meal plan") == "set up"

    def test_below_threshold(self):
        assert match_command_verb("xyz the fitness probe") is None
