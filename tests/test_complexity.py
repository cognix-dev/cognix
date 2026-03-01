"""Tests for semi_auto_engine.py complexity assessment fixes (c4ca527 + Fix E)

Covers:
- Removed overly generic complex keywords
- Retained specific complex keywords
- Heading count detection (code block exclusion)
- Spec size boost scoring
- Fix E: Boost cap (max +4.0)
"""

import re
import pytest
from cognix.semi_auto_engine import ComplexityAssessor


@pytest.fixture
def assessor():
    return ComplexityAssessor()


# ── Complex Keywords Refinement ──────────────────────────────────

class TestComplexKeywords:
    """Verify overly generic keywords were removed and specific ones remain."""

    def test_removed_generic_keywords(self, assessor):
        removed = ['particle', 'state machine', 'fsm', '60fps', 'frame rate',
                    'animation system']
        for kw in removed:
            assert kw not in assessor.complex_keywords, \
                f"'{kw}' should have been removed from complex_keywords"

    def test_retained_specific_keywords(self, assessor):
        retained = ['particle system', 'game engine', 'collision detection',
                     'physics engine', 'canvas game', 'webgl', 'game loop',
                     'custom animation', 'pathfinding', 'procedural generation']
        for kw in retained:
            assert kw in assessor.complex_keywords, \
                f"'{kw}' should still be in complex_keywords"


# ── Simple Keywords ──────────────────────────────────────────────

class TestSimpleKeywords:
    """Verify simple keywords are properly curated."""

    def test_hello_world_is_simple(self, assessor):
        assert 'hello world' in assessor.simple_keywords

    def test_generic_terms_not_in_simple(self, assessor):
        """Generic terms that appear in complex specs should not be simple."""
        generic = ['display', 'show', 'output', 'timer', 'counter', 'random']
        for kw in generic:
            assert kw not in assessor.simple_keywords, \
                f"'{kw}' should not be in simple_keywords (too generic)"


# ── Heading Count Detection ──────────────────────────────────────

class TestHeadingCount:
    """Heading count should exclude code blocks and handle edge cases."""

    def _count_headings(self, goal: str) -> int:
        """Replicate the heading count logic from assess_complexity."""
        clean_goal = re.sub(r'```[\s\S]*?```', '', goal)
        return len(re.findall(r'(?:^|\n)#{2,3}\s', clean_goal))

    def test_normal_headings(self):
        goal = "## Req 1\n### Sub 1\n### Sub 2\n## Req 2\n### Sub 3"
        assert self._count_headings(goal) == 5

    def test_code_block_headings_excluded(self):
        goal = "## Real Heading\n```python\n## comment\n### another\n```\n### Also Real"
        assert self._count_headings(goal) == 2

    def test_heading_at_start_of_string(self):
        goal = "## Start Heading\nSome text"
        assert self._count_headings(goal) == 1

    def test_no_headings(self):
        goal = "Just plain text without any markdown headings"
        assert self._count_headings(goal) == 0

    def test_h1_and_h4_not_counted(self):
        """Only ## and ### are counted, not # or ####."""
        goal = "# H1\n## H2\n### H3\n#### H4"
        assert self._count_headings(goal) == 2

    def test_multiple_code_blocks(self):
        goal = (
            "## Intro\n"
            "```\n## Not counted\n```\n"
            "### Middle\n"
            "```js\n### Also not counted\n```\n"
            "## End"
        )
        assert self._count_headings(goal) == 3


# ── Spec Size Boost ──────────────────────────────────────────────

class TestSpecSizeBoost:
    """Longer specs should receive higher complexity scores."""

    def test_short_spec_lower_score(self, assessor):
        short = "build a simple app"
        _, details_short = assessor.assess_complexity(short)

        long = "build a simple app " + "x" * 5000
        _, details_long = assessor.assess_complexity(long)

        assert details_long['score'] > details_short['score'], \
            "Longer spec should have higher complexity score"

    def test_1500_char_spec_boosts_score(self, assessor):
        # Use a neutral spec (no keywords) to isolate size effect
        base = "implement this feature "
        spec = base + "a" * (1500 - len(base))
        _, details = assessor.assess_complexity(spec)
        assert details['score'] >= 0.8, \
            f"1500+ char spec should get at least 0.8 boost, got {details['score']}"

    def test_5000_char_spec_boosts_more(self, assessor):
        base = "implement this feature "
        spec = base + "a" * (5000 - len(base))
        _, details = assessor.assess_complexity(spec)
        assert details['score'] >= 2.5, \
            f"5000+ char spec should get at least 2.5 boost, got {details['score']}"


