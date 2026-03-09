"""Tests for G-33: HTML Accessibility Check

Covers:
- A-1: _validate_accessibility — img alt 属性欠落検出
- A-2: _validate_accessibility — html lang 属性欠落検出
- A-3: _validate_accessibility — heading 階層スキップ検出
- A-4: _validate_accessibility — form input の label 欠落検出
- A-5: _validate_accessibility — 空ボタン・空リンク検出
- A-6: _validate_accessibility — tabindex > 0 検出
- Auto-fix: _auto_fix_accessibility — A-1, A-2, A-6 の機械的修正
"""

import sys
import os
import pytest
from unittest.mock import MagicMock

# Allow standalone execution
if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_engine_stub():
    """Create a minimal SemiAutoEngine-like object with G-33 methods bound."""
    from cognix.semi_auto_engine import SemiAutoEngine

    engine = MagicMock(spec=SemiAutoEngine)

    engine._validate_accessibility = (
        SemiAutoEngine._validate_accessibility.__get__(engine)
    )
    engine._auto_fix_accessibility = (
        SemiAutoEngine._auto_fix_accessibility.__get__(engine)
    )

    engine.logger = MagicMock()
    return engine


@pytest.fixture
def engine():
    return _make_engine_stub()


# ======================================================================
# A-1: img alt 属性欠落
# ======================================================================


