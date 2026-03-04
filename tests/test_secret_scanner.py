"""Tests for cognix/secret_scanner.py — SecretScanner

Covers:
- 17 service-specific pattern detection (AWS, GitHub, Stripe, Slack, etc.)
- False-positive exclusions (test files, comment lines, env var usage)
- Language-specific fix suggestions
- camelCase → UPPER_SNAKE_CASE conversion
"""

import re
import pytest
from cognix.secret_scanner import SecretScanner


@pytest.fixture
def scanner():
    return SecretScanner()


# ── Pattern Detection ────────────────────────────────────────────


class TestSecretScannerPatterns:
    """Verify each pattern detects the corresponding secret type."""

    def test_aws_access_key(self, scanner):
        files = {"config.py": 'aws_key = "AKIAIOSFODNN7EXAMPLE"'}
        issues = scanner.scan(files)
        assert len(issues) >= 1
        assert any(i["pattern_name"] == "AWS Access Key" for i in issues)

    def test_aws_secret_key(self, scanner):
        files = {"config.py": 'aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"'}
        issues = scanner.scan(files)
        assert any(i["pattern_name"] == "AWS Secret Key" for i in issues)

    def test_github_pat_classic(self, scanner):
        files = {"deploy.py": 'token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef1234"'}
        issues = scanner.scan(files)
        assert any(i["pattern_name"] == "GitHub PAT (Classic)" for i in issues)

    def test_github_oauth(self, scanner):
        files = {"auth.py": 'oauth = "gho_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef1234"'}
        issues = scanner.scan(files)
        assert any(i["pattern_name"] == "GitHub OAuth Token" for i in issues)

    def test_github_fine_grained(self, scanner):
        token = "github_pat_" + "A" * 82
        files = {"ci.py": f'token = "{token}"'}
        issues = scanner.scan(files)
        assert any(i["pattern_name"] == "GitHub Fine-grained PAT" for i in issues)

    def test_gitlab_pat(self, scanner):
        files = {"config.py": 'token = "glpat-ABCDEFGHIJKLMNOPQRSTUV"'}
        issues = scanner.scan(files)
        assert any(i["pattern_name"] == "GitLab PAT" for i in issues)

    def test_stripe_live_secret(self, scanner):
        key = "sk_" + "live_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ" + "ab"
        files = {"billing.py": f'key = "{key}"'}
        issues = scanner.scan(files)
        names = [i["pattern_name"] for i in issues]
        assert "Stripe Live Secret Key" in names

    def test_stripe_live_publishable_severity(self, scanner):
        key = "pk_" + "live_" + "ABCDEFGHIJKLMNOPQRSTUVWXYZ" + "ab"
        files = {"billing.py": f'key = "{key}"'}
        issues = scanner.scan(files)
        stripe_issues = [i for i in issues if i["pattern_name"] == "Stripe Live Publishable Key"]
        assert len(stripe_issues) >= 1
        assert stripe_issues[0]["severity"] == "high"

    def test_slack_token(self, scanner):
        files = {"bot.py": 'token = "xoxb-1234567890-abcdefghij"'}
        issues = scanner.scan(files)
        assert any(i["pattern_name"] == "Slack Token" for i in issues)

    def test_google_api_key(self, scanner):
        key = "AIza" + "A" * 35
        files = {"maps.py": f'api_key = "{key}"'}
        issues = scanner.scan(files)
        assert any(i["pattern_name"] == "Google API Key" for i in issues)

    def test_sendgrid_key(self, scanner):
        key = "SG." + "A" * 22 + "." + "B" * 43
        files = {"email.py": f'sg_key = "{key}"'}
        issues = scanner.scan(files)
        assert any(i["pattern_name"] == "SendGrid API Key" for i in issues)

    def test_npm_token(self, scanner):
        token = "npm_" + "A" * 36
        files = {"config.py": f'NPM_TOKEN = "{token}"'}
        issues = scanner.scan(files)
        assert any(i["pattern_name"] == "npm Token" for i in issues)

    def test_pypi_token(self, scanner):
        token = "pypi-" + "A" * 60
        files = {"setup.py": f'token = "{token}"'}
        issues = scanner.scan(files)
        assert any(i["pattern_name"] == "PyPI Token" for i in issues)

    def test_private_key_block(self, scanner):
        files = {"key.pem": "-----BEGIN RSA PRIVATE KEY-----\nMIIEow..."}
        issues = scanner.scan(files)
        assert any(i["pattern_name"] == "Private Key Block" for i in issues)

    def test_private_key_ec(self, scanner):
        files = {"key.pem": "-----BEGIN EC PRIVATE KEY-----\nMHQC..."}
        issues = scanner.scan(files)
        assert any(i["pattern_name"] == "Private Key Block" for i in issues)

    def test_hardcoded_password(self, scanner):
        files = {"db.py": 'password = "MyS3cureP@ssw0rd!"'}
        issues = scanner.scan(files)
        assert any(i["pattern_name"] == "Hardcoded Password" for i in issues)

    def test_hardcoded_api_key(self, scanner):
        files = {"service.py": 'api_key = "ABCDEFGHIJKLMNOP1234"'}
        issues = scanner.scan(files)
        assert any(i["pattern_name"] == "Hardcoded API Key" for i in issues)

    def test_issue_structure(self, scanner):
        """Verify returned issue dict has all expected keys."""
        files = {"config.py": 'token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef1234"'}
        issues = scanner.scan(files)
        assert len(issues) >= 1
        issue = issues[0]
        assert "file" in issue
        assert "line" in issue
        assert "type" in issue and issue["type"] == 19
        assert "pattern_name" in issue
        assert "severity" in issue
        assert "description" in issue
        assert "fix" in issue
        assert "matched_text" in issue


