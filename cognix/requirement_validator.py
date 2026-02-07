"""
Requirement Validator Module
要件充足度検証機能を提供

配置先: cognix/requirement_validator.py
"""

import re
import sys
from typing import Dict, List, Set, Optional, Any

class RequirementValidator:
    """要件充足度を検証するクラス"""
    
    def __init__(self, workspace_path=None):
        """
        初期化
        
        Args:
            workspace_path: ワークスペースのパス
        """
        from pathlib import Path
        
        if workspace_path is None:
            self.workspace_path = Path.cwd()
        elif isinstance(workspace_path, str):
            self.workspace_path = Path(workspace_path)
        else:
            self.workspace_path = workspace_path    

    # ファイルタイプキーワード
    FILE_TYPE_KEYWORDS = {
        'python': ['python', 'py', '.py'],
        'javascript': ['javascript', 'js', '.js', 'node'],
        'typescript': ['typescript', 'ts', '.ts'],
        'html': ['html', '.html', 'webpage', 'web page'],
        'css': ['css', '.css', 'stylesheet', 'style'],
        'java': ['java', '.java'],
        'cpp': ['c++', 'cpp', '.cpp'],
        'rust': ['rust', '.rs'],
        'go': ['go', 'golang', '.go'],
        'sql': ['sql', '.sql', 'database'],
        'json': ['json', '.json'],
        'yaml': ['yaml', 'yml', '.yaml', '.yml'],
        'markdown': ['markdown', 'md', '.md'],
    }
    
    # 機能キーワード
    FEATURE_KEYWORDS = {
        'encryption': ['encrypt', 'cipher', 'crypto', 'hash'],
        'storage': ['storage', 'database', 'persist', 'save data', 'store data'],
        'authentication': ['auth', 'login', 'password', 'credential', 'sign in', 'user management'],
        'generator': ['code generator', 'file generator', 'auto generate', 'template generator'],
        'cli': ['cli', 'command line', 'terminal', 'argparse', 'command interface'],
        'api': ['api', 'endpoint', 'rest api', 'http server', 'web service'],
        'gui': ['gui', 'graphical interface', 'window', 'dialog', 'tkinter', 'qt'],
        'test': ['test', 'spec', 'unit test', 'pytest', 'jest'],
    }
    
    # ドメイン固有の必須ファイルパターン
    # 言語特化パターンを先に定義（優先順位を上げる）
    API_PROJECT_PATTERNS = {
        # 言語特化パターン（最優先）
        
        # TypeScript REST API
        'rest api typescript': {
            'required_files': [
                'src/server.ts',
                'src/models/index.ts',
                'src/routes/auth.ts',
                'src/routes/v1/auth.ts',
                '.env',
                'package.json'
            ],
            'keywords': ['rest api', 'restful']  # 言語名と 'api' を削除（誤検出防止）
        },
        
        # Python REST API
        'rest api python': {
            'required_files': [
                'main.py',
                'models/user.py',
                'models/__init__.py',
                'schemas/user.py',
                'schemas/__init__.py',
                'routers/auth.py',
                'routers/__init__.py',
                'dependencies/auth.py',  # ⭐ 追加
                'dependencies/__init__.py',  # ⭐ 追加
                'services/auth_service.py',  # ⭐ 追加
                'services/__init__.py',  # ⭐ 追加
                '.env'
            ],
            'keywords': ['rest api', 'restful', 'fastapi', 'flask', 'django']  # 'api' と 'python' を削除（誤検出防止）
        },
        
        # Node.js/JavaScript REST API
        'rest api nodejs': {
            'required_files': [
                'server.js',
                'models/index.js',
                'routes/auth.js',
                '.env',
                'package.json'
            ],
            'keywords': ['rest api', 'restful', 'express']  # 言語名と 'api' を削除（誤検出防止）
        },
        
        # ドメイン特化パターン（次の優先順位）
        
        # 認証
        'authentication': {
            'required_files': ['auth.py', 'models/user.py', 'dependencies/', 'security.py'],
            'keywords': ['authentication', 'auth', 'login', 'oauth', 'jwt']
        },
        
        # Web application
        'web application': {
            'required_files': ['index.html', 'styles.css', 'script.js', 'app.js'],
            'keywords': ['web app', 'website', 'webpage', 'web application']
        },
        
        # Microservice
        'microservice': {
            'required_files': ['main.py', 'models/', 'services/', 'api/', 'config.py', 'Dockerfile'],
            'keywords': ['microservice', 'micro service', 'service architecture']
        },
        
        # CLI application
        'cli application': {
            'required_files': ['main.py', 'cli.py', 'commands/', 'utils.py'],
            'keywords': ['cli app', 'command line', 'terminal app', 'cli tool']
        }
    }

    def validate_requirements(self, goal: str, generated_files: Dict[str, str]) -> Dict:
        """
        要件充足度を検証
        
        Args:
            goal: ユーザーが入力した実装目標
            generated_files: 生成されたファイル {filename: code}
            
        Returns:
            検証結果の辞書
        """
        # ✅ 要求ファイルを抽出（generated_files を引数として渡す）
        required_files = self._extract_required_files(goal, generated_files)
        
        # 要求機能を抽出
        required_features = self._extract_required_features(goal)
        
        # 生成されたファイル名
        generated_filenames = list(generated_files.keys())
        
        # 実装済み機能を確認
        implemented_features = self._check_implemented_features(
            required_features,
            generated_files
        )
        
        # 不足を特定
        missing_files = self._find_missing_files(required_files, generated_filenames)
        
        missing_features = [
            f for f in required_features 
            if f not in implemented_features
        ]
        
        # スコア計算
        file_score = self._calculate_file_score(
            len(required_files),
            len(generated_filenames),
            len(missing_files)
        )
        
        feature_score = self._calculate_feature_score(
            len(required_features),
            len(implemented_features)
        )
        
        # 総合スコア
        fulfillment_score = (file_score + feature_score) / 2.0
        
        # 完全性判定
        is_complete = (len(missing_files) == 0 and len(missing_features) == 0)
        
        # 問題点リスト
        issues = []
        if missing_files:
            issues.append(
                f"Missing {len(missing_files)} required file(s): "
                f"{', '.join(missing_files[:3])}"
            )
        if missing_features:
            issues.append(
                f"Missing {len(missing_features)} required feature(s): "
                f"{', '.join(missing_features[:3])}"
            )
        if len(generated_filenames) == 1 and len(required_files) > 1:
            issues.append(
                "Single file generated but multiple files were requested"
            )
        
        # ファイル名検証を実行
        extension_validation = self.validate_file_extensions(generated_files)
        
        # ファイル名不一致を問題点リストに追加
        if extension_validation['has_mismatches']:
            for mismatch in extension_validation['mismatches']:
                issues.append(
                    f"File extension mismatch: {mismatch['file']} - {mismatch['issue']}. "
                    f"Suggestion: {mismatch['suggestion']}"
                )
        
        return {
            'fulfillment_score': round(fulfillment_score, 2),
            'required_files': required_files,
            'generated_files': generated_filenames,
            'missing_files': missing_files,
            'required_features': required_features,
            'implemented_features': implemented_features,
            'missing_features': missing_features,
            'is_complete': is_complete,
            'issues': issues,
            'extension_validation': extension_validation  # 追加
        }

    def _detect_language(
        self, 
        goal_lower: str, 
        existing_files: Dict[str, str] = None  # ← この行を追加
    ) -> Optional[str]:
        """goalから言語を検出
        
        Args:
            goal_lower: 小文字化されたgoal文字列
            existing_files: 生成されたファイル（言語推測用、オプション）  # ← この行を追加
            
        Returns:
            検出された言語名、または None
        """
        # 言語検出パターン
        language_patterns = {
            'typescript': ['typescript', 'ts'],
            'python': ['python', 'fastapi', 'django', 'flask', 'py'],
            'nodejs': ['node', 'nodejs', 'express', 'javascript', 'js', 'npm'],
            'java': ['java', 'spring', 'maven'],
            'go': ['golang', 'go '],
            'rust': ['rust', 'cargo'],
            'ruby': ['ruby', 'rails'],
        }
        
        for lang, keywords in language_patterns.items():
            if self._match_keywords(goal_lower, keywords):
                return lang
        
        # ✅ Step 2: 既存ファイルから言語を推測（新規追加）
        if existing_files:
            detected_lang = self._detect_language_from_files(existing_files)
            if detected_lang:
                return detected_lang
        
        # ✅ Step 3: 言語不明の場合は None を返す（デフォルト推測を削除）
        return None

    def _detect_language_from_files(self, files: Dict[str, str]) -> Optional[str]:
        """既存ファイルから言語を検出
        
        Args:
            files: 生成されたファイル {filename: code}
            
        Returns:
            検出された言語名、または None
        """
        # 安全性チェック
        if not files:
            return None
        
        # ファイル拡張子から判定
        extension_map = {
            '.py': 'python',
            '.ts': 'typescript',
            '.js': 'nodejs',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
        }
        
        language_counts = {}
        
        for filename in files.keys():  # ← files を使う
            for ext, lang in extension_map.items():
                if filename.endswith(ext):
                    language_counts[lang] = language_counts.get(lang, 0) + 1
        
        # 最も多い言語を返す
        if language_counts:
            return max(language_counts, key=language_counts.get)
        
        return None

    def _detect_language_from_content(self, content: str) -> Optional[str]:
        """
        ファイル内容から言語を検出
        
        Args:
            content: ファイルの内容
        
        Returns:
            検出された言語名、または None
        """
        if not content or not content.strip():
            return None
        
        # JavaScriptパターン
        js_patterns = [
            r'\bconst\s+\w+\s*=',
            r'\blet\s+\w+\s*=',
            r'\bvar\s+\w+\s*=',
            r'\bfunction\s+\w+\s*\(',
            r'=>',
            r'document\.',
            r'console\.',
            r'window\.',
            r'addEventListener\(',
        ]
        js_match_count = sum(1 for pattern in js_patterns if re.search(pattern, content))
        
        # Pythonパターン
        py_patterns = [
            r'\bdef\s+\w+\s*\(',
            r'\bimport\s+\w+',
            r'\bfrom\s+\w+\s+import',
            r'\bclass\s+\w+:',
            r'if __name__',
            r':\s*$',  # コロンで終わる行（Pythonの構文）
        ]
        py_match_count = sum(1 for pattern in py_patterns if re.search(pattern, content, re.MULTILINE))
        
        # HTMLパターン
        html_patterns = [
            r'<html',
            r'<div',
            r'<body',
            r'<!DOCTYPE',
            r'<head>',
            r'<script>',
        ]
        html_match_count = sum(1 for pattern in html_patterns if re.search(pattern, content, re.IGNORECASE))
        
        # CSSパターン
        css_patterns = [
            r'\{[^}]*(?:color|font|margin|padding):',
            r'@media\s+',
            r'@keyframes\s+',
            r'\.[a-zA-Z][\w-]*\s*\{',  # クラスセレクタ
        ]
        css_match_count = sum(1 for pattern in css_patterns if re.search(pattern, content))
        
        # 最もマッチ数が多い言語を返す
        matches = {
            'javascript': js_match_count,
            'python': py_match_count,
            'html': html_match_count,
            'css': css_match_count,
        }
        
        # 最低2個以上のパターンマッチがある場合のみ判定
        max_lang = max(matches, key=matches.get)
        if matches[max_lang] >= 2:
            return max_lang
        
        return None

    def _get_extension_for_language(self, language: str) -> str:
        """
        言語に対応する拡張子を返す
        
        Args:
            language: 言語名
        
        Returns:
            対応する拡張子（ドットなし）
        """
        language_to_extension = {
            'python': 'py',
            'javascript': 'js',
            'typescript': 'ts',
            'html': 'html',
            'css': 'css',
            'java': 'java',
            'go': 'go',
            'rust': 'rs',
            'ruby': 'rb',
            'php': 'php',
        }
        return language_to_extension.get(language, 'txt')

    def validate_file_extensions(self, generated_files: Dict[str, str]) -> Dict[str, Any]:
        """
        ファイル名と内容の整合性をチェック
        
        Args:
            generated_files: 生成されたファイル {filename: code}
        
        Returns:
            検証結果 {
                'has_mismatches': bool,
                'mismatches': [
                    {
                        'file': str,
                        'content_language': str,
                        'extension_language': str,
                        'issue': str,
                        'suggestion': str
                    }
                ],
                'total_files_checked': int
            }
        """
        from pathlib import Path
        
        mismatches = []
        
        extension_to_language = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
        }
        
        for filename, content in generated_files.items():
            ext = Path(filename).suffix.lower()
            
            # 拡張子から期待される言語
            expected_lang = extension_to_language.get(ext)
            
            # 内容から検出される言語
            actual_lang = self._detect_language_from_content(content)
            
            # 両方が検出され、かつ不一致の場合
            if expected_lang and actual_lang and expected_lang != actual_lang:
                suggested_filename = f"{Path(filename).stem}.{self._get_extension_for_language(actual_lang)}"
                
                mismatches.append({
                    'file': filename,
                    'content_language': actual_lang,
                    'extension_language': expected_lang,
                    'issue': f'{actual_lang} code with {ext} extension',
                    'suggestion': f'Rename to {suggested_filename}'
                })
        
        return {
            'has_mismatches': len(mismatches) > 0,
            'mismatches': mismatches,
            'total_files_checked': len(generated_files)
        }

    def _extract_explicit_files(self, goal_lower: str) -> List[str]:
        """
        ユーザーが明示的に指定したファイル名を抽出
        
        Args:
            goal_lower: 小文字化されたgoal文字列
            
        Returns:
            明示的に指定されたファイルのリスト
            
        例:
            "create a landing page with reset.css, variables.css, and components.css"
            → ['reset.css', 'variables.css', 'components.css']
            
            "create a todo app with HTML, CSS, and JavaScript"
            → ['index.html', 'styles.css', 'script.js']
        """
        explicit = []
        
        # ==========================================
        # Step 1: 具体的なファイル名を検出（最優先）
        # ==========================================
        # 一般的な拡張子パターン
        common_extensions = [
            'py', 'js', 'jsx', 'ts', 'tsx',
            'html', 'css', 'scss', 'sass', 'less',
            'json', 'xml', 'yaml', 'yml',
            'md', 'txt', 'sh', 'bat',
            'java', 'cpp', 'c', 'h', 'hpp',
            'go', 'rs', 'rb', 'php', 'swift', 'kt',
            'sql', 'db', 'ini', 'conf', 'cfg', 'env'
        ]
        
        # パターン: ファイル名.拡張子
        # [\w\-]+ = 英数字、アンダースコア、ハイフン（1文字以上）
        extensions_pattern = '|'.join(common_extensions)
        pattern = rf'([\w\-]+\.(?:{extensions_pattern}))\b'
        
        # すべてのファイル名を検出
        detected_files = re.findall(pattern, goal_lower)
        
        if detected_files:
            # 具体的なファイル名が指定されている場合、それを優先して返す
            # 重複を除去
            return list(dict.fromkeys(detected_files))
        
        # ==========================================
        # Step 2: 具体的なファイル名がない場合、デフォルトファイル名を使用
        # ==========================================
        # パターン: "with X, Y, and Z" 形式
        if 'with' in goal_lower:
            # HTML
            if 'html' in goal_lower:
                explicit.append('index.html')
            
            # CSS
            if 'css' in goal_lower:
                explicit.append('styles.css')
            
            # JavaScript
            if 'javascript' in goal_lower or ' js' in goal_lower:
                explicit.append('script.js')
        
        return explicit

    def _match_keywords(self, text: str, keywords: List[str]) -> bool:
            """キーワードマッチング（単語境界を考慮）
            
            Args:
                text: 検索対象のテキスト（小文字化済み）
                keywords: キーワードのリスト
                
            Returns:
                いずれかのキーワードがマッチした場合True
            """
            for keyword in keywords:
                # 複数単語のフレーズはそのまま検索
                if ' ' in keyword:
                    if keyword in text:
                        return True
                else:
                    # 単一単語は単語境界を考慮
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                    if re.search(pattern, text):
                        return True
            return False

    def _extract_required_files(
        self, 
        goal: str, 
        generated_files: Dict[str, str]  # ← 追加
    ) -> List[str]:
        """要求されたファイルを抽出
        
        Args:
            goal: ユーザーが入力した実装目標
            generated_files: 生成されたファイル {filename: code}  # ← 追加
            
        Returns:
            要求されるファイルのリスト
        """
        required = []
        goal_lower = goal.lower()

        explicit_files = self._extract_explicit_files(goal_lower)
        if explicit_files:
            return explicit_files

        # パターン1: 明示的なファイル要求
        explicit_file_patterns = [
            r'separate files? for ([^.]+)',
            r'create ([^.]+) files?',
            r'with ([^.]+) files?',
            r'files?: ([^.]+)',
            r'generate ([^.]+) files?',
            r'split into ([^.]+) files?',
        ]
        
        for pattern in explicit_file_patterns:
            match = re.search(pattern, goal_lower)
            if match:
                items_text = match.group(1)
                items_text = items_text.replace(' and ', ', ')
                items = [item.strip() for item in items_text.split(',') if item.strip()]
                required.extend(items)
        
        # パターン2: ファイル名の明示的な記述
        filename_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_-]*\.(py|js|html|css|java|cpp|rs|go|ts))\b'
        filenames = re.findall(filename_pattern, goal_lower)
        for filename, ext in filenames:
            required.append(filename)
        
        # パターン3: ファイル種別の列挙
        multi_file_keywords = [
            'separate', 'multiple', 'different', 'split', 
            'divide', 'modular', 'organized', 'structured'
        ]
        
        has_multi_file_keyword = any(kw in goal_lower for kw in multi_file_keywords)
        
        detected_types = []
        for file_type, keywords in self.FILE_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.startswith('.') and keyword in goal_lower:
                    detected_types.append(file_type)
                    break
        
        if has_multi_file_keyword and len(detected_types) >= 2:
            required.extend(detected_types)
        
        # パターン4: Web技術スタックの完全セット
        web_stack_keywords = ['html', 'css', 'javascript', 'js']
        web_stack_count = sum(1 for kw in web_stack_keywords if kw in goal_lower)
        
        if web_stack_count >= 3:
            if 'html' not in required:
                required.append('html')
            if 'css' not in required:
                required.append('css')
            if 'js' not in required and 'javascript' not in required:
                required.append('js')
        
        # 重複削除
        required = list(dict.fromkeys(required))
        
        # パターン5: ドメイン固有の必須ファイル（言語判定付き）
        
        # ✅ 言語検出（existing_files を引数として渡す）
        detected_language = self._detect_language(goal_lower, generated_files)
        
        matched = False
        
        # 言語特化パターンを優先的に検索
        if detected_language:
            # 定義済み言語のリスト
            known_languages = ['python', 'nodejs', 'typescript', 'java', 'go', 'rust', 'ruby']
            
            # Step 1: 言語特化パターンを最優先で検索
            for domain, pattern_info in self.API_PROJECT_PATTERNS.items():
                # 言語名がドメインに含まれるパターンのみ
                if any(lang in domain for lang in known_languages):
                    # 検出された言語がドメインに含まれるか確認
                    if detected_language in domain:
                        # キーワードマッチング
                        if self._match_keywords(goal_lower, pattern_info['keywords']):
                            required.extend(pattern_info['required_files'])
                            matched = True
                            break
        
        # Step 2: 言語特化パターンがマッチしなかった場合、汎用パターンを試す
        if not matched:
            # 定義済み言語のリスト
            known_languages = ['python', 'nodejs', 'typescript', 'java', 'go', 'rust', 'ruby']
            
            for domain, pattern_info in self.API_PROJECT_PATTERNS.items():
                # 汎用パターン（言語名を含まない）のみ
                has_language_in_domain = any(lang in domain for lang in known_languages)
                
                if not has_language_in_domain:
                    if self._match_keywords(goal_lower, pattern_info['keywords']):
                        required.extend(pattern_info['required_files'])
                        matched = True
                        break
        
        # 再度、重複削除
        required = list(dict.fromkeys(required))
        
        return required
    
    def _extract_required_features(self, goal: str) -> List[str]:
        """要求された機能を抽出"""
        required = []
        goal_lower = goal.lower()
        
        for feature, keywords in self.FEATURE_KEYWORDS.items():
            for keyword in keywords:
                # より厳密なマッチング
                if len(keyword.split()) > 1:  # 複数単語のフレーズ
                    if keyword in goal_lower:
                        required.append(feature)
                        break
                else:  # 単一単語
                    # 単語境界を考慮したマッチング
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                    if re.search(pattern, goal_lower):
                        required.append(feature)
                        break
        
        return required
    
    def _check_implemented_features(
        self,
        required_features: List[str],
        generated_files: Dict[str, str]
    ) -> List[str]:
        """実装済み機能を確認"""
        implemented = []
        
        # 全コードを結合
        all_code = '\n'.join(generated_files.values()).lower()
        
        for feature in required_features:
            keywords = self.FEATURE_KEYWORDS.get(feature, [])
            # より柔軟なマッチング
            if any(kw in all_code for kw in keywords):
                implemented.append(feature)
        
        return implemented
    
    def _find_missing_files(self, required: List[str], generated: List[str]) -> List[str]:
        """不足ファイルを特定（ディスク上のファイルも確認）"""
        missing = []

        for req in required:
            req_lower = req.lower()

            # ========================================
            # ステップ1: メモリ上の生成ファイルをチェック
            # ========================================
            found = False
            for gen in generated:
                gen_lower = gen.lower()

                # ケース1: 拡張子でマッチング
                if f'.{req_lower}' in gen_lower:
                    found = True
                    break

                # ケース2: ファイル種別名が含まれる
                if req_lower in gen_lower:
                    found = True
                    break

                # ケース3: ファイル名の完全一致
                if req_lower == gen_lower:
                    found = True
                    break

                # ケース4: 拡張子で始まる場合の一致
                if req_lower.startswith('.') and gen_lower.endswith(req_lower):
                    found = True
                    break

                # ケース5: ディレクトリ指定
                if '/' in req_lower:
                    if req_lower in gen_lower:
                        found = True
                        break

                    req_without_ext = req_lower.split('.')[0]
                    gen_without_ext = gen_lower.split('.')[0]
                    if req_without_ext == gen_without_ext:
                        found = True
                        break

            # ========================================
            # ✅ ステップ2: ディスク上のファイルもチェック（新規追加）
            # ========================================
            if not found and hasattr(self, 'workspace_path') and self.workspace_path:
                from pathlib import Path
                
                # 絶対パスとして確認
                file_path = Path(self.workspace_path) / req
                if file_path.exists():
                    found = True
                
                # ディレクトリパターンの確認（例: "models/"）
                if not found and req.endswith('/'):
                    dir_path = Path(self.workspace_path) / req.rstrip('/')
                    if dir_path.exists() and dir_path.is_dir():
                        # ディレクトリ内にファイルがあるかチェック
                        if any(dir_path.iterdir()):
                            found = True

            # ========================================
            # ✅ ステップ3: 拡張子ベースのスマートマッチング（新規追加）
            # ========================================
            if not found:
                req_ext = self._get_extension(req_lower)
                if req_ext:
                    # 同じ拡張子を持つファイルをカウント
                    same_ext_files = [g for g in generated 
                                     if self._get_extension(g.lower()) == req_ext]
                    
                    # 同じ拡張子のファイルが1つだけの場合
                    if len(same_ext_files) == 1:
                        # required に同じ拡張子のファイルが複数あるかチェック
                        same_ext_required = [r for r in required 
                                            if self._get_extension(r.lower()) == req_ext]
                        
                        # required に同じ拡張子が1つだけなら、代替として認める
                        if len(same_ext_required) == 1:
                            found = True
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.debug(
                                f"[RequirementValidator] Accepted {same_ext_files[0]} "
                                f"as alternative to {req} (same extension: .{req_ext})"
                            )

            if not found:
                missing.append(req)

        return missing

    def _get_extension(self, filename: str) -> str:
        """ファイル拡張子を取得
        
        Args:
            filename: ファイル名（小文字化済み）
            
        Returns:
            拡張子（ドットなし）、拡張子がない場合は空文字列
            
        Examples:
            'script.js' -> 'js'
            'calculator.js' -> 'js'
            'index.html' -> 'html'
            'README' -> ''
        """
        parts = filename.split('.')
        if len(parts) > 1:
            return parts[-1]
        return ''
    
    
    def _calculate_file_score(
        self,
        required_count: int,
        generated_count: int,
        missing_count: int
    ) -> float:
        """ファイル充足度スコアを計算"""
        if required_count == 0:
            return min(1.0, generated_count / 3.0)
        
        fulfillment_rate = (required_count - missing_count) / required_count
        
        return max(0.0, min(1.0, fulfillment_rate))
    
    def _calculate_feature_score(
        self,
        required_count: int,
        implemented_count: int
    ) -> float:
        """機能充足度スコアを計算"""
        if required_count == 0:
            return 1.0
        
        return implemented_count / required_count

    # ============================================================
    # ステップ2-1で追加: Import依存関係解析機能
    # ============================================================
    
    def validate_import_dependencies(
        self,
        generated_files: Dict[str, str]
    ) -> List[Dict[str, any]]:
        """
        生成されたPythonコードのimport依存関係を検証
        
        各Pythonファイルのimport文を解析し、存在しないモジュールへの
        参照を検出します。これにより、import依存関係の先行記述問題を
        根本的に解決できます。
        
        Args:
            generated_files: 生成済みファイル {filename: code}
        
        Returns:
            List[Dict]: 未解決のimportのリスト
                各要素は以下のキーを持つ辞書:
                - 'file': importを含むファイル名
                - 'import': import文全体
                - 'missing_file': 不足している推定ファイルパス
                - 'module': モジュール名
                - 'line_number': 行番号（可能な場合）
        
        Example:
            >>> validator = RequirementValidator()
            >>> files = {
            ...     'main.py': 'from models import User\\nfrom auth import get_user',
            ...     'models.py': 'class User: pass'
            ... }
            >>> unresolved = validator.validate_import_dependencies(files)
            >>> print(unresolved)
            [{'file': 'main.py', 'import': 'from auth import get_user', 
              'missing_file': 'auth.py', 'module': 'auth', 'line_number': 2}]
        """
        unresolved_imports = []
        
        # 生成されたファイル名のセット（拡張子なし）を作成
        available_modules = set()
        for filename in generated_files.keys():
            # ディレクトリ構造を考慮したモジュール名を生成
            # 例: models/user.py → models.user, models
            if filename.endswith('.py'):
                module_path = filename[:-3].replace('/', '.')
                available_modules.add(module_path)
                
                # 親ディレクトリも追加
                parts = module_path.split('.')
                for i in range(1, len(parts)):
                    available_modules.add('.'.join(parts[:i]))
        
        # 各Pythonファイルを解析
        for filename, code in generated_files.items():
            # Pythonファイルのみ対象
            if not filename.endswith('.py'):
                continue
            
            # Import文を抽出
            imports = self._extract_imports(code)
            
            for import_info in imports:
                module_name = import_info['module']
                
                # 標準ライブラリはスキップ
                if self._is_standard_library(module_name):
                    continue
                
                # pip パッケージはスキップ
                if self._is_pip_package(module_name, generated_files):
                    continue
                
                # 相対importの処理
                if module_name.startswith('.'):
                    # 相対importは現在のディレクトリからの相対パス
                    current_dir = '/'.join(filename.split('/')[:-1])
                    # 簡易的な処理（完全な相対import解決は複雑）
                    continue
                
                # モジュールが生成済みファイルに存在するか確認
                module_exists = False
                
                # 完全一致チェック
                if module_name in available_modules:
                    module_exists = True
                
                # 部分一致チェック（サブモジュール）
                if not module_exists:
                    for available in available_modules:
                        if available.startswith(module_name + '.') or \
                           module_name.startswith(available + '.'):
                            module_exists = True
                            break
                
                # 存在しない場合は未解決として記録
                if not module_exists:
                    # 期待されるファイルパスを推測
                    expected_file = self._module_to_file(module_name)
                    
                    unresolved_imports.append({
                        'file': filename,
                        'import': import_info['statement'],
                        'missing_file': expected_file,
                        'module': module_name,
                        'line_number': import_info.get('line_number', 0)
                    })
        
        return unresolved_imports


    # ============================================================
    # ステップ2-2で追加: 強化検証フロー
    # ============================================================
    
    def validate_requirements_enhanced(
        self,
        goal: str,
        generated_files: Dict[str, str],
        detected_language: Optional[str] = None
    ) -> Dict[str, any]:
        """
        強化された要件検証（Import依存関係を含む）
        
        従来のファイル存在チェックに加えて、Import依存関係の解析を行い、
        より完全な検証結果を提供します。
        
        Args:
            goal: 実装目標
            generated_files: 生成済みファイル {filename: code}
            detected_language: 検出された言語（オプション）
        
        Returns:
            Dict: 強化された検証結果
                {
                    # 従来の検証結果（継承）
                    'fulfillment_score': float,
                    'required_files': List[str],
                    'generated_files': List[str],
                    'missing_files': List[str],
                    'required_features': List[str],
                    'implemented_features': List[str],
                    'missing_features': List[str],
                    'is_complete': bool,
                    'issues': List[str],
                    
                    # 新規追加項目
                    'unresolved_imports': List[Dict],  # ⭐ 未解決import
                    'import_resolution_score': float,  # ⭐ Import解決スコア
                    'total_imports': int,              # ⭐ 総import数
                    'resolved_imports': int            # ⭐ 解決済みimport数
                }
        
        Example:
            >>> validator = RequirementValidator()
            >>> result = validator.validate_requirements_enhanced(
            ...     goal="create a REST API",
            ...     generated_files={'main.py': '...', 'models.py': '...'}
            ... )
            >>> print(result['import_resolution_score'])
            1.00
        """
        # ==========================================
        # Step 1: 従来の検証を実行
        # ==========================================
        basic_validation = self.validate_requirements(goal, generated_files)
        
        # ==========================================
        # Step 2: Import依存関係の検証（Pythonのみ）
        # ==========================================
        unresolved_imports = []
        import_resolution_score = 1.0
        total_imports = 0
        resolved_imports = 0
        
        # Pythonファイルが含まれているか確認
        has_python_files = any(
            filename.endswith('.py')
            for filename in generated_files.keys()
        )
        
        # 言語が明示的にPythonと指定されているか、
        # またはPythonファイルが存在する場合にImport検証を実行
        should_validate_imports = (
            detected_language == 'python' or
            has_python_files
        )
        
        if should_validate_imports:
            # 未解決importを検出
            unresolved_imports = self.validate_import_dependencies(generated_files)
            
            # 総import数を算出
            total_imports = self._count_all_imports(generated_files)
            
            # Import解決スコアの算出
            if total_imports > 0:
                resolved_imports = total_imports - len(unresolved_imports)
                import_resolution_score = resolved_imports / total_imports
            else:
                # importが1つもない場合は完全解決とみなす
                import_resolution_score = 1.0
        
        # ==========================================
        # Step 3: 検証結果の統合
        # ==========================================
        
        # 完全性の再判定（Import解決も考慮）
        is_complete = (
            basic_validation['is_complete'] and
            len(unresolved_imports) == 0
        )
        
        # 問題点リストの拡張
        enhanced_issues = basic_validation['issues'].copy()
        if unresolved_imports:
            enhanced_issues.append(
                f"Unresolved imports: {len(unresolved_imports)} import(s) "
                f"reference missing modules"
            )
        
        # ==========================================
        # Step 4: 強化された検証結果を返す
        # ==========================================
        return {
            # 従来の検証結果を継承
            **basic_validation,
            
            # 新規追加項目
            'unresolved_imports': unresolved_imports,
            'import_resolution_score': round(import_resolution_score, 2),
            'total_imports': total_imports,
            'resolved_imports': resolved_imports,
            
            # 完全性と問題点を更新
            'is_complete': is_complete,
            'issues': enhanced_issues
        }
    
    
    def _count_all_imports(self, generated_files: Dict[str, str]) -> int:
        """
        生成されたファイル内の総import数をカウント
        
        Args:
            generated_files: 生成済みファイル {filename: code}
        
        Returns:
            int: 総import数
        
        Example:
            >>> validator = RequirementValidator()
            >>> files = {
            ...     'main.py': 'import os\\nfrom models import User',
            ...     'models.py': 'from typing import Optional'
            ... }
            >>> count = validator._count_all_imports(files)
            >>> print(count)
            3
        """
        total_count = 0
        
        for filename, code in generated_files.items():
            # Pythonファイルのみ対象
            if not filename.endswith('.py'):
                continue
            
            # Import文を抽出
            imports = self._extract_imports(code)
            
            # import数を加算
            total_count += len(imports)
        
        return total_count


    def _extract_imports(self, code: str) -> List[Dict[str, str]]:
        """
        Pythonコードからimport文を抽出
        
        Args:
            code: Pythonソースコード
        
        Returns:
            List[Dict]: import情報のリスト
                各要素は以下のキーを持つ辞書:
                - 'statement': import文全体
                - 'module': モジュール名
                - 'imported_items': importされた項目のリスト（from import用）
                - 'line_number': 行番号
        
        Example:
            >>> validator = RequirementValidator()
            >>> code = '''
            ... import os
            ... from models import User, Post
            ... from auth import get_user
            ... '''
            >>> imports = validator._extract_imports(code)
            >>> print(imports)
            [{'statement': 'import os', 'module': 'os', 'imported_items': [], 'line_number': 2},
             {'statement': 'from models import User, Post', 'module': 'models', 
              'imported_items': ['User', 'Post'], 'line_number': 3},
             ...]
        """
        imports = []
        
        # パターン1: import module
        # 例: import os, import sys
        import_pattern = r'^import\s+([\w.]+)(?:\s+as\s+\w+)?'
        
        # パターン2: from module import item
        # 例: from models import User, from auth import get_user
        from_import_pattern = r'^from\s+([\w.]+)\s+import\s+(.+)'
        
        lines = code.split('\n')
        for line_number, line in enumerate(lines, 1):
            line = line.strip()
            
            # コメント行とdocstringをスキップ
            if line.startswith('#') or line.startswith('"""') or line.startswith("'''"):
                continue
            
            # パターン1: import module
            match = re.match(import_pattern, line)
            if match:
                module_name = match.group(1)
                imports.append({
                    'statement': line,
                    'module': module_name,
                    'imported_items': [],
                    'line_number': line_number
                })
                continue
            
            # パターン2: from module import item
            match = re.match(from_import_pattern, line)
            if match:
                module_name = match.group(1)
                imported_items_str = match.group(2)
                
                # 複数項目のimportを分割
                # 例: User, Post → ['User', 'Post']
                imported_items = [
                    item.strip().split(' as ')[0].strip()
                    for item in imported_items_str.split(',')
                ]
                
                imports.append({
                    'statement': line,
                    'module': module_name,
                    'imported_items': imported_items,
                    'line_number': line_number
                })
        
        return imports
    
    
    def _module_to_file(self, module_name: str) -> str:
        """
        モジュール名から期待されるファイルパスを推測
        
        Args:
            module_name: モジュール名（例: 'models.user', 'auth'）
        
        Returns:
            str: 推測されるファイルパス
        
        Example:
            >>> validator = RequirementValidator()
            >>> validator._module_to_file('models.user')
            'models/user.py'
            >>> validator._module_to_file('auth')
            'auth.py'
            >>> validator._module_to_file('services.auth_service')
            'services/auth_service.py'
        """
        # ドット記法をスラッシュに変換
        file_path = module_name.replace('.', '/')
        
        # .py拡張子を追加
        if not file_path.endswith('.py'):
            file_path += '.py'
        
        return file_path
    
    
    def _is_standard_library(self, module_name: str) -> bool:
        """
        モジュールがPython標準ライブラリかどうかを判定
        
        Args:
            module_name: モジュール名
        
        Returns:
            bool: 標準ライブラリの場合True
        
        Example:
            >>> validator = RequirementValidator()
            >>> validator._is_standard_library('os')
            True
            >>> validator._is_standard_library('models')
            False
            >>> validator._is_standard_library('json')
            True
        """
        # Python標準ライブラリの代表的なモジュール
        # 完全なリストはsys.builtin_module_namesとstdlib-listを参照
        standard_modules = {
            # Built-in modules
            'os', 'sys', 're', 'json', 'math', 'datetime', 'time',
            'collections', 'itertools', 'functools', 'operator',
            'pathlib', 'io', 'pickle', 'shelve', 'sqlite3',
            'subprocess', 'threading', 'multiprocessing',
            'asyncio', 'concurrent', 'queue',
            'urllib', 'http', 'email', 'html', 'xml',
            'logging', 'argparse', 'getopt', 'configparser',
            'unittest', 'doctest', 'pdb',
            'typing', 'dataclasses', 'enum', 'abc',
            'copy', 'pprint', 'textwrap', 'string',
            'random', 'secrets', 'statistics',
            'decimal', 'fractions', 'numbers',
            'array', 'heapq', 'bisect', 'weakref',
            'types', 'inspect', 'ast', 'dis',
            'importlib', 'pkgutil', 'modulefinder',
            'warnings', 'contextlib', 'atexit',
            'gc', 'trace', 'traceback', 'sys',
            
            # Common third-party libraries (not standard, but check anyway)
            # これらは標準ライブラリではないが、よく使われるのでチェック対象外
        }
        
        # トップレベルモジュール名を取得
        # 例: 'os.path' → 'os'
        top_level = module_name.split('.')[0]
        
        # 標準ライブラリかチェック
        if top_level in standard_modules:
            return True
        
        # sys.builtin_module_namesでも確認
        if top_level in sys.builtin_module_names:
            return True
        
        return False


    def _is_pip_package(
        self,
        module_name: str,
        generated_files: Dict[str, str]
    ) -> bool:
        """
        モジュールが pip パッケージかどうかを判定
        
        requirements.txt に記載されているパッケージを pip パッケージと判定します。
        これにより、Auto-completion が flask.py のような誤ったファイルを生成するのを防ぎます。
        
        Args:
            module_name: モジュール名（例: 'flask', 'flask_cors', 'pandas'）
            generated_files: 生成済みファイル（requirements.txt を含む）
        
        Returns:
            bool: pip パッケージの場合 True
        
        Example:
            >>> validator = RequirementValidator()
            >>> files = {'requirements.txt': 'Flask==3.0.0\\nFlask-CORS==4.0.0'}
            >>> validator._is_pip_package('flask', files)
            True
            >>> validator._is_pip_package('flask_cors', files)
            True
            >>> validator._is_pip_package('models', files)
            False
        """
        # requirements.txt を取得
        requirements_txt = generated_files.get('requirements.txt', '')
        
        if not requirements_txt:
            # requirements.txt が存在しない場合は pip パッケージではない
            return False
        
        # pip パッケージ名を抽出
        pip_packages = set()
        
        for line in requirements_txt.split('\n'):
            line = line.strip()
            
            # コメントと空行をスキップ
            if not line or line.startswith('#'):
                continue
            
            # パッケージ名を抽出
            # 例:
            #   Flask==3.0.0 → flask
            #   pandas>=1.0.0 → pandas
            #   requests<=2.31.0 → requests
            pkg = line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].strip()
            
            # 小文字化して追加
            pip_packages.add(pkg.lower())
            
            # ハイフンをアンダースコアに変換したバージョンも追加
            # Flask-CORS → flask_cors
            # python-dotenv → python_dotenv
            if '-' in pkg:
                pip_packages.add(pkg.lower().replace('-', '_'))
        
        # モジュール名のトップレベルを取得
        # 例: flask.app → flask
        top_level = module_name.split('.')[0].lower()
        
        # pip パッケージに含まれているかチェック
        return top_level in pip_packages


    def extract_goal_constraints(self, goal: str) -> Dict[str, Any]:
        """
        Goalから制約キーワードを抽出
        
        Args:
            goal: ユーザーが入力した実装目標
            
        Returns:
            {
                "keep_keywords": List[str],      # ["routes", "response format"]
                "only_keywords": List[str],      # ["app.py"]
                "explicit_files": List[str],     # ["app.py", "routes.py"]
                "forbidden_actions": List[str],  # ["change response format", "add files"]
                "constraint_strength": str,      # "strict" | "moderate" | "none"
            }
            
        Examples:
            goal="KEEP existing routes"
            → {"keep_keywords": ["existing routes"], "constraint_strength": "strict"}
            
            goal="Create ONLY app.py"
            → {"only_keywords": ["app.py"], "constraint_strength": "strict"}
            
            goal="Modify routes.py and models.py"
            → {"explicit_files": ["routes.py", "models.py"], "constraint_strength": "moderate"}
        """
        goal_lower = goal.lower()
        constraints = {
            "keep_keywords": [],
            "only_keywords": [],
            "explicit_files": [],
            "forbidden_actions": [],
            "constraint_strength": "none"
        }
        
        # ==========================================
        # Step 1: KEEP検出
        # ==========================================
        keep_patterns = [
            r'keep\s+(\w+(?:\s+(?!(?:and|only|or|but|with)\b)\w+)*)',          # "keep routes", "keep response format"
            r'maintain\s+(\w+(?:\s+(?!(?:and|only|or|but|with)\b)\w+)*)',      # "maintain routes"
            r'preserve\s+(\w+(?:\s+(?!(?:and|only|or|but|with)\b)\w+)*)',      # "preserve routes"
            r'do not change\s+(\w+(?:\s+(?!(?:and|only|or|but|with)\b)\w+)*)', # "do not change routes"
            r"don't change\s+(\w+(?:\s+(?!(?:and|only|or|but|with)\b)\w+)*)",  # "don't change routes"
        ]
        
        for pattern in keep_patterns:
            matches = re.findall(pattern, goal_lower)
            for match in matches:
                # 複数単語の場合、最大3単語まで取得
                words = match.strip().split()[:3]
                keyword = ' '.join(words)
                if keyword and keyword not in constraints["keep_keywords"]:
                    constraints["keep_keywords"].append(keyword)
        
        # ==========================================
        # Step 2: ONLY検出
        # ==========================================
        only_patterns = [
            r'only\s+([\w\-]+\.[\w]+)',                    # "only app.py"
            r'only\s+\w+\s+([\w\-]+\.[\w]+)',              # "only modify app.py"
            r'just\s+([\w\-]+\.[\w]+)',                    # "just app.py"
            r'just\s+\w+\s+([\w\-]+\.[\w]+)',              # "just modify app.py"
            r'([\w\-]+\.[\w]+)\s+only',                    # "app.py only"
            r'\w+\s+only\s+([\w\-]+\.[\w]+)',              # "modify only app.py"
        ]
        
        for pattern in only_patterns:
            matches = re.findall(pattern, goal_lower)
            for match in matches:
                if match and match not in constraints["only_keywords"]:
                    constraints["only_keywords"].append(match)
        
        # ==========================================
        # Step 3: 明示的ファイル抽出（既存メソッド活用）
        # ==========================================
        constraints["explicit_files"] = self._extract_explicit_files(goal_lower)
        
        # ==========================================
        # Step 4: 制約強度判定
        # ==========================================
        if constraints["keep_keywords"] or constraints["only_keywords"]:
            constraints["constraint_strength"] = "strict"
        elif constraints["explicit_files"]:
            constraints["constraint_strength"] = "moderate"
        
        # ==========================================
        # Step 5: 禁止アクション生成
        # ==========================================
        # KEEP検出時の禁止アクション
        for keyword in constraints["keep_keywords"]:
            if "response" in keyword or "format" in keyword:
                if "change response format" not in constraints["forbidden_actions"]:
                    constraints["forbidden_actions"].append("change response format")
            
            if "route" in keyword or "endpoint" in keyword:
                if "modify existing routes" not in constraints["forbidden_actions"]:
                    constraints["forbidden_actions"].append("modify existing routes")
            
            if "behavior" in keyword or "functionality" in keyword:
                if "alter existing behavior" not in constraints["forbidden_actions"]:
                    constraints["forbidden_actions"].append("alter existing behavior")
        
        # ONLY検出時の禁止アクション
        if constraints["only_keywords"]:
            if "add unrequested files" not in constraints["forbidden_actions"]:
                constraints["forbidden_actions"].append("add unrequested files")
        
        return constraints