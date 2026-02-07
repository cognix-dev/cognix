"""
File Requirement Detection System

複数の独立した検出器を統合するパイプライン
Single Point of Failureを排除

Author: Shinichiro
Date: 2025-12-28
Version: 1.0.0
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


# ============================================
# Data Models
# ============================================

@dataclass
class DetectionResult:
    """
    個別検出器の結果
    
    Attributes:
        detector_name: 検出器名（例: "WebKeywordDetector"）
        required: 複数ファイル生成が必要か
        confidence: 信頼度 0.0-1.0（0: 検出なし, 1.0: 確実）
        file_types: 必要なファイル種別（例: ['html', 'css', 'js']）
        reason: 判定理由（デバッグ・ログ用）
        metadata: 追加情報（オプション）
    """
    detector_name: str
    required: bool
    confidence: float
    file_types: List[str] = field(default_factory=list)
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """バリデーション"""
        if not 0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")


@dataclass
class AggregatedResult:
    """
    統合された検出結果
    
    複数の検出器の結果を統合した最終判定
    
    Attributes:
        required: 最終判定（複数ファイル必要か）
        confidence: 統合信頼度（最高信頼度の検出器の値）
        file_types: すべてのファイル種別（和集合）
        reasons: すべての判定理由（デバッグ用）
        detectors: 検出に成功した検出器リスト
        primary_detector: 最高信頼度の検出器名
    """
    required: bool
    confidence: float
    file_types: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    detectors: List[str] = field(default_factory=list)
    primary_detector: str = ""
    
    def to_legacy_dict(self) -> Dict[str, Any]:
        """
        既存の multi_file_detection 形式に変換
        
        後方互換性のため、既存コードが期待する形式で返す
        
        Returns:
            {
                'required': bool,
                'reason': str,
                'file_types': list,
                'confidence': str,
                'detectors': list
            }
        """
        return {
            'required': self.required,
            'reason': '; '.join(self.reasons) if self.reasons else '',
            'file_types': self.file_types,
            'confidence': 'high' if self.confidence > 0.8 else 'medium' if self.confidence > 0.5 else 'low',
            'detectors': self.detectors,
        }


class BaseDetector(ABC):
    """
    検出器の抽象基底クラス
    
    すべての検出器はこのクラスを継承して実装する
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """検出器名"""
        pass
    
    @abstractmethod
    def detect(self, goal: str, context: Dict[str, Any]) -> DetectionResult:
        """
        検出を実行
        
        Args:
            goal: ユーザーのGoal文字列
            context: 追加コンテキスト（既存ファイル、Repository情報等）
        
        Returns:
            DetectionResult
        """
        pass


# ============================================
# Detectors
# ============================================

class ExplicitFileDetector(BaseDetector):
    """
    明示的なファイル名検出器
    
    Goal: "Create index.html, styles.css, and script.js"
    → 明示的に3つのファイルが指定されている
    """
    
    # 一般的なファイル拡張子
    COMMON_EXTENSIONS = [
        # Web
        'html', 'htm', 'css', 'scss', 'sass', 'less',
        'js', 'jsx', 'ts', 'tsx', 'mjs', 'cjs',
        # Python
        'py', 'pyi', 'pyw',
        # Config/Data
        'json', 'yaml', 'yml', 'toml', 'xml', 'ini', 'cfg', 'conf',
        # Docs
        'md', 'mdx', 'txt', 'rst',
        # Other
        'rb', 'php', 'java', 'cpp', 'c', 'h', 'hpp',
        'go', 'rs', 'swift', 'kt', 'scala',
        'sh', 'bash', 'ps1', 'bat', 'cmd',
        'sql', 'db',
        'vue', 'svelte',
    ]
    
    @property
    def name(self) -> str:
        return "ExplicitFileDetector"
    
    def detect(self, goal: str, context: Dict[str, Any]) -> DetectionResult:
        """
        明示的に記載されたファイル名を検出
        
        パターン: "filename.ext" 形式のファイル名を抽出
        複数（2個以上）検出された場合、複数ファイル必須と判定
        """
        goal_lower = goal.lower()
        
        # ファイル名パターン: word.ext
        extensions_pattern = '|'.join(self.COMMON_EXTENSIONS)
        pattern = rf'([\w\-]+\.({extensions_pattern}))\b'
        
        # すべてのファイル名を検出
        matches = re.findall(pattern, goal_lower)
        
        # matchesは [(filename, ext), ...] の形式
        detected_files = [match[0] for match in matches]
        detected_extensions = [match[1] for match in matches]
        
        if len(detected_files) >= 2:
            return DetectionResult(
                detector_name=self.name,
                required=True,
                confidence=1.0,  # 最高信頼度（明示的指示）
                file_types=list(set(detected_extensions)),
                reason=f"Explicit files mentioned: {len(detected_files)} files ({', '.join(detected_files[:3])}{'...' if len(detected_files) > 3 else ''})",
                metadata={
                    'detected_files': detected_files,
                    'file_count': len(detected_files)
                }
            )
        
        return DetectionResult(
            detector_name=self.name,
            required=False,
            confidence=0.0,
            reason="No multiple files explicitly mentioned"
        )