# ── Exclusion / False Positive Prevention ─────────────────────


class TestSecretScannerExclusions:
    """Verify false-positive filtering logic."""

    def test_skip_test_file(self, scanner):
        files = {"test_config.py": 'api_key = "AKIAIOSFODNN7EXAMPLE"'}
        issues = scanner.scan(files)
        assert len(issues) == 0

    def test_skip_spec_file(self, scanner):
        files = {"auth.spec.ts": 'const token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef1234"'}
        issues = scanner.scan(files)
        assert len(issues) == 0

    def test_skip_example_file(self, scanner):
        files = {"example_settings.py": 'password = "MyS3cureP@ssw0rd!"'}
        issues = scanner.scan(files)
        assert len(issues) == 0

    def test_skip_markdown(self, scanner):
        files = {"README.md": 'api_key = "AKIAIOSFODNN7EXAMPLE"'}
        issues = scanner.scan(files)
        assert len(issues) == 0

    def test_skip_comment_line_python(self, scanner):
        files = {"config.py": '# api_key = "ABCDEFGHIJKLMNOP1234"'}
        issues = scanner.scan(files)
        # Should not detect secrets in comments
        api_key_issues = [i for i in issues if i["pattern_name"] == "Hardcoded API Key"]
        assert len(api_key_issues) == 0

    def test_skip_comment_line_js(self, scanner):
        files = {"config.js": '// password = "MyS3cureP@ssw0rd!"'}
        issues = scanner.scan(files)
        pwd_issues = [i for i in issues if i["pattern_name"] == "Hardcoded Password"]
        assert len(pwd_issues) == 0

    def test_skip_env_var_usage(self, scanner):
        files = {"config.py": 'api_key = os.environ.get("API_KEY", "")'}
        issues = scanner.scan(files)
        assert len(issues) == 0

    def test_skip_process_env(self, scanner):
        files = {"config.js": 'const key = process.env.API_KEY || ""'}
        issues = scanner.scan(files)
        assert len(issues) == 0

    def test_password_exclude_placeholder(self, scanner):
        files = {"config.py": 'password = "changeme"'}
        issues = scanner.scan(files)
        pwd_issues = [i for i in issues if i["pattern_name"] == "Hardcoded Password"]
        assert len(pwd_issues) == 0

    def test_password_exclude_test(self, scanner):
        files = {"config.py": 'password = "test_password_value"'}
        issues = scanner.scan(files)
        pwd_issues = [i for i in issues if i["pattern_name"] == "Hardcoded Password"]
        assert len(pwd_issues) == 0

    def test_api_key_exclude_dummy(self, scanner):
        files = {"config.py": 'api_key = "your_api_key_here_placeholder"'}
        issues = scanner.scan(files)
        key_issues = [i for i in issues if i["pattern_name"] == "Hardcoded API Key"]
        assert len(key_issues) == 0

    def test_no_issues_clean_code(self, scanner):
        files = {"app.py": 'def hello():\n    return "Hello, World!"\n'}
        issues = scanner.scan(files)
        assert issues == []

    def test_empty_files(self, scanner):
        files = {"empty.py": ""}
        issues = scanner.scan(files)
        assert issues == []

    def test_multiline_detection_correct_line_number(self, scanner):
        code = 'line1 = "safe"\nline2 = "safe"\ntoken = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef1234"\n'
        files = {"config.py": code}
        issues = scanner.scan(files)
        assert len(issues) >= 1
        assert issues[0]["line"] == 3


