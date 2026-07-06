import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import clean  # noqa: E402


def _red_rule():
    # Sheets round-trips BRIGHT_RED (0.91,0.26,0.21) at 8-bit: 232/66/54 over 255.
    return {"booleanRule": {
        "format": {"backgroundColor": {"red": 232 / 255, "green": 66 / 255, "blue": 54 / 255}},
        "condition": {"type": "CUSTOM_FORMULA",
                      "values": [{"userEnteredValue": '=$I2<>""'}]}}}


def _our_rule(formula):
    return {"booleanRule": {"condition": {"type": "CUSTOM_FORMULA",
            "values": [{"userEnteredValue": formula}]}}}


class TestColletter(unittest.TestCase):
    def test_city_columns_and_wraparound(self):
        self.assertEqual(clean.colletter(7), "G")   # City (Existing)
        self.assertEqual(clean.colletter(8), "H")   # City (New)
        self.assertEqual(clean.colletter(27), "AA")


class TestFormulaOf(unittest.TestCase):
    def test_reads_custom_formula(self):
        self.assertEqual(clean.formula_of(_our_rule('=$H2<>""')), '=$H2<>""')

    def test_non_custom_and_empty_return_none(self):
        self.assertIsNone(clean.formula_of({}))
        self.assertIsNone(clean.formula_of({"booleanRule": {"condition": {
            "type": "NUMBER_GREATER", "values": [{"userEnteredValue": "5"}]}}}))


class TestIsRed(unittest.TestCase):
    def test_matches_despite_8bit_quantization(self):
        # The whole point: exact float equality would FAIL here; _is_red must not.
        self.assertTrue(clean._is_red(_red_rule()))

    def test_rejects_other_colors_and_missing_bg(self):
        self.assertFalse(clean._is_red(_our_rule('=$H2<>""')))  # no backgroundColor
        self.assertFalse(clean._is_red({"booleanRule": {"format": {
            "backgroundColor": clean.VIOLET}}}))


class TestColorRulePlan(unittest.TestCase):
    def test_base_1_and_no_stale_when_only_red_present(self):
        stale, base = clean.color_rule_plan([_red_rule()])
        self.assertEqual(base, 1)      # our rules go BELOW the red rule
        self.assertEqual(stale, [])

    def test_base_0_when_no_red(self):
        _, base = clean.color_rule_plan([])
        self.assertEqual(base, 0)

    def test_stale_lists_only_our_rules_descending(self):
        cfs = [_red_rule(), _our_rule(clean.VIOLET_FORMULA), _our_rule(clean.AMBER_FORMULA)]
        stale, base = clean.color_rule_plan(cfs)
        self.assertEqual(stale, [2, 1])   # descending, red at index 0 untouched
        self.assertEqual(base, 1)

    def test_base_follows_red_when_not_first(self):
        # red is NOT at index 0 (a Status color rule precedes it); we must still
        # insert just below red, not at index 1.
        other = _our_rule('=$A2="In progress"')   # not ours, not red -> not stale
        stale, base = clean.color_rule_plan([other, _red_rule()])
        self.assertEqual(stale, [])
        self.assertEqual(base, 2)                  # just below red at index 1

    def test_base_accounts_for_stale_deleted_above_red(self):
        # a stale rule sits above red; deleting it shifts red up by one.
        stale, base = clean.color_rule_plan([_our_rule(clean.AMBER_FORMULA), _red_rule()])
        self.assertEqual(stale, [0])
        self.assertEqual(base, 1)                  # red -> index 0 after delete, insert at 1


class TestFormulaConsistency(unittest.TestCase):
    def test_detected_set_equals_installed_formulas(self):
        # Guards the idempotency contract: the set used to find our rules must
        # cover the formulas we install (plus retired ones, matched as stale).
        self.assertEqual(clean.COLOR_FORMULAS,
                         {clean.VIOLET_FORMULA, clean.AMBER_FORMULA, clean.GREEN_FORMULA})
        self.assertEqual(clean.STALE_COLOR_FORMULAS,
                         clean.COLOR_FORMULAS | clean.LEGACY_COLOR_FORMULAS)
        self.assertEqual(clean.AMBER_FORMULA, '=$H2<>""')
        # Green must reject ANY "Other..." placeholder, not just the bare "Other".
        self.assertEqual(clean.GREEN_FORMULA, '=AND($G2<>"",LEFT($G2,5)<>"Other")')

    def test_legacy_green_rule_matched_stale(self):
        # A rule installed by an earlier release (old green formula) must be
        # deleted on refresh, not left to stack next to the new one.
        legacy = _our_rule('=AND($G2<>"",$G2<>"Other")')
        stale, base = clean.color_rule_plan([_red_rule(), legacy])
        self.assertEqual(stale, [1])
        self.assertEqual(base, 1)


if __name__ == "__main__":
    unittest.main()