class WebKeywordDetector(BaseDetector):
    """
    Webアプリケーション検出器
    
    "web", "html", "browser" 等のキーワードから
    webアプリケーションを検出
    """
    
    # Webアプリを示すキーワード（包括的）
    WEB_KEYWORDS = [
        # 明示的
        'web', 'html', 'css', 'browser', 'webpage', 'web page',
        'web app', 'webapp', 'web application', 'website',
        'frontend', 'front-end', 'client-side', 'client side',
        # UIを示唆
        'ui', 'interface', 'visual', 'interactive', 'gui',
        # デプロイ方法を示唆
        'online', 'browser-based', 'web-based',
        # Web技術
        'javascript', 'dom', 'ajax',
    ]
    
    # 除外キーワード（CLI、バックエンド専用）
    EXCLUSION_KEYWORDS = [
        'cli', 'command line', 'terminal', 'console', 'command-line',
        'api only', 'backend only', 'server only', 'headless',
        'daemon', 'service', 'cron', 'batch',
        'rest api only', 'graphql api only',
    ]
    
    @property
    def name(self) -> str:
        return "WebKeywordDetector"
    
    def detect(self, goal: str, context: Dict[str, Any]) -> DetectionResult:
        """
        Webキーワードから検出
        
        検出ステップ:
        1. 除外キーワードチェック（CLI、バックエンド専用）
        2. Webキーワードチェック
        3. 汎用 "app" パターンチェック
        """
        goal_lower = goal.lower()
        
        # ステップ1: 除外キーワードチェック
        for exclusion in self.EXCLUSION_KEYWORDS:
            if exclusion in goal_lower:
                return DetectionResult(
                    detector_name=self.name,
                    required=False,
                    confidence=0.95,  # 高信頼度で除外
                    reason=f"Excluded by keyword: '{exclusion}' (non-web project)",
                    metadata={'exclusion_keyword': exclusion}
                )
        
        # ステップ2: Webキーワードチェック
        for keyword in self.WEB_KEYWORDS:
            if keyword in goal_lower:
                return DetectionResult(
                    detector_name=self.name,
                    required=True,
                    confidence=0.9,  # 高信頼度
                    file_types=['html', 'css', 'js'],
                    reason=f"Web keyword detected: '{keyword}'",
                    metadata={'matched_keyword': keyword}
                )
        
        # ステップ3: "XXX app" パターン（汎用）
        if 'app' in goal_lower or 'application' in goal_lower:
            # フレームワーク指定なし、CLI指定なし → デフォルトでweb app
            frameworks = ['react', 'vue', 'angular', 'svelte', 
                         'express', 'flask', 'fastapi', 'django']
            has_framework = any(fw in goal_lower for fw in frameworks)
            
            if not has_framework:
                return DetectionResult(
                    detector_name=self.name,
                    required=True,
                    confidence=0.7,  # 中信頼度（推測）
                    file_types=['html', 'css', 'js'],
                    reason="Generic 'app' detected (defaulting to web app)",
                    metadata={'pattern': 'generic_app'}
                )
        
        return DetectionResult(
            detector_name=self.name,
            required=False,
            confidence=0.0,
            reason="No web keywords detected"
        )