class TestA1ImgAlt:
    """Verify detection and auto-fix of missing alt attribute on <img> tags."""

    def test_img_with_alt_no_issue(self, engine):
        """<img> with alt attribute should produce no issues."""
        files = {
            "index.html": '<img src="logo.png" alt="Logo">',
        }
        result = engine._validate_accessibility(files)
        alt_issues = [i for i in result if i["type"] == "a11y_missing_alt"]
        assert len(alt_issues) == 0

    def test_img_missing_alt_detected(self, engine):
        """<img> without alt should be detected as fixable issue."""
        files = {
            "index.html": '<html lang="en"><body><img src="photo.jpg"></body></html>',
        }
        result = engine._validate_accessibility(files)
        alt_issues = [i for i in result if i["type"] == "a11y_missing_alt"]
        assert len(alt_issues) == 1
        assert alt_issues[0]["fixable"] is True
        assert alt_issues[0]["file"] == "index.html"

    def test_img_decorative_role_presentation_excluded(self, engine):
        """<img> with role="presentation" should not be flagged."""
        files = {
            "index.html": '<img src="spacer.gif" role="presentation">',
        }
        result = engine._validate_accessibility(files)
        alt_issues = [i for i in result if i["type"] == "a11y_missing_alt"]
        assert len(alt_issues) == 0

    def test_img_decorative_role_none_excluded(self, engine):
        """<img> with role="none" should not be flagged."""
        files = {
            "index.html": '<img src="bg.png" role="none">',
        }
        result = engine._validate_accessibility(files)
        alt_issues = [i for i in result if i["type"] == "a11y_missing_alt"]
        assert len(alt_issues) == 0

    def test_img_empty_alt_excluded(self, engine):
        """<img> with alt="" (intentionally decorative) should not be flagged."""
        files = {
            "index.html": '<img src="border.png" alt="">',
        }
        result = engine._validate_accessibility(files)
        alt_issues = [i for i in result if i["type"] == "a11y_missing_alt"]
        assert len(alt_issues) == 0

    def test_img_multiple_some_missing(self, engine):
        """Multiple <img> tags, only those without alt should be flagged."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<img src="a.png" alt="A">'
                '<img src="b.png">'
                '<img src="c.png" alt="C">'
                '<img src="d.png">'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        alt_issues = [i for i in result if i["type"] == "a11y_missing_alt"]
        assert len(alt_issues) == 2

    def test_img_self_closing_detected(self, engine):
        """Self-closing <img /> without alt should be detected."""
        files = {
            "index.html": '<html lang="en"><body><img src="icon.svg" /></body></html>',
        }
        result = engine._validate_accessibility(files)
        alt_issues = [i for i in result if i["type"] == "a11y_missing_alt"]
        assert len(alt_issues) == 1

    def test_autofix_img_alt_from_src(self, engine):
        """Auto-fix should add alt inferred from src filename."""
        files = {
            "index.html": '<img src="images/hero-banner.png">',
        }
        issues = engine._validate_accessibility(files)
        fixable = [i for i in issues if i.get("fixable")]
        files = engine._auto_fix_accessibility(fixable, files)
        assert 'alt="hero banner"' in files["index.html"]

    def test_autofix_img_alt_no_src(self, engine):
        """Auto-fix should add alt="" when no src attribute exists."""
        files = {
            "index.html": '<img class="placeholder">',
        }
        issues = engine._validate_accessibility(files)
        fixable = [i for i in issues if i.get("fixable")]
        files = engine._auto_fix_accessibility(fixable, files)
        assert 'alt=""' in files["index.html"]

    def test_autofix_img_alt_preserves_other_attrs(self, engine):
        """Auto-fix should not remove existing attributes."""
        files = {
            "index.html": '<img src="photo.jpg" class="rounded" width="100">',
        }
        issues = engine._validate_accessibility(files)
        fixable = [i for i in issues if i.get("fixable")]
        files = engine._auto_fix_accessibility(fixable, files)
        content = files["index.html"]
        assert 'alt="photo"' in content
        assert 'class="rounded"' in content
        assert 'width="100"' in content

    def test_autofix_img_alt_resolved_on_revalidation(self, engine):
        """After auto-fix, re-validation should find no fixable alt issues."""
        files = {
            "index.html": '<img src="logo.png"><img src="bg.svg">',
        }
        issues = engine._validate_accessibility(files)
        fixable = [i for i in issues if i.get("fixable")]
        files = engine._auto_fix_accessibility(fixable, files)
        recheck = engine._validate_accessibility(files)
        alt_issues = [i for i in recheck if i["type"] == "a11y_missing_alt"]
        assert len(alt_issues) == 0


# ======================================================================
# A-2: html lang 属性欠落
# ======================================================================


class TestA2HtmlLang:
    """Verify detection and auto-fix of missing lang attribute on <html> tag."""

    def test_html_with_lang_no_issue(self, engine):
        """<html lang="en"> should produce no issue."""
        files = {
            "index.html": '<html lang="en"><head></head><body></body></html>',
        }
        result = engine._validate_accessibility(files)
        lang_issues = [i for i in result if i["type"] == "a11y_missing_lang"]
        assert len(lang_issues) == 0

    def test_html_missing_lang_detected(self, engine):
        """<html> without lang should be detected."""
        files = {
            "index.html": '<html><head></head><body></body></html>',
        }
        result = engine._validate_accessibility(files)
        lang_issues = [i for i in result if i["type"] == "a11y_missing_lang"]
        assert len(lang_issues) == 1
        assert lang_issues[0]["fixable"] is True

    def test_html_with_other_attrs_no_lang(self, engine):
        """<html class="no-js"> without lang should be detected."""
        files = {
            "index.html": '<html class="no-js"><body>Hello</body></html>',
        }
        result = engine._validate_accessibility(files)
        lang_issues = [i for i in result if i["type"] == "a11y_missing_lang"]
        assert len(lang_issues) == 1

    def test_autofix_lang_en_for_english_content(self, engine):
        """Auto-fix should add lang="en" for English content."""
        files = {
            "index.html": '<html><body><h1>Hello World</h1></body></html>',
        }
        issues = engine._validate_accessibility(files)
        fixable = [i for i in issues if i.get("fixable")]
        files = engine._auto_fix_accessibility(fixable, files)
        assert 'lang="en"' in files["index.html"]

    def test_autofix_lang_ja_for_japanese_content(self, engine):
        """Auto-fix should add lang="ja" for content with CJK characters."""
        files = {
            "index.html": '<html><body><h1>メモ帳アプリ</h1></body></html>',
        }
        issues = engine._validate_accessibility(files)
        fixable = [i for i in issues if i.get("fixable")]
        files = engine._auto_fix_accessibility(fixable, files)
        assert 'lang="ja"' in files["index.html"]

    def test_autofix_lang_resolved_on_revalidation(self, engine):
        """After auto-fix, re-validation should find no lang issues."""
        files = {
            "index.html": '<html><body>Content</body></html>',
        }
        issues = engine._validate_accessibility(files)
        fixable = [i for i in issues if i.get("fixable")]
        files = engine._auto_fix_accessibility(fixable, files)
        recheck = engine._validate_accessibility(files)
        lang_issues = [i for i in recheck if i["type"] == "a11y_missing_lang"]
        assert len(lang_issues) == 0


# ======================================================================
# A-3: heading 階層スキップ
# ======================================================================


class TestA3HeadingHierarchy:
    """Verify detection of heading level skips."""

    def test_correct_hierarchy_no_issue(self, engine):
        """h1 → h2 → h3 should produce no issues."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<h1>Title</h1>'
                '<h2>Section</h2>'
                '<h3>Subsection</h3>'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        skip_issues = [i for i in result if i["type"] == "a11y_heading_skip"]
        assert len(skip_issues) == 0

    def test_h1_to_h3_skip_detected(self, engine):
        """h1 → h3 (skipping h2) should be detected."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<h1>Title</h1>'
                '<h3>Subsection</h3>'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        skip_issues = [i for i in result if i["type"] == "a11y_heading_skip"]
        assert len(skip_issues) == 1
        assert skip_issues[0]["fixable"] is False

    def test_h2_to_h5_skip_detected(self, engine):
        """h2 → h5 (skipping h3, h4) should be detected."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<h2>Section</h2>'
                '<h5>Deep sub</h5>'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        skip_issues = [i for i in result if i["type"] == "a11y_heading_skip"]
        assert len(skip_issues) == 1

    def test_decreasing_level_no_skip(self, engine):
        """h3 → h1 (going back up) should NOT be flagged as a skip."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<h1>Title</h1>'
                '<h2>Section</h2>'
                '<h3>Sub</h3>'
                '<h1>New Section</h1>'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        skip_issues = [i for i in result if i["type"] == "a11y_heading_skip"]
        assert len(skip_issues) == 0

    def test_single_heading_no_skip(self, engine):
        """A single heading should never produce a skip issue."""
        files = {
            "index.html": '<html lang="en"><body><h3>Only heading</h3></body></html>',
        }
        result = engine._validate_accessibility(files)
        skip_issues = [i for i in result if i["type"] == "a11y_heading_skip"]
        assert len(skip_issues) == 0


# ======================================================================
# A-4: form input の label 欠落
# ======================================================================


class TestA4FormLabels:
    """Verify detection of form elements without associated labels."""

    def test_input_with_label_for_no_issue(self, engine):
        """<input> with matching <label for> should produce no issue."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<label for="name">Name</label>'
                '<input id="name" type="text">'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        label_issues = [i for i in result if i["type"] == "a11y_missing_label"]
        assert len(label_issues) == 0

    def test_input_with_aria_label_no_issue(self, engine):
        """<input> with aria-label should produce no issue."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<input type="text" aria-label="Search">'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        label_issues = [i for i in result if i["type"] == "a11y_missing_label"]
        assert len(label_issues) == 0

    def test_input_with_title_no_issue(self, engine):
        """<input> with title attribute should produce no issue."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<input type="text" title="Enter your name">'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        label_issues = [i for i in result if i["type"] == "a11y_missing_label"]
        assert len(label_issues) == 0

    def test_input_hidden_excluded(self, engine):
        """<input type="hidden"> should not require a label."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<input type="hidden" name="csrf_token" value="abc">'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        label_issues = [i for i in result if i["type"] == "a11y_missing_label"]
        assert len(label_issues) == 0

    def test_input_submit_excluded(self, engine):
        """<input type="submit"> should not require a label."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<input type="submit" value="Send">'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        label_issues = [i for i in result if i["type"] == "a11y_missing_label"]
        assert len(label_issues) == 0

    def test_input_no_label_detected(self, engine):
        """<input> without any label mechanism should be detected."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<input type="text" name="email">'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        label_issues = [i for i in result if i["type"] == "a11y_missing_label"]
        assert len(label_issues) == 1
        assert label_issues[0]["fixable"] is False

    def test_select_no_label_detected(self, engine):
        """<select> without label should be detected."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<select name="country"><option>Japan</option></select>'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        label_issues = [i for i in result if i["type"] == "a11y_missing_label"]
        assert len(label_issues) == 1

    def test_textarea_no_label_detected(self, engine):
        """<textarea> without label should be detected."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<textarea name="comment"></textarea>'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        label_issues = [i for i in result if i["type"] == "a11y_missing_label"]
        assert len(label_issues) == 1


# ======================================================================
# A-5: 空ボタン・空リンク
# ======================================================================


class TestA5EmptyInteractive:
    """Verify detection of empty buttons and links."""

    def test_button_with_text_no_issue(self, engine):
        """<button> with text content should produce no issue."""
        files = {
            "index.html": '<html lang="en"><body><button>Click me</button></body></html>',
        }
        result = engine._validate_accessibility(files)
        btn_issues = [i for i in result if i["type"] == "a11y_empty_button"]
        assert len(btn_issues) == 0

    def test_button_with_aria_label_no_issue(self, engine):
        """<button> with aria-label but no text should produce no issue."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<button aria-label="Close"><span class="icon-x"></span></button>'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        btn_issues = [i for i in result if i["type"] == "a11y_empty_button"]
        assert len(btn_issues) == 0

    def test_button_with_title_no_issue(self, engine):
        """<button> with title but no text should produce no issue."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<button title="Menu"><i class="hamburger"></i></button>'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        btn_issues = [i for i in result if i["type"] == "a11y_empty_button"]
        assert len(btn_issues) == 0

    def test_empty_button_detected(self, engine):
        """<button> with only HTML tags (no text) should be detected."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<button><i class="icon"></i></button>'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        btn_issues = [i for i in result if i["type"] == "a11y_empty_button"]
        assert len(btn_issues) == 1
        assert btn_issues[0]["fixable"] is False

    def test_completely_empty_button_detected(self, engine):
        """<button></button> should be detected."""
        files = {
            "index.html": '<html lang="en"><body><button></button></body></html>',
        }
        result = engine._validate_accessibility(files)
        btn_issues = [i for i in result if i["type"] == "a11y_empty_button"]
        assert len(btn_issues) == 1

    def test_link_with_text_no_issue(self, engine):
        """<a> with text content should produce no issue."""
        files = {
            "index.html": '<html lang="en"><body><a href="/">Home</a></body></html>',
        }
        result = engine._validate_accessibility(files)
        link_issues = [i for i in result if i["type"] == "a11y_empty_link"]
        assert len(link_issues) == 0

    def test_empty_link_detected(self, engine):
        """<a> with only an image (no text, no aria-label) should be detected."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<a href="/"><img src="logo.png" alt="Logo"></a>'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        link_issues = [i for i in result if i["type"] == "a11y_empty_link"]
        # img tag is HTML, text_only after stripping tags is empty
        assert len(link_issues) == 1

    def test_link_with_aria_label_no_issue(self, engine):
        """<a> with aria-label should produce no issue even without text."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<a href="/" aria-label="Home"><img src="logo.png"></a>'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        link_issues = [i for i in result if i["type"] == "a11y_empty_link"]
        assert len(link_issues) == 0


