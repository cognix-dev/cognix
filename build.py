#!/usr/bin/env python3
"""
Cognix v0.2.0 - Nuitka Build Script (Windows)

再現可能なビルドプロセスを提供するビルドスクリプト。
cognix_nuitka_build_steps.md で検証済みのコマンドを自動化。

必須環境:
  - Python 3.13+
  - Nuitka 2.8+
  - Visual Studio Build Tools 2022 (MSVC v143)

使い方:
  python build.py standalone   # standalone ビルド（動作確認用）
  python build.py onefile      # onefile ビルド（配布用）
  python build.py check        # ビルド環境チェックのみ
  python build.py clean        # ビルド成果物を削除

出典:
  - ビルドコマンド: cognix_nuitka_build_steps.md（ID3で検証済み）
  - Nuitka公式: https://nuitka.net/user-documentation/user-manual.html
"""

import subprocess
import sys
import os
import shutil
import argparse
from pathlib import Path


# ============================================================
# ビルド設定（cognix_nuitka_build_steps.md から転記）
# ============================================================

PRODUCT_NAME = "Cognix"
PRODUCT_VERSION = "0.2.0"
COMPANY_NAME = "Cognix"
COPYRIGHT = "Copyright (c) 2025-2026 Cognix"
FILE_DESCRIPTION = "Cognix - AI-Powered CLI Development Assistant"
ENTRY_POINT = "cognix/main.py"
OUTPUT_FILENAME = "cognix.exe"
ICON_FILE = "Cognix_logo.jpg"  # Note: --windows-icon-from-ico requires .ico or .png; .jpg is skipped
ONEFILE_TEMPDIR = "{CACHE_DIR}/Cognix/{VERSION}"

# Nuitka 共通オプション
COMMON_OPTIONS = [
    "--msvc=latest",
    "--include-package=cognix",
    "--include-data-dir=cognix/data=cognix/data",
    "--include-package=openai",
    "--include-package=anthropic",
    "--nofollow-import-to=pytest",
    "--nofollow-import-to=ruff",
    f"--output-filename={OUTPUT_FILENAME}",
    "--windows-console-mode=force",
]

# onefile 追加オプション
ONEFILE_OPTIONS = [
    f"--onefile-tempdir-spec={ONEFILE_TEMPDIR}",
    f"--company-name={COMPANY_NAME}",
    f"--product-name={PRODUCT_NAME}",
    f"--product-version={PRODUCT_VERSION}",
    f"--file-description={FILE_DESCRIPTION}",
    f"--copyright={COPYRIGHT}",
]

# ビルド成果物ディレクトリ
STANDALONE_DIR = "main.dist"
STANDALONE_BUILD = "main.build"
ONEFILE_BUILD = "main.onefile-build"


# ============================================================
# 環境チェック
# ============================================================

def check_python_version():
    """Python 3.13+ の確認"""
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 13):
        print(f"[ERROR] Python 3.13+ が必要です (現在: {v.major}.{v.minor}.{v.micro})")
        return False
    print(f"[OK] Python {v.major}.{v.minor}.{v.micro}")
    return True


def check_nuitka():
    """Nuitka のインストール確認"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            capture_output=True, text=True, timeout=30
        )
        version_line = result.stdout.strip().split("\n")[0] if result.stdout else ""
        print(f"[OK] Nuitka: {version_line}")
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("[ERROR] Nuitka が見つかりません: pip install nuitka")
        return False


def check_entry_point():
    """エントリーポイントの存在確認"""
    if Path(ENTRY_POINT).exists():
        print(f"[OK] エントリーポイント: {ENTRY_POINT}")
        return True
    else:
        print(f"[ERROR] エントリーポイントが見つかりません: {ENTRY_POINT}")
        return False


def check_data_dir():
    """data ディレクトリの存在確認"""
    data_path = Path("cognix/data")
    if data_path.exists() and data_path.is_dir():
        print(f"[OK] データディレクトリ: cognix/data")
        return True
    else:
        print(f"[ERROR] データディレクトリが見つかりません: cognix/data")
        return False


def check_icon():
    """アイコンファイルの存在確認（onefile用、任意）"""
    if Path(ICON_FILE).exists():
        print(f"[OK] アイコン: {ICON_FILE}")
        return True
    else:
        print(f"[WARN] アイコンが見つかりません: {ICON_FILE}（onefile時はスキップ）")
        return False


def check_cognix_package():
    """cognix パッケージの import 確認"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import cognix; print(cognix.__version__)"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            ver = result.stdout.strip()
            print(f"[OK] cognix パッケージ: v{ver}")
            return True
        else:
            print(f"[ERROR] cognix パッケージの import に失敗: {result.stderr.strip()}")
            print("       pip install -e . を実行してください")
            return False
    except subprocess.TimeoutExpired:
        print("[ERROR] cognix パッケージの確認がタイムアウト")
        return False