class AppPatternDetector(BaseDetector):
    """
    アプリケーションパターン検出器
    
    app_patterns.json の定義に基づいて
    特定のアプリタイプ（calculator, todo, dashboard等）を検出
    """
    
    @property
    def name(self) -> str:
        return "AppPatternDetector"
    
    def __init__(self, logger=None):
        """
        Args:
            logger: ログ出力用（オプション）
        """
        self.logger = logger
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> Dict[str, Any]:
        """
        app_patterns.json を読み込み
        
        優先順位:
        1. ~/.cognix/knowledge/app_patterns.json
        2. ~/.cognix/app_patterns.json
        3. プログラム本体の隣（フォールバック）
        """
        user_cognix_dir = Path.home() / '.cognix'
        
        # 優先順位1
        patterns_path = user_cognix_dir / 'knowledge' / 'app_patterns.json'
        
        # 優先順位2
        if not patterns_path.exists():
            patterns_path = user_cognix_dir / 'app_patterns.json'
        
        # 優先順位3
        if not patterns_path.exists():
            patterns_path = Path(__file__).parent / 'knowledge' / 'app_patterns.json'
        
        # 優先順位4
        if not patterns_path.exists():
            patterns_path = Path(__file__).parent / 'app_patterns.json'
        
        if patterns_path.exists():
            try:
                with open(patterns_path, 'r', encoding='utf-8') as f:
                    patterns = json.load(f)
                
                if self.logger:
                    self.logger.debug(f"[AppPatternDetector] Loaded patterns from {patterns_path}")
                
                return patterns
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"[AppPatternDetector] Failed to load patterns: {e}")
                return {}
        else:
            if self.logger:
                self.logger.debug(f"[AppPatternDetector] No patterns file found")
            return {}
    
    def detect(self, goal: str, context: Dict[str, Any]) -> DetectionResult:
        """
        app_patterns.json のパターンマッチング
        
        STEP 1: 明示的キーワード検出（高確信度）
        STEP 2: コンテキスト検出（中確信度）
        """
        if not self.patterns:
            return DetectionResult(
                detector_name=self.name,
                required=False,
                confidence=0.0,
                reason="No patterns loaded"
            )
        
        goal_lower = goal.lower()
        web_app_patterns = self.patterns.get('web_app_patterns', {})
        
        # STEP 1: 明示的キーワード検出
        for pattern_name, pattern_data in web_app_patterns.items():
            trigger_conditions = pattern_data.get('trigger_conditions', {})
            
            # v2.1.0形式と v1.0.0形式の両方をサポート
            if 'triggers' in trigger_conditions:
                explicit_section = trigger_conditions.get('triggers', {}).get('explicit_keywords', {})
                explicit_keywords = explicit_section.get('keywords', [])
            else:
                explicit_keywords = trigger_conditions.get('explicit_keywords', [])
            
            # 明示的キーワードをチェック
            for keyword in explicit_keywords:
                if keyword in goal_lower:
                    return DetectionResult(
                        detector_name=self.name,
                        required=True,
                        confidence=0.95,  # 高信頼度
                        file_types=pattern_data.get('files', []),
                        reason=f"App pattern detected (explicit): '{pattern_name}' - {pattern_data.get('reason', '')}",
                        metadata={
                            'pattern_name': pattern_name,
                            'matched_keyword': keyword,
                            'detected_pattern': pattern_data
                        }
                    )
        
        # STEP 2: コンテキスト検出（既存ファイルから推測）
        repo_data = context.get('repository_data', {})
        if repo_data:
            has_html = any(f.endswith(('.html', '.htm')) for f in repo_data.keys())
            has_css = any(f.endswith('.css') for f in repo_data.keys())
            
            if has_html or has_css:
                for pattern_name, pattern_data in web_app_patterns.items():
                    if pattern_name in goal_lower:
                        return DetectionResult(
                            detector_name=self.name,
                            required=True,
                            confidence=0.75,  # 中信頼度
                            file_types=pattern_data.get('files', []),
                            reason=f"App pattern detected (context): '{pattern_name}' in web project - {pattern_data.get('reason', '')}",
                            metadata={
                                'pattern_name': pattern_name,
                                'detected_pattern': pattern_data,
                                'context': 'existing_web_files'
                            }
                        )
        
        return DetectionResult(
            detector_name=self.name,
            required=False,
            confidence=0.0,
            reason="No app patterns matched"
        )


