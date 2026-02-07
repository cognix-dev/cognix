"""
Linter Integration for Cognix
Provides automatic code quality checking using external linters
"""

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from cognix.logger import logger


class LinterIntegration:
    """外部linterとの統合 (Aider方式)"""
    
    # 言語別linterコマンド (必須エラーのみ)
    LANGUAGE_LINTERS = {
        'python': {
            'commands': [
                'flake8 --select=E9,F821,F823,F401,F841',  # 致命的エラーのみ
                'ruff check --select=E9,F',  # ruff (alternative)
            ],
            'required': False,  # オプショナル
        },
        'javascript': {
            'commands': [
                'eslint --no-eslintrc --rule "no-undef:error" --rule "no-unused-vars:warn"',
                'standard --fix',
            ],
            'required': False,
        },
        'javascript_tsc': {
            'commands': [
                'tsc --allowJs --checkJs --noEmit --skipLibCheck',
            ],
            'required': False,
        },
        'typescript': {
            'commands': [
                'tsc --noEmit --skipLibCheck',
            ],
            'required': False,
        },
        'html': {
            'commands': [
                'htmlhint',
            ],
            'required': False,
        },
        'css': {
            'commands': [
                'stylelint',
            ],
            'required': False,
        },
    }
    
    # TypeScript エラーコード フィルタリング設定
    # 
    # 修正: 2025-12-29
    # 目的: 純粋なJavaScriptファイルに対して、構文エラーと致命的エラーのみを報告し、
    #       型関連のノイズ（暗黙のany、型不一致等）を除去
    #
    # 参考: https://github.com/microsoft/TypeScript/blob/main/src/compiler/diagnosticMessages.json
    
    # 報告すべき重要なTSエラーコード（FAILとして扱う）
    TS_CRITICAL_ERROR_CODES = {
        # 構文エラー (TS1xxx)
        '1002',  # Unterminated string literal
        '1003',  # Identifier expected
        '1005',  # ';' expected
        '1009',  # Trailing comma not allowed
        '1010',  # '*/' expected
        '1012',  # Unexpected token
        '1014',  # A rest parameter must be last in a parameter list
        '1015',  # Parameter cannot have question mark and initializer
        '1016',  # A required parameter cannot follow an optional parameter
        '1036',  # Statements are not allowed in ambient contexts
        '1109',  # Expression expected
        '1127',  # Invalid character
        '1128',  # Declaration or statement expected
        '1134',  # Variable declaration expected
        '1141',  # String literal expected
        '1160',  # Unterminated template literal
        '1161',  # Unterminated regular expression literal
        
        # 未定義識別子・プロパティ (致命的)
        '2304',  # Cannot find name 'xxx'
        '2339',  # Property 'xxx' does not exist on type 'yyy'
        '2552',  # Cannot find name 'xxx'. Did you mean 'yyy'?
        '2580',  # Cannot find name 'require'
        '2581',  # Cannot find name 'xxx'. Do you need to install type definitions?
        
        # 重大な参照エラー
        '2448',  # Block-scoped variable 'xxx' used before its declaration
        '2454',  # Variable 'xxx' is used before being assigned
    }
    
    # 無視すべきTSエラーコード（純粋なJSでは無意味）
    TS_IGNORABLE_ERROR_CODES = {
        # 型不一致エラー (JSでは無意味)
        '2322',  # Type 'xxx' is not assignable to type 'yyy'
        '2345',  # Argument of type 'xxx' is not assignable to parameter of type 'yyy'
        '2355',  # A function whose declared type is neither 'undefined', 'void', nor 'any' must return a value
        '2365',  # Operator '+' cannot be applied to types 'xxx' and 'yyy'
        '2367',  # This comparison appears to be unintentional
        '2416',  # Property 'xxx' in type 'yyy' is not assignable to the same property in base type 'zzz'
        '2559',  # Type 'xxx' has no properties in common with type 'yyy'
        '2571',  # Object is of type 'unknown'
        
        # 暗黙のany関連 (JSでは無意味)
        '7005',  # Variable 'xxx' implicitly has an 'any' type
        '7006',  # Parameter 'xxx' implicitly has an 'any' type
        '7008',  # Member 'xxx' implicitly has an 'any' type
        '7009',  # 'new' expression, whose target lacks a construct signature, implicitly has an 'any' type
        '7010',  # 'xxx', which lacks return-type annotation, implicitly has an 'any' return type
        '7015',  # Element implicitly has an 'any' type because index expression is not of type 'number'
        '7016',  # Could not find a declaration file for module 'xxx'
        '7017',  # Element implicitly has an 'any' type because type 'xxx' has no index signature
        '7019',  # Rest parameter 'xxx' implicitly has an 'any[]' type
        '7022',  # 'xxx' implicitly has type 'any' because it does not have a type annotation
        '7023',  # 'xxx' implicitly has return type 'any'
        '7024',  # Function implicitly has return type 'any'
        '7031',  # Binding element 'xxx' implicitly has an 'any' type
        '7034',  # Variable 'xxx' implicitly has type 'any' in some locations
        
        # null/undefined関連 (strict: falseで無効化済みだが念のため)
        '2531',  # Object is possibly 'null'
        '2532',  # Object is possibly 'undefined'
        '2533',  # Object is possibly 'null' or 'undefined'
        '18046', # 'xxx' is of type 'unknown'
        '18047', # 'xxx' is possibly 'null'
        '18048', # 'xxx' is possibly 'undefined'
        '18049', # 'xxx' is possibly 'null' or 'undefined'
        
        # this関連
        '2683',  # 'this' implicitly has type 'any' because it does not have a type annotation
        '2684',  # The 'this' context of type 'xxx' is not assignable to method's 'this' of type 'yyy'
        
        # その他のノイズ
        '2307',  # Cannot find module 'xxx' or its corresponding type declarations
        '2349',  # This expression is not callable
        '2488',  # Type 'xxx' must have a '[Symbol.iterator]()' method
        '2769',  # No overload matches this call
    }
    
    def __init__(self):
        """Initialize linter integration"""
        self._cache_available_linters()
    
    def _cache_available_linters(self):
        """利用可能なlinterをキャッシュ"""
        self.available_linters = {}
        self.actual_linter_commands = {}  # 実際のコマンド名（.cmd付き）を保存
        
        for language, config in self.LANGUAGE_LINTERS.items():
            for cmd in config['commands']:
                linter_name = cmd.split()[0]
                actual_cmd = self._get_available_command(linter_name)
                if actual_cmd:
                    if language not in self.available_linters:
                        self.available_linters[language] = []
                        self.actual_linter_commands[language] = []
                    self.available_linters[language].append(cmd)
                    self.actual_linter_commands[language].append(actual_cmd)
                    logger.debug(f"[Linter] Available: {language} -> {actual_cmd}")
                    break  # 最初に見つかったlinterを使用
        
        if not self.available_linters:
            logger.debug("[Linter] No external linters found (optional)")
    
    def _get_available_command(self, linter_name: str) -> Optional[str]:
        """linterが利用可能かチェックし、実際のコマンド名を返す"""
        # Windows環境では .cmd/.bat 拡張子が必要な場合がある
        import platform
        candidates = [linter_name]
        if platform.system() == 'Windows':
            candidates.extend([f"{linter_name}.cmd", f"{linter_name}.bat"])
        
        for cmd in candidates:
            try:
                result = subprocess.run(
                    [cmd, '--version'],
                    capture_output=True,
                    timeout=5,
                    encoding='utf-8',
                    errors='replace',
                    shell=False
                )
                if result.returncode == 0:
                    logger.debug(f"[Linter] Detected: {cmd}")
                    return cmd  # 実際のコマンド名を返す
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                continue
        
        return None
    
    def _is_linter_available(self, linter_name: str) -> bool:
        """linterが利用可能かチェック"""
        return self._get_available_command(linter_name) is not None

    def _detect_language(self, filename: str) -> Optional[str]:
        """ファイル名から言語を判定"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.html': 'html',
            '.htm': 'html',
            '.css': 'css',
            '.scss': 'css',
            '.sass': 'css',
        }
        
        ext = Path(filename).suffix.lower()
        return ext_map.get(ext)
    
    def lint_generated_code(self, generated_files: Dict[str, str]) -> Dict[str, Any]:
        all_errors = []
        all_warnings = []
        linters_used = []
        file_languages = {}  # ✅ 言語情報を保存する辞書を追加
        
        for filename, code in generated_files.items():
            language = self._detect_language(filename)
            file_languages[filename] = language or 'unknown'  # ✅ 言語情報を保存
            
            if not language or language not in self.available_linters:
                logger.debug(f"[Linter] No linter available for {filename}")
                # ★ この13行を追加
                if filename.endswith('.js') or filename.endswith('.jsx'):
                    logger.debug(f"[Linter] Attempting TypeScript type check for {filename}")
                    tsc_result = self.run_typescript_type_check(filename, code)
                    
                    if not tsc_result.get('skipped'):
                        if tsc_result['has_errors']:
                            all_errors.extend(tsc_result['errors'])
                            linters_used.append('tsc')
                        if tsc_result.get('has_warnings'):
                            all_warnings.extend(tsc_result['warnings'])
                continue
            
            linter_cmd = self.available_linters[language][0]
            linter_name = linter_cmd.split()[0]
            linters_used.append(linter_name)
            
            # 一時ファイル作成してlinter実行
            errors, warnings = self._run_linter(linter_cmd, filename, code, self.actual_linter_commands.get(language, [None])[0])
            all_errors.extend(errors)
            all_warnings.extend(warnings)
            
            # ★ JavaScriptファイルの場合、追加でTypeScript型チェックも実行
            if (filename.endswith('.js') or filename.endswith('.jsx')) and linter_name != 'tsc':
                logger.debug(f"[Linter] Running additional TypeScript type check for {filename}")
                try:
                    tsc_result = self.run_typescript_type_check(filename, code)
                    
                    if not tsc_result.get('skipped'):
                        if tsc_result['has_errors']:
                            all_errors.extend(tsc_result['errors'])
                            if 'tsc' not in linters_used:
                                linters_used.append('tsc')
                        if tsc_result.get('has_warnings'):
                            all_warnings.extend(tsc_result['warnings'])
                except Exception as e:
                    logger.debug(f"[Linter] Error during TypeScript type check: {e}")
        
        return {
            'has_errors': len(all_errors) > 0,
            'has_warnings': len(all_warnings) > 0,
            'errors': all_errors,
            'warnings': all_warnings,
            'can_auto_fix': self._check_auto_fixable(all_errors),
            'linters_used': linters_used,
            'file_languages': file_languages  # ✅ 言語情報を戻り値に追加
        }
    
    def _run_linter(self, linter_cmd: str, filename: str, code: str, actual_cmd: str = None) -> Tuple[List[Dict], List[Dict]]:
        """linterを実行してエラー/警告を取得"""
        errors = []
        warnings = []
        
        # 一時ファイルに書き込み
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=Path(filename).suffix,
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            # linter実行
            cmd_parts = linter_cmd.split()
            # 実際のコマンド名（.cmd付き）を使用
            if actual_cmd:
                cmd_parts[0] = actual_cmd
            cmd_parts.append(temp_path)
            
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                timeout=30
            )
            
            if result.returncode != 0 or result.stdout or result.stderr:
                # エラー/警告をパース
                parsed_errors, parsed_warnings = self._parse_linter_output(
                    result.stdout,
                    result.stderr,
                    filename,
                    cmd_parts[0]
                )
                errors.extend(parsed_errors)
                warnings.extend(parsed_warnings)
        
        except subprocess.TimeoutExpired:
            logger.debug(f"[Linter] Timeout: {linter_cmd}")
        except Exception as e:
            logger.debug(f"[Linter] Error running {linter_cmd}: {e}")
        finally:
            # 一時ファイル削除
            try:
                os.unlink(temp_path)
            except:
                pass
        
        return errors, warnings
    
    def _parse_linter_output(
        self,
        stdout: str,
        stderr: str,
        filename: str,
        linter_name: str
    ) -> Tuple[List[Dict], List[Dict]]:
        """Linter出力をパースして構造化"""
        errors = []
        warnings = []
        output = stdout + stderr
        
        # 一般的なlinterフォーマット: filename:line:col: severity: message
        # flake8: filename:line:col: code message
        # eslint: filename:line:col: severity message [code]
        # tsc: filename(line,col): error/warning TS code: message
        
        for line in output.split('\n'):
            if not line.strip():
                continue
            
            # flake8/ruff形式: path:line:col: code message
            match = re.match(r'.*?:(\d+):(\d+):\s*([A-Z]\d+)\s+(.+)', line)
            if match:
                item = {
                    'file': filename,
                    'line': int(match.group(1)),
                    'column': int(match.group(2)),
                    'code': match.group(3),
                    'message': match.group(4).strip(),
                    'linter': linter_name
                }
                
                # Fで始まるコードはエラー、それ以外は警告
                if match.group(3).startswith('F') or match.group(3).startswith('E9'):
                    errors.append(item)
                else:
                    warnings.append(item)
                continue
            
            # eslint形式: line:col severity message [code]
            match = re.match(r'.*?(\d+):(\d+)\s+(error|warning)\s+(.+?)\s+\[(.+?)\]', line)
            if match:
                item = {
                    'file': filename,
                    'line': int(match.group(1)),
                    'column': int(match.group(2)),
                    'severity': match.group(3),
                    'message': match.group(4).strip(),
                    'code': match.group(5),
                    'linter': linter_name
                }
                
                if match.group(3) == 'error':
                    errors.append(item)
                else:
                    warnings.append(item)
                continue
            
            # tsc形式: filename(line,col): error/warning TS code: message
            match = re.match(r'.*?\((\d+),(\d+)\):\s+(error|warning)\s+TS(\d+):\s+(.+)', line)
            if match:
                item = {
                    'file': filename,
                    'line': int(match.group(1)),
                    'column': int(match.group(2)),
                    'severity': match.group(3),
                    'code': f'TS{match.group(4)}',
                    'message': match.group(5).strip(),
                    'linter': linter_name
                }
                
                if match.group(3) == 'error':
                    errors.append(item)
                else:
                    warnings.append(item)
                continue
        
        return errors, warnings
    
    def _check_auto_fixable(self, errors: List[Dict]) -> bool:
        """エラーが自動修正可能かチェック
        
        すべてのエラーはファイル+行番号情報があればLLMで修正可能。
        エラーコードによる制限は不要。
        
        Returns:
            bool: 常にTrue（すべてのエラーで修正を試みる）
        """
        return True
    
    def run_typescript_type_check(self, filename: str, code: str) -> Dict[str, Any]:
        """
        JavaScriptファイルに対してTypeScript型チェックを実行
        
        Args:
            filename: チェック対象ファイル名 (.js)
            code: ファイルのコード内容
            
        Returns:
            {
                'has_errors': bool,
                'errors': List[Dict],
                'warnings': List[Dict]
            }
        """
        import json
        
        errors = []
        warnings = []
        
        # TypeScriptコンパイラが利用可能かチェック
        tsc_cmd = self._get_available_command('tsc')
        if not tsc_cmd:
            logger.debug("[TSC] TypeScript compiler not available")
            return {
                'has_errors': False,
                'errors': [],
                'warnings': [],
                'skipped': True
            }
        
        # 一時ディレクトリ作成
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # JavaScriptファイル作成
            js_path = tmpdir_path / filename
            js_path.write_text(code, encoding='utf-8')
            
            # tsconfig.json作成
            # 
            # 修正: 2025-12-29
            # 問題: strict: true により、純粋なJavaScriptファイルに対して
            #       型アノテーション関連のエラーが大量発生（187件等）
            # 対策: 
            #   - strict: false に変更
            #   - noImplicitAny: false を追加（暗黙のany許可）
            #   - strictNullChecks: false を追加（null/undefined厳密チェック無効）
            #   - noImplicitThis: false を追加（暗黙のthis許可）
            # 目的: 構文エラーと未定義識別子のみを検出し、型関連のノイズを除去
            tsconfig = {
                "compilerOptions": {
                    "allowJs": True,
                    "checkJs": True,
                    "noEmit": True,
                    "strict": False,              # True → False に変更
                    "noImplicitAny": False,       # 追加: 暗黙のany許可
                    "strictNullChecks": False,    # 追加: null/undefinedチェック無効
                    "noImplicitThis": False,      # 追加: 暗黙のthis許可
                    "target": "ES2020",
                    "lib": ["ES2020", "DOM"],
                    "skipLibCheck": True,
                    "noUnusedLocals": False,
                    "noUnusedParameters": False
                },
                "include": [filename]
            }
            
            config_path = tmpdir_path / 'tsconfig.json'
            config_path.write_text(json.dumps(tsconfig, indent=2), encoding='utf-8')
            
            # TSC実行
            try:
                result = subprocess.run(
                    [tsc_cmd, '--project', str(config_path)],
                    capture_output=True,
                    encoding='utf-8',
                    errors='replace',
                    cwd=tmpdir,
                    timeout=30
                )
                
                # エラーパース
                if result.returncode != 0 or result.stdout:
                    parsed_errors, parsed_warnings = self._parse_tsc_output(
                        result.stdout,
                        filename
                    )
                    errors.extend(parsed_errors)
                    warnings.extend(parsed_warnings)
                
            except subprocess.TimeoutExpired:
                logger.debug("[TSC] Type check timeout")
            except Exception as e:
                logger.debug(f"[TSC] Type check error: {e}")
        
        return {
            'has_errors': len(errors) > 0,
            'has_warnings': len(warnings) > 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _parse_tsc_output(self, output: str, filename: str) -> Tuple[List[Dict], List[Dict]]:
        """
        TypeScript Compiler出力をパース（フィルタリング機能付き）
        
        Format: filename(line,col): error/warning TS code: message
        Example: calculator.js(220,5): error TS2345: Argument of type '"÷"' is not assignable...
        
        修正: 2025-12-29
        - 純粋なJavaScriptファイルに対して、致命的エラーのみを報告
        - 型関連のノイズ（暗黙のany、型不一致等）をフィルタリング
        """
        errors = []
        warnings = []
        skipped_count = 0
        
        for line in output.split('\n'):
            if not line.strip():
                continue
            
            # tsc形式: filename(line,col): error/warning TS code: message
            match = re.match(r'.*?\((\d+),(\d+)\):\s+(error|warning)\s+TS(\d+):\s+(.+)', line)
            if match:
                ts_code = match.group(4)  # TSエラーコード（数字部分のみ）
                
                # フィルタリング: 無視すべきエラーコードはスキップ
                if ts_code in self.TS_IGNORABLE_ERROR_CODES:
                    skipped_count += 1
                    continue
                
                # 重要なエラーコードかチェック
                is_critical = ts_code in self.TS_CRITICAL_ERROR_CODES
                
                # 構文エラー（TS1xxx）は全て重要
                if ts_code.startswith('1'):
                    is_critical = True
                
                item = {
                    'file': filename,
                    'line': int(match.group(1)),
                    'column': int(match.group(2)),
                    'severity': match.group(3),
                    'code': f'TS{ts_code}',
                    'message': match.group(5).strip(),
                    'linter': 'tsc',
                    'is_critical': is_critical  # 重要度フラグを追加
                }
                
                if match.group(3) == 'error':
                    # 重要なエラーのみerrorsに追加、それ以外はwarningsに降格
                    if is_critical:
                        errors.append(item)
                    else:
                        # 重要でないエラーは警告として扱う（オプション）
                        # ここではスキップする
                        skipped_count += 1
                else:
                    warnings.append(item)
        
        # フィルタリング結果をログ出力
        if skipped_count > 0:
            logger.debug(f"[TSC] Filtered out {skipped_count} non-critical errors for {filename}")
        
        return errors, warnings


if __name__ == "__main__":
    # テスト用コード
    linter = LinterIntegration()
    print(f"Available linters: {linter.available_linters}")
    
    # サンプルコード
    test_files = {
        'test.py': '''
def hello():
    print("Hello")
    x = undefined_var  # エラー
''',
        'test.js': '''
function hello() {
    console.log("Hello");
    return undefined_var;  // エラー
}
'''
    }
    
    result = linter.lint_generated_code(test_files)
    print(f"\nLint result: {result}")