# cognix.ui_zen_integration
from __future__ import annotations
import os, time, sys
from cognix.theme_zen import rule, color, ACCENT, GREEN, GREEN_BRIGHT, ORANGE, is_tty

def render_logo_once_if_needed(version: str, app_name: str = "C O G N I X") -> None:
    """ボックスアニメーションを表示（毎回）"""
    if not is_tty():
        return
    
    # COGNIX_SKIP_LOGO_ANIM=1 で完全スキップ
    if os.getenv("COGNIX_SKIP_LOGO_ANIM") in ("1","true","True"):
        print(f"{app_name}   —  ver.{version}")
        print(rule())
        return

    # ✅ ボックスアニメーション実装
    letters = ["C", "O", "G", "N", "I", "X"]
    GRAY = "\033[90m"  # 暗いグレー
    BRIGHT_WHITE = "\033[97m"
    RESET = "\033[0m"
    
    # フレーム1-7: 各文字が順番に表示される（グレー）
    for i in range(len(letters) + 1):
        if i == 0:
            # 空のボックス6個
            top = "┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐"
            middle = "│   ││   ││   ││   ││   ││   │"
            bottom = "└───┘└───┘└───┘└───┘└───┘└───┘"
        else:
            # i個の文字入りボックス + (6-i)個の空ボックス
            boxes = []
            for j in range(6):
                if j < i:
                    boxes.append(f"│ {letters[j]} │")
                else:
                    boxes.append("│   │")
            
            top = "┌───┐" * 6
            middle = "".join(boxes)
            bottom = "└───┘" * 6
        
        # 3行上書き表示（カーソル移動）
        if i > 0:
            sys.stdout.write("\033[3A")  # 3行上に移動
        sys.stdout.write("\r\033[2K" + GRAY + top + RESET + "\n")
        sys.stdout.write("\r\033[2K" + GRAY + middle + RESET + "\n")
        sys.stdout.write("\r\033[2K" + GRAY + bottom + RESET + "\n")
        sys.stdout.flush()
        time.sleep(0.12)
    
    # フレーム8: ピカッと発光（明るい白）✨
    sys.stdout.write("\033[3A")  # 3行上に移動
    top_bright = BRIGHT_WHITE + "┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐" + RESET
    middle_bright = BRIGHT_WHITE + "│ C ││ O ││ G ││ N ││ I ││ X │" + RESET
    bottom_bright = BRIGHT_WHITE + "└───┘└───┘└───┘└───┘└───┘└───┘" + RESET
    
    sys.stdout.write("\r\033[2K" + top_bright + "\n")
    sys.stdout.write("\r\033[2K" + middle_bright + "\n")
    sys.stdout.write("\r\033[2K" + bottom_bright + "\n")
    sys.stdout.flush()
    time.sleep(0.15)
    
    # フレーム9: グレーに戻る
    sys.stdout.write("\033[3A")
    sys.stdout.write("\r\033[2K" + GRAY + "┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐" + RESET + "\n")
    sys.stdout.write("\r\033[2K" + GRAY + "│ C ││ O ││ G ││ N ││ I ││ X │" + RESET + "\n")
    sys.stdout.write("\r\033[2K" + GRAY + "└───┘└───┘└───┘└───┘└───┘└───┘" + RESET + "\n")
    sys.stdout.flush()
    time.sleep(0.12)
    
    # フレーム10: 最終表示（Cognixグリーン + バージョンは下に）
    sys.stdout.write("\033[3A")  # 3行上に移動
    top_final = color("┌───┐┌───┐┌───┐┌───┐┌───┐┌───┐", GREEN)
    middle_final = color("│ C ││ O ││ G ││ N ││ I ││ X │", GREEN)
    bottom_final = color("└───┘└───┘└───┘└───┘└───┘└───┘", GREEN)
    
    sys.stdout.write("\r\033[2K" + top_final + "\n")
    sys.stdout.write("\r\033[2K" + middle_final + "\n")
    sys.stdout.write("\r\033[2K" + bottom_final + "\n")
    sys.stdout.flush()
    
    # バージョン＋クレジット表示（ボックスの下に）- グレー、左寄せ
    GRAY = "\033[90m"
    RESET = "\033[0m"
    print(f"{GRAY}Version {version} Deus Ex Machina Made by Indie Maker{RESET}")

    print(rule())