class FrameworkDetector(BaseDetector):
    """
    フレームワーク検出器
    
    React, Vue, Angular, Svelte 等の
    明示的なフレームワーク指定を検出
    """
    
    # フレームワーク定義
    FRAMEWORKS = {
        'React': {
            'keywords': [
                'react app', 'react application', 'create react',
                'react component', 'react project', 'using react',
                'with react', 'in react', 'react.js', 'reactjs'
            ],
            'file_types': ['jsx', 'js', 'css', 'html'],
        },
        'Vue': {
            'keywords': [
                'vue app', 'vue application', 'create vue',
                'vue component', 'vue project', 'using vue',
                'with vue', 'in vue', 'vue.js', 'vuejs'
            ],
            'file_types': ['vue', 'js', 'css', 'html'],
        },
        'Angular': {
            'keywords': [
                'angular app', 'angular application', 'create angular',
                'angular component', 'angular project', 'using angular',
                'with angular', 'in angular', 'angularjs'
            ],
            'file_types': ['ts', 'html', 'css'],
        },
        'Svelte': {
            'keywords': [
                'svelte app', 'svelte application', 'create svelte',
                'svelte component', 'svelte project', 'using svelte',
                'with svelte', 'in svelte', 'sveltejs'
            ],
            'file_types': ['svelte', 'js', 'css'],
        },
    }
    
    @property
    def name(self) -> str:
        return "FrameworkDetector"
    
    def detect(self, goal: str, context: Dict[str, Any]) -> DetectionResult:
        """フレームワークキーワードから検出"""
        goal_lower = goal.lower()
        
        for framework_name, framework_data in self.FRAMEWORKS.items():
            keywords = framework_data['keywords']
            
            for keyword in keywords:
                if keyword in goal_lower:
                    return DetectionResult(
                        detector_name=self.name,
                        required=True,
                        confidence=0.95,  # 高信頼度
                        file_types=framework_data['file_types'],
                        reason=f"{framework_name} project detected from explicit keyword: '{keyword}'",
                        metadata={
                            'framework': framework_name,
                            'matched_keyword': keyword
                        }
                    )
        
        return DetectionResult(
            detector_name=self.name,
            required=False,
            confidence=0.0,
            reason="No framework keywords detected"
        )


