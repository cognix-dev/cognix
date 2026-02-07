"""
Cognix Safe Editor - 安全編集システム

既存のコードベースへの影響を最小限に抑えながら、
安全で可逆的なファイル編集機能を提供します。
"""

from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
import difflib
import tempfile
import shutil
import ast
import json
import uuid
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import re


class EditRiskLevel(Enum):
    """編集リスクレベル"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EditContext:
    """編集コンテキスト情報"""
    file_path: str
    original_content: str
    proposed_content: str
    edit_type: str  # "modify", "add", "delete"
    risk_level: EditRiskLevel
    impact_score: float
    affected_files: List[str]
    safety_checks: Dict[str, bool]
    recommendations: List[str]
    backup_path: Optional[str] = None
    edit_id: Optional[str] = None
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（JSON保存用）"""
        return {
            'file_path': self.file_path,
            'original_content': self.original_content,
            'proposed_content': self.proposed_content,
            'edit_type': self.edit_type,
            'risk_level': self.risk_level.value,
            'impact_score': self.impact_score,
            'affected_files': self.affected_files,
            'safety_checks': self.safety_checks,
            'recommendations': self.recommendations,
            'backup_path': self.backup_path,
            'edit_id': self.edit_id,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EditContext':
        """辞書から復元（JSON読み込み用）"""
        data['risk_level'] = EditRiskLevel(data['risk_level'])
        return cls(**data)


class BackupManager:
    """編集バックアップの管理システム"""

    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.backup_dir / "backup_metadata.json"

    def create_backup(self, file_path: str) -> str:
        """タイムスタンプ付きバックアップを作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        file_name = Path(file_path).name
        backup_name = f"{file_name}_{timestamp}.backup"
        backup_path = self.backup_dir / backup_name

        # ファイルをバックアップ
        shutil.copy2(file_path, backup_path)
        
        # メタデータを保存
        self._save_backup_metadata(file_path, str(backup_path), timestamp)
        
        return str(backup_path)

    def _save_backup_metadata(self, original_path: str, backup_path: str, timestamp: str):
        """バックアップメタデータを保存"""
        metadata = self._load_metadata()
        
        if original_path not in metadata:
            metadata[original_path] = []
            
        metadata[original_path].append({
            "backup_path": backup_path,
            "timestamp": timestamp,
            "created_at": datetime.now().isoformat()
        })
        
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def _load_metadata(self) -> Dict[str, Any]:
        """バックアップメタデータを読み込み"""
        if not self.metadata_file.exists():
            return {}
        
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def list_backups(self, file_path: str) -> List[Dict[str, Any]]:
        """ファイルのバックアップリストを取得"""
        metadata = self._load_metadata()
        return metadata.get(file_path, [])

    def restore_from_backup(self, original_path: str, backup_path: str) -> bool:
        """バックアップから復元"""
        try:
            if Path(backup_path).exists():
                shutil.copy2(backup_path, original_path)
                return True
            return False
        except Exception:
            return False


class SafeEditor:
    """安全な編集操作を提供するシステム"""

    def __init__(self, memory_manager, diff_engine=None, impact_analyzer=None, repository_manager=None):
        self.memory = memory_manager
        self.diff_engine = diff_engine
        self.impact_analyzer = impact_analyzer
        self.repository_manager = repository_manager
        
        # バックアップディレクトリの設定
        self.backup_dir = Path.cwd() / ".cognix" / "backups"
        self.backup_manager = BackupManager(self.backup_dir)
        
        # 編集履歴の管理
        self.history_file = Path.cwd() / ".cognix" / "edit_history.json"
        self.edit_history: List[EditContext] = self._load_edit_history()
        
        # 安全性設定の読み込み
        self.safety_config = self._load_safety_config()

    def prepare_safe_edit(self, file_path: str, proposed_content: str) -> EditContext:
        """
        安全編集の準備と分析

        Args:
            file_path: 編集対象ファイルパス
            proposed_content: 提案される新しい内容

        Returns:
            EditContext: 編集コンテキスト情報
        """
        # ファイルパスの正規化
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # 現在の内容を読み込み
        try:
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except UnicodeDecodeError:
            with open(file_path_obj, 'r', encoding='shift_jis') as f:
                original_content = f.read()

        # 編集タイプの判定
        edit_type = self._determine_edit_type(original_content, proposed_content)

        # 影響解析（他チャットのimpact_analyzerと連携）
        impact_info = self._analyze_impact(file_path, edit_type, original_content, proposed_content)

        # リスクレベルの計算
        risk_level = self._calculate_risk_level(original_content, proposed_content, impact_info)

        # 安全性チェック
        safety_checks = self._perform_safety_checks(original_content, proposed_content, file_path)

        # 推奨事項の生成
        recommendations = self._generate_recommendations(
            original_content, proposed_content, impact_info, safety_checks
        )

        return EditContext(
            file_path=str(file_path_obj),
            original_content=original_content,
            proposed_content=proposed_content,
            edit_type=edit_type,
            risk_level=risk_level,
            impact_score=impact_info.get("impact_score", 0.0),
            affected_files=impact_info.get("affected_files", []),
            safety_checks=safety_checks,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )

    def validate_edit_safety(self, edit_context: EditContext) -> Dict[str, Any]:
        """
        編集の安全性を検証

        Args:
            edit_context: 編集コンテキスト

        Returns:
            検証結果の辞書
        """
        validation_result = {
            "is_safe": True,
            "risk_level": edit_context.risk_level.value,
            "blocking_issues": [],
            "warnings": [],
            "recommendations": edit_context.recommendations.copy(),
            "can_proceed": True
        }

        # 構文チェック
        syntax_check = self._validate_syntax(edit_context.proposed_content, edit_context.file_path)
        if not syntax_check["valid"]:
            validation_result["blocking_issues"].append(f"Syntax error: {syntax_check['error']}")
            validation_result["is_safe"] = False
            validation_result["can_proceed"] = False

        # インポートチェック
        import_check = self._validate_imports(edit_context.proposed_content)
        if import_check["missing_imports"]:
            validation_result["warnings"].extend([
                f"Undefined import: {imp}" for imp in import_check["missing_imports"]
            ])

        # 依存関係チェック
        if edit_context.impact_score > 0.7:
            validation_result["warnings"].append("High-impact change detected")
            
        if edit_context.risk_level == EditRiskLevel.CRITICAL:
            validation_result["blocking_issues"].append("Critical risk detected")
            validation_result["can_proceed"] = False

        # 既存機能の破壊チェック
        compatibility_check = self._check_backward_compatibility(edit_context)
        if not compatibility_check["compatible"]:
            validation_result["warnings"].extend(compatibility_check["issues"])

        # 安全性チェック失敗項目の確認
        failed_checks = [check for check, result in edit_context.safety_checks.items() if not result]
        if failed_checks:
            if any("critical" in check.lower() for check in failed_checks):
                validation_result["can_proceed"] = False
            validation_result["warnings"].extend([f"Safety check failed: {check}" for check in failed_checks])

        return validation_result

    def execute_safe_edit(self, edit_context: EditContext, force: bool = False) -> Dict[str, Any]:
        """
        安全編集を実行

        Args:
            edit_context: 編集コンテキスト
            force: 強制実行フラグ

        Returns:
            実行結果の辞書
        """
        # 安全性検証
        if not force:
            validation = self.validate_edit_safety(edit_context)
            if not validation["can_proceed"]:
                return {
                    "success": False,
                    "error": "Safety validation failed",
                    "blocking_issues": validation["blocking_issues"]
                }

        # バックアップ作成
        try:
            backup_path = self.backup_manager.create_backup(edit_context.file_path)
            edit_context.backup_path = backup_path
        except Exception as e:
            return {
                "success": False,
                "error": f"Backup creation failed: {str(e)}"
            }

        try:
            # 差分エンジンを使用した適用（利用可能な場合）
            if self.diff_engine and hasattr(self.diff_engine, 'apply_changes'):
                diff_result = self.diff_engine.apply_changes(
                    edit_context.file_path,
                    edit_context.original_content,
                    edit_context.proposed_content
                )
            else:
                # 直接書き込み
                with open(edit_context.file_path, 'w', encoding='utf-8') as f:
                    f.write(edit_context.proposed_content)
                diff_result = {"applied": True, "method": "direct_write"}

            # 編集履歴に記録
            edit_id = self._generate_edit_id()
            edit_context.edit_id = edit_id
            self.edit_history.append(edit_context)

            # 編集履歴を永続化
            self._save_edit_history()

            return {
                "success": True,
                "backup_path": backup_path,
                "changes_applied": diff_result,
                "warnings": edit_context.recommendations,
                "edit_id": edit_id
            }

        except Exception as e:
            # エラー時はバックアップから復元
            if edit_context.backup_path:
                restored = self.backup_manager.restore_from_backup(
                    edit_context.file_path, 
                    edit_context.backup_path
                )
                return {
                    "success": False,
                    "error": f"Error during edit execution: {str(e)}",
                    "backup_restored": restored
                }
            else:
                return {
                    "success": False,
                    "error": f"Error during edit execution: {str(e)}",
                    "backup_restored": False
                }

    def create_backup(self, file_path: str) -> str:
        """ファイルバックアップを作成"""
        return self.backup_manager.create_backup(file_path)

    def rollback_edit(self, edit_id: str) -> Dict[str, Any]:
        """編集をロールバック"""
        # 編集履歴から該当する編集を検索
        target_edit = None
        for edit in self.edit_history:
            if edit.edit_id == edit_id:
                target_edit = edit
                break

        if not target_edit:
            return {
                "success": False,
                "error": f"Edit ID '{edit_id}' not found"
            }

        if not target_edit.backup_path:
            return {
                "success": False,
                "error": "Backup file not found"
            }

        # バックアップから復元
        try:
            restored = self.backup_manager.restore_from_backup(
                target_edit.file_path,
                target_edit.backup_path
            )

            if restored:
                return {
                    "success": True,
                    "restored_file": target_edit.file_path,
                    "backup_used": target_edit.backup_path
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to restore from backup"
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error during rollback: {str(e)}"
            }

    def get_edit_suggestions(self, file_path: str, change_description: str) -> List[Dict[str, Any]]:
        """編集提案を生成"""
        suggestions = []

        # ファイルの現在の内容を読み込み
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
        except FileNotFoundError:
            return [{"error": f"File not found: {file_path}"}]

        # リポジトリマネージャーとの連携（利用可能な場合）
        if self.repository_manager and hasattr(self.repository_manager, 'get_file_context_for_editing'):
            context = self.repository_manager.get_file_context_for_editing(file_path)
            suggestions.append({
                "type": "context_suggestion",
                "description": "Suggestion based on repository context",
                "details": context
            })

        # 基本的な編集提案
        suggestions.extend([
            {
                "type": "safety_suggestion",
                "description": "We recommend creating a backup before making changes",
                "action": "create_backup"
            },
            {
                "type": "validation_suggestion", 
                "description": "Please review changes in preview mode",
                "action": "preview_mode"
            }
        ])

        return suggestions

    def analyze_change_patterns(self, file_path: str) -> Dict[str, Any]:
        """変更パターンを分析"""
        # 過去の編集履歴から該当ファイルの変更パターンを分析
        file_edits = [edit for edit in self.edit_history if edit.file_path == file_path]
        
        if not file_edits:
            return {"pattern": "no_history", "recommendations": []}

        # 変更頻度の分析
        risk_levels = [edit.risk_level.value for edit in file_edits]
        avg_impact = sum(edit.impact_score for edit in file_edits) / len(file_edits)

        return {
            "pattern": "analyzed",
            "edit_count": len(file_edits),
            "average_impact_score": avg_impact,
            "risk_distribution": {level: risk_levels.count(level) for level in set(risk_levels)},
            "recommendations": self._generate_pattern_recommendations(file_edits)
        }

    # --- 内部メソッド ---

    def _determine_edit_type(self, original: str, proposed: str) -> str:
        """編集タイプを判定"""
        if not original.strip() and proposed.strip():
            return "add"
        elif original.strip() and not proposed.strip():
            return "delete"
        else:
            return "modify"

    def _analyze_impact(self, file_path: str, edit_type: str, original: str, proposed: str) -> Dict[str, Any]:
        """影響を解析"""
        impact_info = {
            "impact_score": 0.0,
            "affected_files": [],
            "change_type": edit_type
        }

        # 外部impact_analyzerとの連携
        if self.impact_analyzer and hasattr(self.impact_analyzer, 'analyze_change_impact'):
            try:
                external_impact = self.impact_analyzer.analyze_change_impact(file_path, edit_type)
                impact_info.update(external_impact)
                return impact_info
            except Exception:
                pass  # 外部解析が失敗した場合は内部解析にフォールバック

        # 内部影響解析
        # ファイル拡張子に基づく基本スコア
        file_ext = Path(file_path).suffix.lower()
        if file_ext == '.py':
            impact_info["impact_score"] = self._analyze_python_impact(original, proposed)
        elif file_ext in ['.js', '.ts']:
            impact_info["impact_score"] = self._analyze_javascript_impact(original, proposed)
        else:
            impact_info["impact_score"] = self._analyze_generic_impact(original, proposed)

        return impact_info

    def _analyze_python_impact(self, original: str, proposed: str) -> float:
        """Python固有の影響解析"""
        score = 0.0

        # import文の変更をチェック
        orig_imports = set(re.findall(r'^(?:from .+ )?import .+', original, re.MULTILINE))
        new_imports = set(re.findall(r'^(?:from .+ )?import .+', proposed, re.MULTILINE))
        
        if orig_imports != new_imports:
            score += 0.3

        # 関数定義の変更をチェック
        orig_functions = set(re.findall(r'^def (\w+)', original, re.MULTILINE))
        new_functions = set(re.findall(r'^def (\w+)', proposed, re.MULTILINE))
        
        removed_functions = orig_functions - new_functions
        if removed_functions:
            score += 0.5

        # クラス定義の変更をチェック
        orig_classes = set(re.findall(r'^class (\w+)', original, re.MULTILINE))
        new_classes = set(re.findall(r'^class (\w+)', proposed, re.MULTILINE))
        
        removed_classes = orig_classes - new_classes
        if removed_classes:
            score += 0.4

        return min(score, 1.0)

    def _analyze_javascript_impact(self, original: str, proposed: str) -> float:
        """JavaScript/TypeScript固有の影響解析"""
        score = 0.0

        # export文の変更をチェック
        orig_exports = set(re.findall(r'export .*', original))
        new_exports = set(re.findall(r'export .*', proposed))
        
        if orig_exports != new_exports:
            score += 0.4

        # 関数宣言の変更をチェック
        orig_functions = set(re.findall(r'function (\w+)', original))
        new_functions = set(re.findall(r'function (\w+)', proposed))
        
        removed_functions = orig_functions - new_functions
        if removed_functions:
            score += 0.3

        return min(score, 1.0)

    def _analyze_generic_impact(self, original: str, proposed: str) -> float:
        """一般的な影響解析"""
        # 変更行数ベースの基本スコア
        orig_lines = original.splitlines()
        new_lines = proposed.splitlines()
        
        diff = list(difflib.unified_diff(orig_lines, new_lines, n=0))
        change_count = len([line for line in diff if line.startswith(('+', '-'))])
        total_lines = max(len(orig_lines), len(new_lines), 1)
        
        return min(change_count / total_lines, 1.0)

    def _calculate_risk_level(self, original: str, proposed: str, impact_info: Dict[str, Any]) -> EditRiskLevel:
        """リスクレベルを計算"""
        impact_score = impact_info.get("impact_score", 0.0)
        
        if impact_score < 0.2:
            return EditRiskLevel.LOW
        elif impact_score < 0.5:
            return EditRiskLevel.MEDIUM
        elif impact_score < 0.8:
            return EditRiskLevel.HIGH
        else:
            return EditRiskLevel.CRITICAL

    def _perform_safety_checks(self, original: str, proposed: str, file_path: str) -> Dict[str, bool]:
        """安全性チェックを実行"""
        checks = {}

        # 構文チェック
        syntax_result = self._validate_syntax(proposed, file_path)
        checks["syntax_valid"] = syntax_result["valid"]

        # インポートチェック
        import_result = self._validate_imports(proposed)
        checks["imports_resolved"] = len(import_result["missing_imports"]) == 0

        # 既存関数の保持チェック
        checks["functions_preserved"] = self._check_functions_preserved(original, proposed)

        # 既存クラスの保持チェック
        checks["classes_preserved"] = self._check_classes_preserved(original, proposed)

        # API互換性チェック
        checks["api_compatible"] = self._check_api_compatibility(original, proposed)

        # 無限ループチェック
        checks["no_infinite_loops"] = self._check_infinite_loops(proposed)

        # メモリ安全性チェック
        checks["memory_safe"] = self._check_memory_safety(proposed)

        return checks

    def _validate_syntax(self, content: str, file_path: str) -> Dict[str, Any]:
        """構文を検証"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.py':
            try:
                ast.parse(content)
                return {"valid": True, "error": None}
            except SyntaxError as e:
                return {"valid": False, "error": f"Line {e.lineno}: {e.msg}"}
        else:
            # Python以外のファイルは基本的な検証のみ
            return {"valid": True, "error": None}

    def _validate_imports(self, content: str) -> Dict[str, Any]:
        """インポートを検証"""
        # 簡単な実装：実際には利用可能なモジュールをチェック
        import_lines = re.findall(r'^(?:from .+ )?import (.+)', content, re.MULTILINE)
        missing_imports = []
        
        for import_line in import_lines:
            # 基本的なPython標準ライブラリのチェック
            modules = [mod.strip() for mod in import_line.split(',')]
            for module in modules:
                module_name = module.split('.')[0].split(' as ')[0]
                if module_name and not self._is_known_module(module_name):
                    missing_imports.append(module_name)
        
        return {"missing_imports": list(set(missing_imports))}

    def _is_known_module(self, module_name: str) -> bool:
        """既知のモジュールかどうかチェック"""
        known_modules = {
            'os', 'sys', 'json', 'datetime', 'pathlib', 'typing', 'dataclasses',
            'enum', 're', 'difflib', 'tempfile', 'shutil', 'uuid', 'ast'
        }
        return module_name in known_modules

    def _check_functions_preserved(self, original: str, proposed: str) -> bool:
        """既存関数が保持されているかチェック"""
        orig_functions = set(re.findall(r'^def (\w+)', original, re.MULTILINE))
        new_functions = set(re.findall(r'^def (\w+)', proposed, re.MULTILINE))
        
        # 既存の公開関数（_で始まらない）が削除されていないかチェック
        orig_public_functions = {f for f in orig_functions if not f.startswith('_')}
        new_public_functions = {f for f in new_functions if not f.startswith('_')}
        
        return orig_public_functions.issubset(new_public_functions)

    def _check_classes_preserved(self, original: str, proposed: str) -> bool:
        """既存クラスが保持されているかチェック"""
        orig_classes = set(re.findall(r'^class (\w+)', original, re.MULTILINE))
        new_classes = set(re.findall(r'^class (\w+)', proposed, re.MULTILINE))
        
        # 既存の公開クラスが削除されていないかチェック
        orig_public_classes = {c for c in orig_classes if not c.startswith('_')}
        new_public_classes = {c for c in new_classes if not c.startswith('_')}
        
        return orig_public_classes.issubset(new_public_classes)

    def _check_api_compatibility(self, original: str, proposed: str) -> bool:
        """API互換性をチェック"""
        # 簡単な実装：公開関数とクラスの保持チェック
        functions_ok = self._check_functions_preserved(original, proposed)
        classes_ok = self._check_classes_preserved(original, proposed)
        
        return functions_ok and classes_ok

    def _check_infinite_loops(self, content: str) -> bool:
        """無限ループの可能性をチェック"""
        # 簡単な実装：while Trueや明らかな無限ループパターンを検出
        dangerous_patterns = [
            r'while\s+True\s*:(?!\s*#.*break)',  # while True: でbreakコメントがない
            r'while\s+1\s*:',  # while 1:
            r'for.*:\s*while\s+True:'  # forループ内のwhile True
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                return False
        
        return True

    def _check_memory_safety(self, content: str) -> bool:
        """メモリ安全性をチェック"""
        # 危険なパターンを検出
        dangerous_patterns = [
            r'exec\s*\(',  # exec関数の使用
            r'eval\s*\(',  # eval関数の使用
            r'__import__\s*\(',  # 動的インポート
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, content):
                return False
        
        return True

    def _check_backward_compatibility(self, edit_context: EditContext) -> Dict[str, Any]:
        """後方互換性をチェック"""
        original = edit_context.original_content
        proposed = edit_context.proposed_content
        
        issues = []
        
        # 公開API（関数・クラス）の削除チェック
        if not self._check_functions_preserved(original, proposed):
            issues.append("Public functions have been removed")
            
        if not self._check_classes_preserved(original, proposed):
            issues.append("Public classes have been removed")
        
        # インポート変更による互換性問題
        orig_imports = set(re.findall(r'^(?:from .+ )?import .+', original, re.MULTILINE))
        new_imports = set(re.findall(r'^(?:from .+ )?import .+', proposed, re.MULTILINE))
        
        removed_imports = orig_imports - new_imports
        if removed_imports:
            issues.append(f"Imports have been removed: {list(removed_imports)}")
        
        return {
            "compatible": len(issues) == 0,
            "issues": issues
        }

    def _generate_recommendations(self, original: str, proposed: str, impact_info: Dict[str, Any], safety_checks: Dict[str, bool]) -> List[str]:
        """推奨事項を生成"""
        recommendations = []
        
        # 安全性チェック結果に基づく推奨事項
        failed_checks = [check for check, result in safety_checks.items() if not result]
        if failed_checks:
            recommendations.append("Please fix failed safety check items")
            
        # 影響度に基づく推奨事項
        impact_score = impact_info.get("impact_score", 0.0)
        if impact_score > 0.5:
            recommendations.append("High-impact change detected. Please run thorough tests")
            
        if impact_score > 0.7:
            recommendations.append("Critical change detected. Consider staged deployment")
            
        # ファイル固有の推奨事項
        if "def " in proposed and "def " in original:
            recommendations.append("Function changes detected. Consider updating documentation")
            
        if "class " in proposed and "class " in original:
            recommendations.append("Class changes detected. Check impact on inherited classes")
        
        # 一般的な推奨事項
        if not recommendations:
            recommendations.append("Backup will be created before changes")
            
        return recommendations

    def _generate_pattern_recommendations(self, file_edits: List[EditContext]) -> List[str]:
        """変更パターンに基づく推奨事項を生成"""
        recommendations = []
        
        # 頻繁な編集のパターン
        if len(file_edits) > 5:
            recommendations.append("This file is frequently edited. Consider refactoring")
            
        # 高リスク変更が多い場合
        high_risk_count = sum(1 for edit in file_edits if edit.risk_level in [EditRiskLevel.HIGH, EditRiskLevel.CRITICAL])
        if high_risk_count > len(file_edits) * 0.5:
            recommendations.append("This file has many high-risk changes. Please edit more carefully")
            
        return recommendations

    def _generate_edit_id(self) -> str:
        """一意の編集IDを生成"""
        return f"edit_{uuid.uuid4().hex[:8]}"

    def _load_edit_history(self) -> List[EditContext]:
        """編集履歴を読み込み"""
        if not self.history_file.exists():
            return []
            
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [EditContext.from_dict(item) for item in data]
        except (json.JSONDecodeError, IOError, KeyError):
            return []

    def _save_edit_history(self):
        """編集履歴を保存"""
        # ディレクトリが存在しない場合は作成
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 最新100件のみ保持
        history_to_save = self.edit_history[-100:]
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([edit.to_dict() for edit in history_to_save], f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Failed to save edit history: {e}")

    def _load_safety_config(self) -> Dict[str, Any]:
        """安全性設定を読み込み"""
        config_file = Path.cwd() / ".cognix" / "safety_config.json"
        
        default_config = {
            "max_impact_score": 0.8,
            "require_backup": True,
            "auto_syntax_check": True,
            "block_critical_changes": True
        }
        
        if not config_file.exists():
            return default_config
            
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                default_config.update(config)
                return default_config
        except (json.JSONDecodeError, IOError):
            return default_config

    # --- 他チャットとの連携メソッド ---

    def integrate_impact_analysis(self, impact_analyzer):
        """影響解析エンジンとの統合"""
        self.impact_analyzer = impact_analyzer

    def integrate_repository_manager(self, repository_manager):
        """リポジトリマネージャーとの統合"""
        self.repository_manager = repository_manager

    def get_impact_aware_edit_context(self, file_path: str, proposed_content: str) -> EditContext:
        """影響解析を考慮した編集コンテキストを作成"""
        # 基本的な編集コンテキストを作成
        edit_context = self.prepare_safe_edit(file_path, proposed_content)
        
        # 追加の影響解析（外部impact_analyzerを使用）
        if self.impact_analyzer:
            try:
                additional_impact = self.impact_analyzer.analyze_detailed_impact(
                    file_path, edit_context.original_content, proposed_content
                )
                # 影響情報を更新
                edit_context.impact_score = max(edit_context.impact_score, additional_impact.get("impact_score", 0.0))
                edit_context.affected_files.extend(additional_impact.get("additional_affected_files", []))
            except Exception as e:
                edit_context.recommendations.append(f"External impact analysis error: {str(e)}")
        
        return edit_context

    def get_repository_aware_suggestions(self, file_path: str) -> List[Dict[str, Any]]:
        """リポジトリ情報を考慮した編集提案を生成"""
        suggestions = []
        
        if self.repository_manager:
            try:
                repo_context = self.repository_manager.get_file_context_for_editing(file_path)
                
                suggestions.append({
                    "type": "repository_context",
                    "description": "Repository context information",
                    "context": repo_context
                })
                
                # リポジトリ情報に基づく具体的な提案
                if repo_context.get("is_core_file", False):
                    suggestions.append({
                        "type": "core_file_warning",
                        "description": "This is a core system file. Please edit carefully",
                        "priority": "high"
                    })
                
                if repo_context.get("has_dependents", False):
                    suggestions.append({
                        "type": "dependency_warning", 
                        "description": f"This file has {repo_context.get('dependent_count', 0)} dependent files",
                        "priority": "medium"
                    })
                    
            except Exception as e:
                suggestions.append({
                    "type": "error",
                    "description": f"Repository information retrieval error: {str(e)}"
                })
        
        return suggestions