# ── Fix Suggestions ──────────────────────────────────────────


class TestSuggestFix:
    """Verify language-specific fix suggestions."""

    def _make_match(self, scanner, line):
        for pn, pd in scanner.PATTERNS.items():
            m = pd["pattern"].search(line)
            if m:
                return pn, m
        return None, None

    def test_python_fix(self, scanner):
        line = 'api_key = "ABCDEFGHIJKLMNOP1234"'
        pn, m = self._make_match(scanner, line)
        fix = scanner.suggest_fix("config.py", line, pn, m)
        assert "os.environ.get" in fix

    def test_js_fix(self, scanner):
        line = 'const apiKey = "ABCDEFGHIJKLMNOP1234"'
        pn, m = self._make_match(scanner, line)
        fix = scanner.suggest_fix("config.js", line, pn, m)
        assert "process.env" in fix

    def test_go_fix(self, scanner):
        line = 'apiKey = "ABCDEFGHIJKLMNOP1234"'
        pn, m = self._make_match(scanner, line)
        fix = scanner.suggest_fix("config.go", line, pn, m)
        assert "os.Getenv" in fix

    def test_ruby_fix(self, scanner):
        line = 'api_key = "ABCDEFGHIJKLMNOP1234"'
        pn, m = self._make_match(scanner, line)
        fix = scanner.suggest_fix("config.rb", line, pn, m)
        assert "ENV[" in fix

    def test_unknown_language_fix(self, scanner):
        line = 'api_key = "ABCDEFGHIJKLMNOP1234"'
        pn, m = self._make_match(scanner, line)
        fix = scanner.suggest_fix("config.xyz", line, pn, m)
        assert "environment variable" in fix.lower()


# ── Env Var Name Conversion ──────────────────────────────────


class TestToEnvVarName:
    """Verify camelCase → UPPER_SNAKE_CASE conversion."""

    def test_camel_case(self):
        assert SecretScanner._to_env_var_name("apiKey") == "API_KEY"

    def test_snake_case(self):
        assert SecretScanner._to_env_var_name("api_key") == "API_KEY"

    def test_pascal_case(self):
        assert SecretScanner._to_env_var_name("DatabasePassword") == "DATABASE_PASSWORD"

    def test_already_upper_snake(self):
        assert SecretScanner._to_env_var_name("SECRET_KEY") == "SECRET_KEY"

    def test_single_word(self):
        assert SecretScanner._to_env_var_name("password") == "PASSWORD"