class BackendKeywordDetector(BaseDetector):
    """
    バックエンド検出器
    
    Flask, Django, API, Database等のキーワードから
    バックエンド要件を検出し、適切なfile_typesを返す
    
    検出カテゴリ:
    1. Pythonバックエンドフレームワーク (flask, django, fastapi)
    2. Node.jsバックエンドフレームワーク (express, nestjs)
    3. 一般バックエンドキーワード (backend, server, api)
    4. データ永続化キーワード (database, save, cloud)
    5. 認証キーワード (login, authentication, user account)
    6. リアルタイム機能キーワード (leaderboard, multiplayer)
    """
    
    # Pythonバックエンドを示すキーワード → file_types: ['python']
    PYTHON_BACKEND_KEYWORDS = [
        # フレームワーク（明示的）
        'flask', 'django', 'fastapi', 'bottle', 'pyramid',
        'tornado', 'sanic', 'starlette', 'quart',
        # 明示的なPythonバックエンド
        'python backend', 'python server', 'python api',
        'python web server', 'python rest',
    ]
    
    # Node.jsバックエンドを示すキーワード → file_types: ['node']
    NODE_BACKEND_KEYWORDS = [
        # フレームワーク（明示的）
        'express', 'express.js', 'expressjs',
        'node.js', 'nodejs', 'node backend', 'node server',
        'nestjs', 'nest.js', 'koa', 'koa.js',
        'hapi', 'hapi.js', 'fastify',
        # 明示的なNodeバックエンド
        'node api', 'node rest', 'javascript backend',
        'javascript server', 'js backend', 'js server',
    ]
    
    # 一般的なバックエンドキーワード（言語は文脈から推測）
    # デフォルトでPythonを返す（Cognixの主要ターゲット）
    GENERAL_BACKEND_KEYWORDS = [
        # 明示的バックエンド
        'backend', 'back-end', 'back end',
        'server', 'server-side', 'server side',
        # API関連
        'api', 'rest api', 'restful', 'restful api',
        'graphql', 'graphql api',
        'websocket', 'websockets', 'web socket',
        'endpoint', 'endpoints',
        # データ永続化（サーバーサイド必須）
        'database', 'db', 'sql', 'nosql',
        'postgresql', 'postgres', 'mysql', 'mariadb',
        'mongodb', 'mongo', 'sqlite', 'redis',
        'save to server', 'cloud save', 'cloud saves',
        'persist', 'persistence', 'data storage',
        # 認証・ユーザー管理（サーバーサイド必須）
        'authentication', 'auth', 'authorization',
        'login', 'logout', 'signin', 'sign in', 'sign-in',
        'signup', 'sign up', 'sign-up', 'register',
        'user account', 'user accounts', 'user management',
        'session', 'sessions', 'jwt', 'token', 'oauth',
        # リアルタイム機能（サーバーサイド必須）
        'leaderboard', 'leaderboards', 'scoreboard',
        'multiplayer', 'multi-player', 'multi player',
        'real-time', 'realtime', 'real time',
        'chat', 'messaging', 'notification', 'notifications',
    ]
    
    # 除外キーワード（フロントエンド専用を示す）
    # G-32: 否定パターン拡張（11→30個）- Tetris誤検出バグ修正
    EXCLUSION_KEYWORDS = [
        # 既存キーワード
        'frontend only', 'front-end only', 'client only',
        'static site', 'static website', 'static page',
        'no backend', 'no server', 'serverless',
        'localstorage only', 'local storage only',
        # G-32追加: フレームワーク否定
        'no frameworks', 'no framework',
        'without frameworks', 'without framework',
        # G-32追加: Pure/Vanilla/Plain パターン
        'pure html', 'pure javascript',
        'vanilla javascript', 'vanilla js',
        'plain html', 'plain javascript',
        # G-32追加: ファイル構成パターン
        'single html', 'html only',
        'html/css/js only', 'html css js only',
        # G-32追加: バックエンド不要明示
        'no database', 'without database',
        # G-32追加: クライアント限定
        'client-side only', 'browser only', 'offline only',
    ]
    
    @property
    def name(self) -> str:
        return "BackendKeywordDetector"
    
    def detect(self, goal: str, context: Dict[str, Any]) -> DetectionResult:
        """
        バックエンドキーワードから検出
        
        検出優先順位:
        1. 除外キーワードチェック
        2. Pythonバックエンドキーワード（高確信度）
        3. Node.jsバックエンドキーワード（高確信度）
        4. 一般バックエンドキーワード（中確信度、デフォルトPython）
        """
        goal_lower = goal.lower()
        
        # ステップ1: 除外キーワードチェック
        for exclusion in self.EXCLUSION_KEYWORDS:
            if exclusion in goal_lower:
                return DetectionResult(
                    detector_name=self.name,
                    required=False,
                    confidence=0.95,
                    reason=f"Excluded by keyword: '{exclusion}' (frontend-only project)",
                    metadata={'exclusion_keyword': exclusion}
                )
        
        # ステップ2: Pythonバックエンドキーワード
        for keyword in self.PYTHON_BACKEND_KEYWORDS:
            if keyword in goal_lower:
                return DetectionResult(
                    detector_name=self.name,
                    required=True,
                    confidence=0.95,
                    file_types=['python', 'html', 'css', 'js'],
                    reason=f"Python backend keyword detected: '{keyword}'",
                    metadata={
                        'matched_keyword': keyword,
                        'backend_type': 'python'
                    }
                )
        
        # ステップ3: Node.jsバックエンドキーワード
        for keyword in self.NODE_BACKEND_KEYWORDS:
            if keyword in goal_lower:
                return DetectionResult(
                    detector_name=self.name,
                    required=True,
                    confidence=0.95,
                    file_types=['node', 'js', 'html', 'css'],
                    reason=f"Node.js backend keyword detected: '{keyword}'",
                    metadata={
                        'matched_keyword': keyword,
                        'backend_type': 'node'
                    }
                )
        
        # ステップ4: 一般バックエンドキーワード（デフォルトPython）
        for keyword in self.GENERAL_BACKEND_KEYWORDS:
            if keyword in goal_lower:
                # 追加チェック: Node.js関連の文脈があるか
                node_context = any(kw in goal_lower for kw in ['javascript', 'js', 'node', 'npm'])
                
                if node_context:
                    return DetectionResult(
                        detector_name=self.name,
                        required=True,
                        confidence=0.85,
                        file_types=['node', 'js', 'html', 'css'],
                        reason=f"Backend keyword detected: '{keyword}' (Node.js context)",
                        metadata={
                            'matched_keyword': keyword,
                            'backend_type': 'node',
                            'context_hint': 'javascript_related'
                        }
                    )
                else:
                    return DetectionResult(
                        detector_name=self.name,
                        required=True,
                        confidence=0.85,
                        file_types=['python', 'html', 'css', 'js'],
                        reason=f"Backend keyword detected: '{keyword}' (defaulting to Python)",
                        metadata={
                            'matched_keyword': keyword,
                            'backend_type': 'python',
                            'context_hint': 'default'
                        }
                    )
        
        return DetectionResult(
            detector_name=self.name,
            required=False,
            confidence=0.0,
            reason="No backend keywords detected"
        )