# ======================================================================
# A-6: tabindex > 0
# ======================================================================


class TestA6Tabindex:
    """Verify detection and auto-fix of positive tabindex values."""

    def test_tabindex_zero_no_issue(self, engine):
        """tabindex="0" should produce no issue."""
        files = {
            "index.html": '<html lang="en"><body><div tabindex="0">Focus me</div></body></html>',
        }
        result = engine._validate_accessibility(files)
        tab_issues = [i for i in result if i["type"] == "a11y_positive_tabindex"]
        assert len(tab_issues) == 0

    def test_tabindex_negative_no_issue(self, engine):
        """tabindex="-1" should produce no issue."""
        files = {
            "index.html": '<html lang="en"><body><div tabindex="-1">Hidden</div></body></html>',
        }
        result = engine._validate_accessibility(files)
        tab_issues = [i for i in result if i["type"] == "a11y_positive_tabindex"]
        assert len(tab_issues) == 0

    def test_tabindex_positive_detected(self, engine):
        """tabindex="5" should be detected as fixable issue."""
        files = {
            "index.html": '<html lang="en"><body><input tabindex="5" type="text"></body></html>',
        }
        result = engine._validate_accessibility(files)
        tab_issues = [i for i in result if i["type"] == "a11y_positive_tabindex"]
        assert len(tab_issues) == 1
        assert tab_issues[0]["fixable"] is True
        assert tab_issues[0]["original_value"] == "5"

    def test_multiple_positive_tabindex(self, engine):
        """Multiple positive tabindex values should all be detected."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<input tabindex="3" type="text">'
                '<input tabindex="1" type="text">'
                '<input tabindex="0" type="text">'
                '</body></html>'
            ),
        }
        result = engine._validate_accessibility(files)
        tab_issues = [i for i in result if i["type"] == "a11y_positive_tabindex"]
        assert len(tab_issues) == 2

    def test_autofix_tabindex_to_zero(self, engine):
        """Auto-fix should change tabindex="5" to tabindex="0"."""
        files = {
            "index.html": '<html lang="en"><body><div tabindex="5">Div</div></body></html>',
        }
        issues = engine._validate_accessibility(files)
        fixable = [i for i in issues if i.get("fixable")]
        files = engine._auto_fix_accessibility(fixable, files)
        assert 'tabindex="0"' in files["index.html"]
        assert 'tabindex="5"' not in files["index.html"]

    def test_autofix_tabindex_resolved_on_revalidation(self, engine):
        """After auto-fix, re-validation should find no tabindex issues."""
        files = {
            "index.html": (
                '<html lang="en"><body>'
                '<input tabindex="2">'
                '<input tabindex="10">'
                '</body></html>'
            ),
        }
        issues = engine._validate_accessibility(files)
        fixable = [i for i in issues if i.get("fixable")]
        files = engine._auto_fix_accessibility(fixable, files)
        recheck = engine._validate_accessibility(files)
        tab_issues = [i for i in recheck if i["type"] == "a11y_positive_tabindex"]
        assert len(tab_issues) == 0


# ======================================================================
# Non-HTML files should be skipped
# ======================================================================


class TestNonHtmlSkipped:
    """Verify that non-HTML files are completely ignored."""

    def test_python_file_ignored(self, engine):
        """Python files should produce no accessibility issues."""
        files = {
            "app.py": '<img src="test.png">',
        }
        result = engine._validate_accessibility(files)
        assert len(result) == 0

    def test_css_file_ignored(self, engine):
        """CSS files should produce no accessibility issues."""
        files = {
            "style.css": '<img src="test.png">',
        }
        result = engine._validate_accessibility(files)
        assert len(result) == 0

    def test_js_file_ignored(self, engine):
        """JavaScript files should produce no accessibility issues."""
        files = {
            "app.js": 'document.write("<img src=x>");',
        }
        result = engine._validate_accessibility(files)
        assert len(result) == 0

    def test_htm_extension_included(self, engine):
        """Files with .htm extension should be checked."""
        files = {
            "page.htm": '<html><body><img src="pic.png"></body></html>',
        }
        result = engine._validate_accessibility(files)
        assert len(result) >= 1  # At least missing lang and missing alt


# ======================================================================
# Combined scenario: full-page integration test
# ======================================================================


class TestCombinedScenario:
    """Verify full-page scenarios with multiple issue types."""

    def test_clean_html_no_issues(self, engine):
        """A well-formed accessible HTML should produce no fixable issues."""
        files = {
            "index.html": (
                '<!DOCTYPE html>\n'
                '<html lang="en">\n'
                '<head><title>Test</title></head>\n'
                '<body>\n'
                '<h1>Title</h1>\n'
                '<h2>Section</h2>\n'
                '<img src="logo.png" alt="Logo">\n'
                '<form>\n'
                '  <label for="email">Email</label>\n'
                '  <input id="email" type="email">\n'
                '  <input type="submit" value="Send">\n'
                '</form>\n'
                '<button>Click me</button>\n'
                '<a href="/">Home</a>\n'
                '</body>\n'
                '</html>'
            ),
        }
        result = engine._validate_accessibility(files)
        fixable = [i for i in result if i.get("fixable")]
        assert len(fixable) == 0

    def test_multiple_issues_all_types(self, engine):
        """HTML with all issue types should detect them all."""
        files = {
            "index.html": (
                '<html>\n'
                '<body>\n'
                '<h1>Title</h1>\n'
                '<h3>Skipped h2</h3>\n'
                '<img src="photo.jpg">\n'
                '<input type="text" name="q">\n'
                '<button><i class="icon"></i></button>\n'
                '<a href="/"><img src="x.png" alt=""></a>\n'
                '<div tabindex="3">Custom</div>\n'
                '</body>\n'
                '</html>'
            ),
        }
        result = engine._validate_accessibility(files)
        types = [i["type"] for i in result]
        assert "a11y_missing_lang" in types
        assert "a11y_missing_alt" in types
        assert "a11y_heading_skip" in types
        assert "a11y_missing_label" in types
        assert "a11y_empty_button" in types
        assert "a11y_positive_tabindex" in types

    def test_full_autofix_cycle(self, engine):
        """Full detect → fix → re-validate cycle should resolve all fixable issues."""
        files = {
            "index.html": (
                '<html>\n'
                '<body>\n'
                '<img src="images/hero-bg.png">\n'
                '<img src="icons/close.svg">\n'
                '<div tabindex="2">Tab</div>\n'
                '<button tabindex="7">OK</button>\n'
                '</body>\n'
                '</html>'
            ),
        }
        # Detect
        issues = engine._validate_accessibility(files)
        fixable = [i for i in issues if i.get("fixable")]
        assert len(fixable) >= 4  # 2 alt + 1 lang + 2 tabindex

        # Fix
        files = engine._auto_fix_accessibility(fixable, files)

        # Re-validate
        remaining = engine._validate_accessibility(files)
        remaining_fixable = [i for i in remaining if i.get("fixable")]
        assert len(remaining_fixable) == 0

        # Verify content
        content = files["index.html"]
        assert 'lang="en"' in content
        assert 'alt="hero bg"' in content
        assert 'alt="close"' in content
        assert 'tabindex="0"' in content
        assert 'tabindex="2"' not in content
        assert 'tabindex="7"' not in content

    def test_line_numbers_correct(self, engine):
        """Issue line numbers should match the actual position in content."""
        files = {
            "index.html": (
                '<html>\n'            # L1 — lang missing
                '<body>\n'            # L2
                '<p>Text</p>\n'       # L3
                '<img src="x.png">\n' # L4 — alt missing
                '</body>\n'           # L5
                '</html>'             # L6
            ),
        }
        result = engine._validate_accessibility(files)
        lang_issue = [i for i in result if i["type"] == "a11y_missing_lang"][0]
        alt_issue = [i for i in result if i["type"] == "a11y_missing_alt"][0]
        assert lang_issue["line"] == 1
        assert alt_issue["line"] == 4