def run_checks():
    """全ての環境チェックを実行"""
    print("=" * 60)
    print(f"  {PRODUCT_NAME} v{PRODUCT_VERSION} ビルド環境チェック")
    print("=" * 60)
    print()

    results = [
        check_python_version(),
        check_nuitka(),
        check_entry_point(),
        check_data_dir(),
        check_icon(),
        check_cognix_package(),
    ]

    print()
    ok_count = sum(1 for r in results if r)
    total = len(results)
    print(f"結果: {ok_count}/{total} チェック通過")

    # WARN（アイコン）は失敗扱いにしない
    critical_results = results[:4] + results[5:]  # アイコンを除く
    return all(critical_results)


# ============================================================
# ビルド実行
# ============================================================

def build_standalone():
    """standalone モードでビルド（動作確認用）"""
    print()
    print("=" * 60)
    print(f"  {PRODUCT_NAME} v{PRODUCT_VERSION} - Standalone Build")
    print("=" * 60)
    print()

    cmd = [
        sys.executable, "-m", "nuitka",
        "--mode=standalone",
    ] + COMMON_OPTIONS + [ENTRY_POINT]

    print("実行コマンド:")
    print(f"  {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print()
        print("[SUCCESS] Standalone ビルド完了")
        print(f"  出力: {STANDALONE_DIR}/{OUTPUT_FILENAME}")
        print()
        print("動作確認:")
        print(f"  cd {STANDALONE_DIR}")
        print(f"  .\\{OUTPUT_FILENAME} --version")
        print(f"  .\\{OUTPUT_FILENAME} --help")
    else:
        print()
        print(f"[FAILED] ビルド失敗 (exit code: {result.returncode})")
        sys.exit(1)


def build_onefile():
    """onefile モードでビルド（配布用）"""
    print()
    print("=" * 60)
    print(f"  {PRODUCT_NAME} v{PRODUCT_VERSION} - Onefile Build")
    print("=" * 60)
    print()

    cmd = [
        sys.executable, "-m", "nuitka",
        "--mode=onefile",
    ] + COMMON_OPTIONS

    # アイコンが存在する場合のみ追加
    if Path(ICON_FILE).exists():
        cmd.append(f"--windows-icon-from-ico={ICON_FILE}")

    cmd += ONEFILE_OPTIONS + [ENTRY_POINT]

    print("実行コマンド:")
    print(f"  {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd)

    if result.returncode == 0:
        # 出力ファイルのサイズを表示
        output_path = Path(OUTPUT_FILENAME)
        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print()
            print("[SUCCESS] Onefile ビルド完了")
            print(f"  出力: {OUTPUT_FILENAME}")
            print(f"  サイズ: {size_mb:.1f} MB")
            print()
            print("動作確認:")
            print(f"  .\\{OUTPUT_FILENAME} --version")
            print(f"  .\\{OUTPUT_FILENAME} --help")
        else:
            print()
            print("[SUCCESS] ビルド完了（出力ファイルの場所を確認してください）")
    else:
        print()
        print(f"[FAILED] ビルド失敗 (exit code: {result.returncode})")
        sys.exit(1)


def clean():
    """ビルド成果物を削除"""
    print()
    print("=" * 60)
    print(f"  {PRODUCT_NAME} - ビルド成果物クリーン")
    print("=" * 60)
    print()

    targets = [
        STANDALONE_DIR,
        STANDALONE_BUILD,
        ONEFILE_BUILD,
    ]

    # 単一ファイル出力
    output_file = Path(OUTPUT_FILENAME)
    if output_file.exists():
        print(f"  削除: {OUTPUT_FILENAME}")
        output_file.unlink()

    for target in targets:
        target_path = Path(target)
        if target_path.exists():
            print(f"  削除: {target}/")
            shutil.rmtree(target_path)

    print()
    print("[DONE] クリーン完了")


# ============================================================
# メイン
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description=f"{PRODUCT_NAME} v{PRODUCT_VERSION} Nuitka Build Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python build.py check       環境チェックのみ
  python build.py standalone  standalone ビルド（動作確認用）
  python build.py onefile     onefile ビルド（配布用）
  python build.py clean       ビルド成果物を削除

推奨手順:
  1. python build.py check      → 環境確認
  2. python build.py standalone → 動作確認
  3. python build.py onefile    → 配布用バイナリ生成
        """
    )

    parser.add_argument(
        "mode",
        choices=["standalone", "onefile", "check", "clean"],
        help="ビルドモード"
    )

    args = parser.parse_args()

    if args.mode == "clean":
        clean()
        return

    # check / standalone / onefile は全て環境チェックから開始
    if not run_checks():
        print()
        print("[ABORT] 環境チェックに失敗しました。上記のエラーを修正してください。")
        sys.exit(1)

    if args.mode == "check":
        print()
        print("[OK] ビルド環境は正常です。")
        return

    if args.mode == "standalone":
        build_standalone()

    elif args.mode == "onefile":
        build_onefile()


if __name__ == "__main__":
    main()