class RepositoryDetector(BaseDetector):
    """
    リポジトリベース検出器
    
    既存のファイル構成から必要なファイルを推測
    """
    
    @property
    def name(self) -> str:
        return "RepositoryDetector"
    
    def detect(self, goal: str, context: Dict[str, Any]) -> DetectionResult:
        """
        既存ファイルから推測
        
        ルール:
        - HTML + JS 存在 → UI/ロジック両方必要
        - Python 3+ ファイル存在 → マルチファイル修正
        """
        repo_data = context.get('repository_data', {})
        
        if not repo_data or len(repo_data) == 0:
            return DetectionResult(
                detector_name=self.name,
                required=False,
                confidence=0.0,
                reason="New project (no existing files)"
            )
        
        goal_lower = goal.lower()
        
        # 操作キーワード検出
        operation_keywords = [
            'add', 'create', 'implement', 'build',
            'modify', 'update', 'change', 'extend',
            'support', 'enable', 'allow', 'fix'
        ]
        
        has_operation = any(kw in goal_lower for kw in operation_keywords)
        
        if not has_operation:
            return DetectionResult(
                detector_name=self.name,
                required=False,
                confidence=0.0,
                reason="No operation keywords detected"
            )
        
        # ファイルタイプ分析
        has_html = any(f.endswith(('.html', '.htm')) for f in repo_data.keys())
        has_js = any(f.endswith('.js') or f.endswith('.jsx') for f in repo_data.keys())
        has_css = any(f.endswith('.css') or f.endswith('.scss') for f in repo_data.keys())
        
        # HTML + JS プロジェクト
        if has_html and has_js:
            file_types = ['html', 'js']
            if has_css:
                file_types.append('css')
            
            return DetectionResult(
                detector_name=self.name,
                required=True,
                confidence=0.8,  # 高信頼度
                file_types=file_types,
                reason="Repository contains HTML and JS files - UI and logic changes likely needed",
                metadata={
                    'has_html': has_html,
                    'has_js': has_js,
                    'has_css': has_css
                }
            )
        
        # Pythonマルチファイルプロジェクト
        py_files = [f for f in repo_data.keys() if f.endswith('.py')]
        if len(py_files) >= 3:
            return DetectionResult(
                detector_name=self.name,
                required=True,
                confidence=0.75,  # 中信頼度
                file_types=['python'],
                reason=f"Repository contains {len(py_files)} Python files - multi-file modification likely",
                metadata={
                    'python_file_count': len(py_files)
                }
            )
        
        return DetectionResult(
            detector_name=self.name,
            required=False,
            confidence=0.0,
            reason="No clear multi-file requirement from repository"
        )


