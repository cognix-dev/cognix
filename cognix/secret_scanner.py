"""
Secret Scanner Module
サービス固有パターンによる決定論的シークレット検出

配置先: cognix/secret_scanner.py
"""

import re
from typing import Dict, List, Optional, Tuple


class SecretScanner:
    """コード内のハードコードされたシークレットを正規表現で検出"""

    # サービス固有パターン (高精度、低偽陽性)
    PATTERNS: Dict[str, Dict] = {
        'AWS Access Key': {
            'pattern': re.compile(r'AKIA[0-9A-Z]{16}'),
            'severity': 'critical',
            'description': 'AWS Access Key ID detected',
        },
        'AWS Secret Key': {
            'pattern': re.compile(
                r'(?i)aws[_\-]?secret[_\-]?access[_\-]?key\s*[=:]\s*["\']([A-Za-z0-9/+=]{40})["\']'
            ),
            'severity': 'critical',
            'description': 'AWS Secret Access Key detected',
        },
        'GitHub PAT (Classic)': {
            'pattern': re.compile(r'ghp_[A-Za-z0-9]{36}'),
            'severity': 'critical',
            'description': 'GitHub Personal Access Token detected',
        },
        'GitHub OAuth Token': {
            'pattern': re.compile(r'gho_[A-Za-z0-9]{36}'),
            'severity': 'critical',
            'description': 'GitHub OAuth Token detected',
        },
        'GitHub Fine-grained PAT': {
            'pattern': re.compile(r'github_pat_[A-Za-z0-9_]{82}'),
            'severity': 'critical',
            'description': 'GitHub Fine-grained Personal Access Token detected',
        },
        'GitLab PAT': {
            'pattern': re.compile(r'glpat-[A-Za-z0-9\-]{20,}'),
            'severity': 'critical',
            'description': 'GitLab Personal Access Token detected',
        },
        'Stripe Live Secret Key': {
            'pattern': re.compile(r'sk_live_[A-Za-z0-9]{24,}'),
            'severity': 'critical',
            'description': 'Stripe Live Secret Key detected',
        },
        'Stripe Live Publishable Key': {
            'pattern': re.compile(r'pk_live_[A-Za-z0-9]{24,}'),
            'severity': 'high',
            'description': 'Stripe Live Publishable Key detected',
        },
        'Slack Token': {
            'pattern': re.compile(r'xox[baprs]-[A-Za-z0-9\-]{10,}'),
            'severity': 'critical',
            'description': 'Slack Token detected',
        },
        'Google API Key': {
            'pattern': re.compile(r'AIza[0-9A-Za-z\-_]{35}'),
            'severity': 'high',
            'description': 'Google API Key detected',
        },
        'Twilio Account SID': {
            'pattern': re.compile(r'AC[0-9a-f]{32}'),
            'severity': 'high',
            'description': 'Twilio Account SID detected',
        },
        'SendGrid API Key': {
            'pattern': re.compile(r'SG\.[A-Za-z0-9\-_]{22}\.[A-Za-z0-9\-_]{43}'),
            'severity': 'critical',
            'description': 'SendGrid API Key detected',
        },
        'npm Token': {
            'pattern': re.compile(r'npm_[A-Za-z0-9]{36}'),
            'severity': 'critical',
            'description': 'npm Access Token detected',
        },
        'PyPI Token': {
            'pattern': re.compile(r'pypi-[A-Za-z0-9]{60,}'),
            'severity': 'critical',
            'description': 'PyPI API Token detected',
        },
        'Private Key Block': {
            'pattern': re.compile(r'-----BEGIN\s+(RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----'),
            'severity': 'critical',
            'description': 'Private key block detected',
        },
        'Hardcoded Password': {
            'pattern': re.compile(
                r'(?i)(password|passwd|pwd)\s*[=:]\s*["\'](?![\s"\'])[^"\']{8,}["\']'
            ),
            'severity': 'high',
            'description': 'Hardcoded password detected',
            'exclude': re.compile(
                r'(?i)(placeholder|example|changeme|your[_\-]?password|xxx|dummy|test|default|TODO)',
            ),
        },
        'Hardcoded API Key': {
            'pattern': re.compile(
                r'(?i)(api[_\-]?key|apikey|secret[_\-]?key)\s*[=:]\s*["\'](?![\s"\'])[A-Za-z0-9\-_./+=]{16,}["\']'
            ),
            'severity': 'high',
            'description': 'Hardcoded API key detected',
            'exclude': re.compile(
                r'(?i)(placeholder|example|your[_\-]?api|xxx|dummy|test|TODO|change[_\-]?me)',
            ),
        },
    }

    # 除外パターン: テストファイル、コメント行、環境変数読み込み
    SKIP_LINE_PATTERNS = [
        re.compile(r'^\s*#'),           # Python comment
        re.compile(r'^\s*//'),          # JS/TS/Go/Java comment
        re.compile(r'^\s*\*'),          # Block comment body
        re.compile(r'os\.environ'),     # Already using env vars
        re.compile(r'process\.env'),    # Already using env vars
        re.compile(r'getenv'),          # Already using env vars
    ]

    SKIP_FILE_PATTERNS = [
        re.compile(r'test[_\-]'),       # Test files
        re.compile(r'_test\.'),         # Test files
        re.compile(r'\.test\.'),        # Test files
        re.compile(r'\.spec\.'),        # Spec files
        re.compile(r'mock[_\-s]'),      # Mock files
        re.compile(r'fixture'),         # Fixture files
        re.compile(r'example'),         # Example files
        re.compile(r'\.md$'),           # Markdown docs
    ]

    def scan(self, code_files: Dict[str, str]) -> List[Dict]:
        """全ファイルをスキャンしてシークレットを検出

        Args:
            code_files: {filepath: code_content} の辞書

        Returns:
            検出結果のリスト。各要素は:
            {
                'file': str,
                'line': int,
                'type': 19,  # blocking issue type (Security)
                'pattern_name': str,
                'severity': str,
                'description': str,
                'fix': str,
                'matched_text': str (先頭8文字 + '...' でマスク)
            }
        """
        issues = []

        for filepath, content in code_files.items():
            if self._should_skip_file(filepath):
                continue

            file_issues = self._scan_file(filepath, content)
            issues.extend(file_issues)

        return issues

    def _should_skip_file(self, filepath: str) -> bool:
        """テストファイル等をスキップ"""
        filename = filepath.rsplit('/', 1)[-1] if '/' in filepath else filepath
        filename = filename.rsplit('\\', 1)[-1] if '\\' in filename else filename
        return any(p.search(filename) for p in self.SKIP_FILE_PATTERNS)

    def _should_skip_line(self, line: str) -> bool:
        """コメント行や環境変数読み込み行をスキップ"""
        return any(p.search(line) for p in self.SKIP_LINE_PATTERNS)

    def _scan_file(self, filepath: str, content: str) -> List[Dict]:
        """単一ファイルをスキャン"""
        issues = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            if self._should_skip_line(line):
                continue

            for pattern_name, pattern_def in self.PATTERNS.items():
                match = pattern_def['pattern'].search(line)
                if not match:
                    continue

                # 除外パターンチェック
                exclude = pattern_def.get('exclude')
                if exclude and exclude.search(line):
                    continue

                matched_text = match.group(0)
                masked = matched_text[:8] + '...' if len(matched_text) > 8 else matched_text

                fix = self.suggest_fix(filepath, line, pattern_name, match)

                issues.append({
                    'file': filepath,
                    'line': line_num,
                    'type': 19,  # Security issue (blocking type)
                    'pattern_name': pattern_name,
                    'severity': pattern_def['severity'],
                    'description': f"{pattern_def['description']} (line {line_num}): {masked}",
                    'fix': fix,
                    'matched_text': masked,
                })

        return issues

    def suggest_fix(
        self,
        filepath: str,
        line: str,
        pattern_name: str,
        match: re.Match,
    ) -> str:
        """検出パターンに対する修正提案を生成"""
        # 変数名を抽出
        var_match = re.match(r'\s*(?:const|let|var|export\s+(?:const|let))?\s*(\w+)\s*[=:]', line)
        if var_match:
            var_name = var_match.group(1)
        else:
            var_name = 'SECRET_VALUE'

        env_var_name = self._to_env_var_name(var_name)

        if filepath.endswith('.py'):
            return f'Use environment variable: {var_name} = os.environ.get("{env_var_name}", "")'
        elif filepath.endswith(('.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs')):
            return f'Use environment variable: const {var_name} = process.env.{env_var_name} || ""'
        elif filepath.endswith('.go'):
            return f'Use environment variable: {var_name} := os.Getenv("{env_var_name}")'
        elif filepath.endswith(('.rb', '.ruby')):
            return f'Use environment variable: {var_name} = ENV["{env_var_name}"] || ""'
        elif filepath.endswith('.php'):
            return f'Use environment variable: ${var_name} = getenv("{env_var_name}") ?: ""'
        elif filepath.endswith(('.java', '.kt')):
            return f'Use environment variable: String {var_name} = System.getenv("{env_var_name}")'
        elif filepath.endswith('.rs'):
            return f'Use environment variable: let {var_name} = std::env::var("{env_var_name}").unwrap_or_default()'
        else:
            return f'Replace hardcoded secret with environment variable: {env_var_name}'

    @staticmethod
    def _to_env_var_name(var_name: str) -> str:
        """変数名を環境変数名に変換 (UPPER_SNAKE_CASE)"""
        # camelCase/PascalCase → UPPER_SNAKE_CASE
        result = re.sub(r'([a-z])([A-Z])', r'\1_\2', var_name)
        result = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', result)
        return result.upper()
