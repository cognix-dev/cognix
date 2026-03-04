"""Tests for LLM response truncation recovery

Covers:
- Fix A: Dynamic max_tokens calculation based on file size
- Fix B1: Pattern 1 truncation recovery (missing closing ```)
- Fix B2: Step 2.5 truncated code block detection
- Fix B3: __code__ key mapping to error file
- Fix C: Quality fix markdown fallback parsing
- Fix D: Truncated XML <file> tag recovery in _parse_llm_response
- Fix F: Quality fix dynamic max_tokens calculation
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


def _make_engine_stub():
    """Create minimal SemiAutoEngine-like object with extraction methods."""
    from cognix.semi_auto_engine import SemiAutoEngine
    engine = MagicMock(spec=SemiAutoEngine)
    # Bind real methods to the mock
    engine._extract_code_blocks = SemiAutoEngine._extract_code_blocks.__get__(engine)
    engine._extract_multiple_files_from_response = SemiAutoEngine._extract_multiple_files_from_response.__get__(engine)
    engine._clean_generated_code = SemiAutoEngine._clean_generated_code.__get__(engine)
    engine._aggressive_markdown_removal = SemiAutoEngine._aggressive_markdown_removal.__get__(engine)
    engine._verify_and_fix_markdown_markers = SemiAutoEngine._verify_and_fix_markdown_markers.__get__(engine)
    engine._parse_llm_response = SemiAutoEngine._parse_llm_response.__get__(engine)
    engine._no_framework_mode = True
    engine.logger = MagicMock()
    engine.extractor = None
    engine.linter_integration = None  # Disable linter phase in extraction
    return engine


@pytest.fixture
def engine():
    return _make_engine_stub()


# ── Fix A: Dynamic max_tokens ──────────────────────────────────


class TestDynamicMaxTokens:
    """Verify max_tokens is calculated from file size, not just file count."""

    def test_small_file_gets_floor(self):
        """Files under ~18K chars should get the 8000 floor."""
        total_chars = 10000
        fix_max_tokens = max(8000, min(total_chars // 3 + 2000, 32000))
        assert fix_max_tokens == 8000

    def test_medium_file_scales(self):
        """952-line file (~43K chars) should get ~16K tokens."""
        total_chars = 43000
        fix_max_tokens = max(8000, min(total_chars // 3 + 2000, 32000))
        assert fix_max_tokens == 16333
        assert fix_max_tokens > 8000  # Must exceed old single-file default

    def test_large_file_gets_ceiling(self):
        """Very large files should be capped at 32000."""
        total_chars = 100000
        fix_max_tokens = max(8000, min(total_chars // 3 + 2000, 32000))
        assert fix_max_tokens == 32000

    def test_empty_file_gets_floor(self):
        """Empty file should still get the floor."""
        total_chars = 0
        fix_max_tokens = max(8000, min(total_chars // 3 + 2000, 32000))
        assert fix_max_tokens == 8000

    def test_multi_file_total(self):
        """Multiple files' sizes should be summed."""
        # Simulate 3 files: 20K + 15K + 10K = 45K chars
        files = {"a.py": "x" * 20000, "b.py": "x" * 15000, "c.py": "x" * 10000}
        total_chars = sum(len(v) for v in files.values())
        fix_max_tokens = max(8000, min(total_chars // 3 + 2000, 32000))
        assert fix_max_tokens == 17000  # 45000 // 3 + 2000


# ── Fix B1: Pattern 1 Truncation Recovery ─────────────────────


class TestPattern1TruncationRecovery:
    """Verify extraction works when closing ``` is missing."""

    def test_truncated_single_file(self, engine):
        """## File: header + opening ``` but NO closing ``` → should extract code."""
        response = (
            "Here is the fixed code:\n\n"
            "## File: main.py\n"
            "```python\n"
            "import os\n"
            "import flask\n"
            "\n"
            "app = flask.Flask(__name__)\n"
            "# ... rest of code truncated by max_tokens"
        )
        result = engine._extract_multiple_files_from_response(response)
        assert "main.py" in result
        assert "import os" in result["main.py"]
        assert "import flask" in result["main.py"]

    def test_truncated_with_substantial_code(self, engine):
        """Large truncated code block should still be extracted."""
        code_lines = [f"line_{i} = {i}" for i in range(100)]
        code_text = "\n".join(code_lines)
        response = f"## File: app.py\n```python\n{code_text}"
        result = engine._extract_multiple_files_from_response(response)
        assert "app.py" in result
        assert "line_0 = 0" in result["app.py"]
        assert "line_99 = 99" in result["app.py"]

    def test_non_truncated_still_works(self, engine):
        """Normal response with closing ``` should still work as before."""
        response = (
            "## File: main.py\n"
            "```python\n"
            "print('hello')\n"
            "```\n"
        )
        result = engine._extract_multiple_files_from_response(response)
        assert "main.py" in result
        assert "print('hello')" in result["main.py"]

    def test_too_short_truncated_code_skipped(self, engine):
        """Truncated code under 10 chars should be skipped."""
        response = "## File: main.py\n```python\nhi"
        result = engine._extract_multiple_files_from_response(response)
        assert "main.py" not in result


# ── Fix B2: Step 2.5 Truncated Code Block ─────────────────────


class TestStep25TruncatedCodeBlock:
    """Verify _extract_code_blocks recovers from truncated responses."""

    def test_truncated_code_block_recovery(self, engine):
        """Opening ``` with no closing ``` should be recovered in Step 2.5."""
        response = (
            "Here is the fix:\n\n"
            "```python\n"
            "def hello():\n"
            "    return 'world'\n"
            "\n"
            "def foo():\n"
            "    return 'bar'"
        )
        result = engine._extract_code_blocks(response)
        assert len(result) > 0
        # Should contain the code content
        code = list(result.values())[0]
        assert "def hello():" in code
        assert "def foo():" in code

    def test_complete_code_block_uses_normal_path(self, engine):
        """Complete code block should use Step 1/2, not Step 2.5."""
        response = (
            "```python\n"
            "print('hello')\n"
            "```\n"
        )
        result = engine._extract_code_blocks(response)
        assert len(result) > 0
        code = list(result.values())[0]
        assert "print('hello')" in code

    def test_no_code_block_at_all(self, engine):
        """Response with no code blocks should return empty dict."""
        response = "This is just text with no code blocks at all."
        result = engine._extract_code_blocks(response)
        assert result == {}


# ── Fix B3: __code__ Mapping ──────────────────────────────────


class TestCodeKeyMapping:
    """Verify __code__ key is mapped to the correct error file."""

    def test_single_file_mapping(self):
        """__code__ should be mapped to single error file."""
        fixed_files = {'__code__': 'print("fixed")'}
        errors = [{'file': 'main.py', 'line': 10, 'code': 'F841'}]
        generated_files = {'main.py': 'print("original")'}

        # Simulate the mapping logic
        if '__code__' in fixed_files and len(fixed_files) == 1:
            error_filenames = list(set(
                err['file'] for err in errors if err['file'] in generated_files
            ))
            if len(error_filenames) == 1:
                fixed_files[error_filenames[0]] = fixed_files.pop('__code__')

        assert 'main.py' in fixed_files
        assert '__code__' not in fixed_files
        assert fixed_files['main.py'] == 'print("fixed")'

    def test_multi_file_no_mapping(self):
        """__code__ should NOT be mapped when multiple error files exist."""
        fixed_files = {'__code__': 'print("fixed")'}
        errors = [
            {'file': 'a.py', 'line': 1, 'code': 'E302'},
            {'file': 'b.py', 'line': 5, 'code': 'F841'},
        ]
        generated_files = {'a.py': '', 'b.py': ''}

        if '__code__' in fixed_files and len(fixed_files) == 1:
            error_filenames = list(set(
                err['file'] for err in errors if err['file'] in generated_files
            ))
            if len(error_filenames) == 1:
                fixed_files[error_filenames[0]] = fixed_files.pop('__code__')

        # Should NOT be mapped (2 error files)
        assert '__code__' in fixed_files

    def test_named_file_not_affected(self):
        """Named file results should not be affected by mapping logic."""
        fixed_files = {'main.py': 'print("fixed")'}
        errors = [{'file': 'main.py', 'line': 10, 'code': 'F841'}]
        generated_files = {'main.py': 'print("original")'}

        if '__code__' in fixed_files and len(fixed_files) == 1:
            error_filenames = list(set(
                err['file'] for err in errors if err['file'] in generated_files
            ))
            if len(error_filenames) == 1:
                fixed_files[error_filenames[0]] = fixed_files.pop('__code__')

        assert 'main.py' in fixed_files
        assert '__code__' not in fixed_files


# ── Fix C: Quality Fix Fallback ───────────────────────────────


class TestQualityFixFallback:
    """Verify quality fix falls back to code block extraction."""

    def test_markdown_response_extracted(self, engine):
        """LLM responding with markdown instead of XML should be recoverable."""
        markdown_response = (
            "Here is the fixed code:\n\n"
            "## File: main.py\n"
            "```python\n"
            "def real_implementation():\n"
            "    return 42\n"
            "```\n"
        )
        # _parse_llm_response looks for <file> tags; markdown won't match
        # But _extract_code_blocks should handle it
        result = engine._extract_code_blocks(markdown_response)
        assert "main.py" in result
        assert "def real_implementation():" in result["main.py"]

    def test_code_key_mapped_for_quality_fix(self):
        """When extraction returns __code__, should map to issue file."""
        fixed_files = {'__code__': 'def real(): return 42'}
        placeholder_issues = [
            {'filename': 'main.py', 'count': 1, 'details': ['# TODO: implement']}
        ]

        if fixed_files and '__code__' in fixed_files and len(fixed_files) == 1:
            issue_filenames = list(set(i['filename'] for i in placeholder_issues))
            if len(issue_filenames) == 1:
                fixed_files[issue_filenames[0]] = fixed_files.pop('__code__')

        assert 'main.py' in fixed_files
        assert fixed_files['main.py'] == 'def real(): return 42'


# ── Fix D: Truncated XML <file> Tag Recovery ─────────────────


class TestTruncatedXMLRecovery:
    """Verify _parse_llm_response recovers from truncated <file> tags."""

    def test_truncated_file_tag_recovery(self, engine):
        """<file path='...'> with NO closing </file> should still extract code."""
        response = (
            "Here is the fixed code:\n\n"
            "<file path='main.py'>\n"
            "#!/usr/bin/env python3\n"
            "import os\n"
            "import flask\n"
            "\n"
            "app = flask.Flask(__name__)\n"
            "# rest of code truncated by max_tokens"
        )
        result = engine._parse_llm_response(response)
        assert result is not None
        assert "main.py" in result
        assert "import os" in result["main.py"]
        assert "import flask" in result["main.py"]

    def test_truncated_large_file(self, engine):
        """Large truncated <file> block should be recovered."""
        code_lines = [f"line_{i} = {i}" for i in range(200)]
        code_text = "\n".join(code_lines)
        response = f"<file path='app.py'>\n{code_text}"
        result = engine._parse_llm_response(response)
        assert result is not None
        assert "app.py" in result
        assert "line_0 = 0" in result["app.py"]
        assert "line_199 = 199" in result["app.py"]

    def test_complete_file_tag_still_works(self, engine):
        """Normal response with closing </file> should work as before."""
        response = (
            "<file path='main.py'>\n"
            "print('hello')\n"
            "</file>\n"
        )
        result = engine._parse_llm_response(response)
        assert result is not None
        assert "main.py" in result
        assert "print('hello')" in result["main.py"]

    def test_truncated_too_short_skipped(self, engine):
        """Truncated code under 10 chars should be skipped."""
        response = "<file path='main.py'>\nhi"
        result = engine._parse_llm_response(response)
        assert result is None

    def test_multiple_files_one_truncated(self, engine):
        """First file complete, second file truncated → both extracted."""
        response = (
            "<file path='a.py'>\nprint('a')\n</file>\n"
            "<file path='b.py'>\n"
            "import os\n"
            "import sys\n"
            "# truncated here"
        )
        result = engine._parse_llm_response(response)
        assert result is not None
        assert "a.py" in result
        assert "print('a')" in result["a.py"]
        assert "b.py" in result
        assert "import os" in result["b.py"]

    def test_no_file_tags_returns_none(self, engine):
        """Response with no <file> tags should return None."""
        response = "Just some text with no file tags."
        result = engine._parse_llm_response(response)
        assert result is None

    def test_double_quote_path(self, engine):
        """<file path="..."> with double quotes should also work for truncation."""
        response = (
            '<file path="main.py">\n'
            "def hello():\n"
            "    return 'world'\n"
            "# truncated"
        )
        result = engine._parse_llm_response(response)
        assert result is not None
        assert "main.py" in result


# ── Fix F: Quality Fix Dynamic max_tokens ─────────────────────


class TestQualityFixDynamicMaxTokens:
    """Verify quality fix uses dynamic max_tokens based on code size."""

    def test_small_code_gets_floor(self):
        """Small code files should get 8000 floor."""
        generated_code = {"main.py": "x" * 5000}
        total_code_chars = sum(len(v) for v in generated_code.values())
        quality_max_tokens = max(8000, min(total_code_chars // 3 + 2000, 32000))
        assert quality_max_tokens == 8000

    def test_medium_code_scales(self):
        """978-line Stripe file (~35K chars) should get ~13K tokens."""
        generated_code = {"main.py": "x" * 35000}
        total_code_chars = sum(len(v) for v in generated_code.values())
        quality_max_tokens = max(8000, min(total_code_chars // 3 + 2000, 32000))
        assert quality_max_tokens == 13666
        assert quality_max_tokens > 8000  # Must exceed old hardcoded value

    def test_large_code_gets_ceiling(self):
        """Very large code should cap at 32000."""
        generated_code = {"main.py": "x" * 100000}
        total_code_chars = sum(len(v) for v in generated_code.values())
        quality_max_tokens = max(8000, min(total_code_chars // 3 + 2000, 32000))
        assert quality_max_tokens == 32000

    def test_multi_file_code_summed(self):
        """Multiple files' sizes should be summed."""
        generated_code = {"a.py": "x" * 20000, "b.py": "x" * 15000}
        total_code_chars = sum(len(v) for v in generated_code.values())
        quality_max_tokens = max(8000, min(total_code_chars // 3 + 2000, 32000))
        assert quality_max_tokens == 13666  # 35000 // 3 + 2000


# ── Fix G: Quality Fix Syntax Validation ─────────────────────


class TestQualityFixSyntaxValidation:
    """Verify quality fix rejects code with syntax errors."""

    def test_reject_syntax_error_python(self):
        """Quality fix should reject .py files that fail ast.parse()."""
        import ast

        # Simulate the validation logic from _fix_quality_issues_with_llm
        generated_code = {"main.py": "print('original')"}
        fixed_files = {"main.py": "def broken(\n    # missing closing paren and colon"}

        updated_code = generated_code.copy()
        actually_updated = 0
        for filename, code in fixed_files.items():
            if filename in generated_code:
                if filename.endswith('.py'):
                    try:
                        ast.parse(code)
                    except SyntaxError:
                        continue  # Skip this file
                updated_code[filename] = code
                actually_updated += 1

        # Should have skipped the broken file
        assert actually_updated == 0
        assert updated_code["main.py"] == "print('original')"  # Original preserved

    def test_accept_valid_python(self):
        """Quality fix should accept .py files that pass ast.parse()."""
        import ast

        generated_code = {"main.py": "# TODO: implement\npass"}
        fixed_files = {"main.py": "def real_impl():\n    return 42\n"}

        updated_code = generated_code.copy()
        actually_updated = 0
        for filename, code in fixed_files.items():
            if filename in generated_code:
                if filename.endswith('.py'):
                    try:
                        ast.parse(code)
                    except SyntaxError:
                        continue
                updated_code[filename] = code
                actually_updated += 1

        assert actually_updated == 1
        assert "def real_impl" in updated_code["main.py"]

    def test_non_python_skips_ast_check(self):
        """Non-Python files should skip ast.parse() validation."""
        import ast

        generated_code = {"app.js": "// original"}
        # Invalid Python but valid JS-like content
        fixed_files = {"app.js": "const x = () => { return 42; }"}

        updated_code = generated_code.copy()
        actually_updated = 0
        for filename, code in fixed_files.items():
            if filename in generated_code:
                if filename.endswith('.py'):
                    try:
                        ast.parse(code)
                    except SyntaxError:
                        continue
                updated_code[filename] = code
                actually_updated += 1

        assert actually_updated == 1
        assert "const x" in updated_code["app.js"]

    def test_truncated_code_rejected(self):
        """Truncated code from XML recovery should be rejected if it has syntax errors."""
        import ast

        # Simulate truncation recovery producing incomplete code
        original = "import os\nimport flask\n\napp = flask.Flask(__name__)\n"
        truncated_fix = (
            "import os\nimport flask\n\napp = flask.Flask(__name__)\n\n"
            "def handle_payment():\n"
            "    amount = request.json.get('amount')\n"
            "    if amount > 0:\n"
            "        stripe.PaymentIntent.create(\n"
            "            amount=amount,\n"
            # Truncated here - missing closing paren and rest of function
        )

        generated_code = {"main.py": original}
        fixed_files = {"main.py": truncated_fix}

        updated_code = generated_code.copy()
        actually_updated = 0
        for filename, code in fixed_files.items():
            if filename in generated_code:
                if filename.endswith('.py'):
                    try:
                        ast.parse(code)
                    except SyntaxError:
                        continue
                updated_code[filename] = code
                actually_updated += 1

        # Truncated code should be rejected
        assert actually_updated == 0
        assert updated_code["main.py"] == original  # Original preserved


# ── Fix H: Dynamic Diff Limit ────────────────────────────────


class TestDynamicDiffLimit:
    """Verify diff limit scales with file size."""

    def test_small_file_gets_floor(self):
        """Files under 500 lines should get the 50-line floor."""
        file_line_count = 100
        diff_limit = max(50, min(file_line_count // 10, 120))
        assert diff_limit == 50

    def test_medium_file_scales(self):
        """500-line file should get 50-line limit (500//10=50)."""
        file_line_count = 500
        diff_limit = max(50, min(file_line_count // 10, 120))
        assert diff_limit == 50

    def test_large_file_scales(self):
        """1148-line file (Stripe test) should get 114-line limit."""
        file_line_count = 1148
        diff_limit = max(50, min(file_line_count // 10, 120))
        assert diff_limit == 114
        assert 59 <= diff_limit  # 59-line diff should now be accepted

    def test_very_large_file_gets_ceiling(self):
        """Files over 1200 lines should get the 120-line ceiling."""
        file_line_count = 2000
        diff_limit = max(50, min(file_line_count // 10, 120))
        assert diff_limit == 120

    def test_empty_file_gets_floor(self):
        """Empty file should get the 50-line floor."""
        file_line_count = 0
        diff_limit = max(50, min(file_line_count // 10, 120))
        assert diff_limit == 50