# ============================================
# Pipeline
# ============================================

class FileRequirementDetector:
    """
    ファイル要件検出パイプライン
    
    複数の独立した検出器を実行し、結果を統合
    """
    
    def __init__(self, logger=None, repository_analyzer=None):
        """
        Args:
            logger: ログ出力用（オプション）
            repository_analyzer: リポジトリアナライザー（オプション）
        """
        self.logger = logger
        self.repository_analyzer = repository_analyzer
        
        # 検出器を優先度順に登録
        self.detectors: List[BaseDetector] = [
            ExplicitFileDetector(),           # 優先度1: 明示的ファイル名
            WebKeywordDetector(),             # 優先度2: "web", "html"
            FrameworkDetector(),              # 優先度3: "React", "Vue"
            BackendKeywordDetector(),         # 優先度4: "Flask", "backend", "API"
            AppPatternDetector(logger=logger),# 優先度5: app_patterns.json
            RepositoryDetector(),             # 優先度6: 既存ファイルから推測
        ]
    
    def detect(self, goal: str, context: Optional[Dict[str, Any]] = None) -> AggregatedResult:
        """
        すべての検出器を実行し、結果を統合
        
        Args:
            goal: ユーザーのGoal文字列
            context: 追加コンテキスト
                - repository_data: Dict[filename, content]
                - existing_files: Dict[filename, content]
        
        Returns:
            AggregatedResult: 統合された検出結果
        """
        if context is None:
            context = {}
        
        # repository_analyzer がある場合、repository_data を追加
        if self.repository_analyzer and hasattr(self.repository_analyzer, 'memory'):
            context['repository_data'] = self.repository_analyzer.memory.repository_data
        
        results: List[DetectionResult] = []
        
        # すべての検出器を実行（1つが失敗しても続行）
        for detector in self.detectors:
            try:
                result = detector.detect(goal, context)
                
                if result.confidence > 0:
                    results.append(result)
                    
                    if self.logger:
                        self.logger.debug(
                            f"[{detector.name}] "
                            f"required={result.required}, "
                            f"confidence={result.confidence:.2f}, "
                            f"reason='{result.reason}'"
                        )
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"[{detector.name}] Detection failed: {e}")
                # 失敗しても続行（他の検出器を試す）
        
        # 統合判定
        aggregated = self._aggregate(results)
        
        if self.logger:
            self.logger.debug(
                f"[Pipeline] Aggregated result: "
                f"required={aggregated.required}, "
                f"confidence={aggregated.confidence:.2f}, "
                f"primary={aggregated.primary_detector}"
            )
        
        return aggregated
    
    def _aggregate(self, results: List[DetectionResult]) -> AggregatedResult:
        """
        複数の検出結果を統合
        
        統合ルール:
        1. 信頼度でソート（降順）
        2. 最高信頼度の結果を基準とする
        3. file_typesは和集合を取る（保守的判定）
        4. 矛盾がある場合は保守的に判定（より多くのファイルを生成）
        """
        if not results:
            return AggregatedResult(
                required=False,
                confidence=0.0,
                file_types=[],
                reasons=["No detectors found any requirements"],
                detectors=[],
                primary_detector="None"
            )
        
        # 信頼度でソート（降順）
        results.sort(key=lambda r: r.confidence, reverse=True)
        
        # 最高信頼度の結果を基準
        best = results[0]
        
        # required=True の検出器を集める
        positive_results = [r for r in results if r.required]
        
        if not positive_results:
            # すべての検出器が required=False
            return AggregatedResult(
                required=False,
                confidence=best.confidence,
                file_types=[],
                reasons=[r.reason for r in results],
                detectors=[r.detector_name for r in results],
                primary_detector=best.detector_name
            )
        
        # file_typesの和集合を取る（保守的判定）
        all_file_types = set()
        for result in positive_results:
            all_file_types.update(result.file_types)
        
        return AggregatedResult(
            required=True,
            confidence=positive_results[0].confidence,  # 最高信頼度
            file_types=list(all_file_types),
            reasons=[r.reason for r in positive_results],
            detectors=[r.detector_name for r in positive_results],
            primary_detector=positive_results[0].detector_name
        )