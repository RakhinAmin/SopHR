# fuzzy_matcher.py
from rapidfuzz import process, fuzz
from functools import lru_cache

class FuzzyMatcher:
    def __init__(self, rule_map, config, logger):
        self.rule_map = rule_map
        self.rule_keys = list(rule_map.keys())
        self.config = config
        self.logger = logger

    def hybrid_score(self, a, b):
        return 0.6 * fuzz.token_set_ratio(a, b) + 0.4 * fuzz.partial_ratio(a, b)

    @lru_cache(maxsize=1000)
    def match(self, desc_clean):
        if desc_clean in self.rule_map:
            return self.rule_map[desc_clean], 100.0, desc_clean
        try:
            result = process.extractOne(desc_clean, self.rule_keys, scorer=self.hybrid_score)
            if result is None or result[1] < self.config.match_threshold:
                return "Uncategorised", result[1] if result else 0.0, result[0] if result else ""
            return self.rule_map[result[0]], result[1], result[0]
        except Exception as e:
            self.logger.warning(f"Fuzzy match error: {e}")
            return "Uncategorised", 0.0, ""

    def suggest(self, desc_clean, num=3):
        matches = process.extract(desc_clean, self.rule_keys, scorer=self.hybrid_score, limit=num)
        suggestions = [self.rule_map[m[0]] for m in matches]
        scores = [round(m[1], 2) for m in matches]
        while len(suggestions) < num:
            suggestions.append("No Match")
            scores.append(0.0)
        return suggestions, scores
