"""
Cognix CLI メインモジュール（ファサード）

このモジュールは、Cognixコマンドラインインターフェースのメインエントリーポイントです。
既存のインポート構造を維持するためのファサードとして機能し、実際の実装を分割後のモジュールに移譲します。
"""

import cmd
from typing import Dict, Any, Optional, List

# 実際のCLI実装をインポート
from cognix.config import Config
from cognix.cli_main import CognixCLI as RealCLI

class CognixCLI(cmd.Cmd):
    """CLI.pyの後方互換性維持用ファサード
    
    既存のインポート構造を維持するためのラッパークラス
    実際の実装は分割後のモジュールに移譲します
    """
    
    def __init__(self, config: Config, auto_mode: bool = False):
        # 実際のCLIを初期化
        self.__dict__['_real_cli'] = RealCLI(config, auto_mode)
        
        # 基本クラスの初期化
        cmd.Cmd.__init__(self)

    def __getattr__(self, name):
        """すべての未定義属性を_real_cliに委譲"""
        real_cli = self.__dict__.get('_real_cli')
        
        if real_cli is None:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}' (_real_cli not initialized)")
        
        # すべての属性アクセスを_real_cliに委譲
        try:
            return getattr(real_cli, name)
        except AttributeError:
            # _real_cliにも存在しない場合は標準のAttributeErrorを発生
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name, value):
        """属性設定を適切に委譲"""
        real_cli = self.__dict__.get('_real_cli')
        
        # _real_cliが存在する場合は委譲
        if real_cli is not None:
            setattr(real_cli, name, value)
        # 初期化中の場合は直接設定
        else:
            self.__dict__[name] = value
    
    # 以下、必須メソッドの委譲
    
    def run(self):
        """メインループの実行を委譲"""
        return self._real_cli.run()
    
    def cmdloop(self, intro=None):
        """cmdloopを委譲"""
        return self._real_cli.cmdloop(intro)
    
    def default(self, line: str):
        """通常入力処理を委譲"""
        return self._real_cli.default(line)

    def emptyline(self):
        """空行処理を委譲"""
        return self._real_cli.emptyline()
    
    def precmd(self, line):
        """コマンド前処理を委譲"""
        return self._real_cli.precmd(line)
    
    def postcmd(self, stop, line):
        """コマンド後処理を委譲"""
        return self._real_cli.postcmd(stop, line)
    
    def onecmd(self, line):
        """単一コマンド実行を委譲"""
        return self._real_cli.onecmd(line)