# ── Integration: Complexity Classification ───────────────────────

class TestComplexityClassification:
    @pytest.fixture
    def clean_assessor(self):
        """Assessor with no existing files (isolates keyword logic)."""
        a = ComplexityAssessor()
        a.existing_files = {}
        return a

    def test_hello_world_matches_simple(self, assessor):
        """'hello world' should match simple keyword regardless of environment."""
        _, details = assessor.assess_complexity("hello world")
        assert "hello world" in details["simple_matches"]

    def test_hello_world_is_simple_clean(self, clean_assessor):
        """Without existing files, 'hello world' should be classified as simple."""
        complexity, _ = clean_assessor.assess_complexity("hello world")
        assert complexity == "simple"

    def test_game_engine_is_complex(self, assessor):
        complexity, _ = assessor.assess_complexity(
            "build a game engine with collision detection and physics simulation"
        )
        assert complexity == "complex"

    def test_state_machine_not_in_complex_keywords(self, assessor):
        """'state machine' was removed from complex keywords."""
        _, details = assessor.assess_complexity(
            "implement a state machine for form validation"
        )
        # 'state machine' should not appear in complex matches
        assert "state machine" not in details.get("complex_matches_filtered", [])
        assert "state machine" not in details.get("complex_matches_original", [])


# ── Fix E: Boost Cap ─────────────────────────────────────────────

class TestBoostCap:
    """Spec size boosts (goal_length + existing_files + headings) should cap at +4.0."""

    def test_boost_cap_in_source(self):
        """Verify _calculate_score caps spec-size boosts at 4.0."""
        import inspect
        source = inspect.getsource(ComplexityAssessor._calculate_score)
        assert "min(boost, 4.0)" in source, \
            "_calculate_score should cap spec-size boost at 4.0"

    def test_boost_cap_behavioral(self):
        """Adding more boost factors should not scale linearly past cap."""
        a = ComplexityAssessor()
        a.existing_files = {}

        # Both specs use many words to keep word_count score stable
        words = " ".join(["zzz"] * 30)  # 30 words (score += 1.0 for >= 20 words)

        # Spec A: only goal_length boost (pad to 5500+ chars → +2.5)
        spec_a = words + " " + "z" * (5500 - len(words) - 1)
        _, details_a = a.assess_complexity(spec_a)

        # Spec B: goal_length boost + headings boost
        headings = "\n".join([f"## zzz {i}" for i in range(12)])
        spec_b = words + "\n" + headings + "\n" + "z" * (5500 - len(words) - len(headings) - 2)
        _, details_b = a.assess_complexity(spec_b)

        # Without cap: headings would add +2.0 (total boost 4.5)
        # With cap: headings can only add +1.5 (total boost capped at 4.0)
        diff = details_b['score'] - details_a['score']
        assert diff <= 1.5 + 0.1, \
            f"Headings boost should be limited by cap (expected <=1.6, got {diff})"

    def test_boost_with_existing_files(self):
        """existing_files boost + goal_length boost should also be capped."""
        a = ComplexityAssessor()
        # Simulate large existing files (+2.5 boost)
        a.existing_files = {"big.txt": "y" * 6000}

        # Large goal (+2.5 boost) + headings (+2.0 boost)
        # Total uncapped: 7.0
        headings = "\n".join([f"## Section {i}" for i in range(12)])
        spec = headings + "\n" + "z" * 5000
        _, details = a.assess_complexity(spec)

        # Base score from existing_files environment may add some points,
        # but the 3 size boosts together should be capped at +4.0
        # We check that the score is less than what it would be uncapped
        assert details['score'] < 7.0, \
            f"Boost cap should prevent score from reaching 7.0+, got {details['score']}"
