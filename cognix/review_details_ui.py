
# cognix.review_details_ui
from __future__ import annotations
from typing import List, Dict, Any

def list_files_block(files_meta: List[Dict[str, Any]]) -> None:
    print("Files changed: " + str(len(files_meta)))
    for i, f in enumerate(files_meta, 1):
        print(f"  {i}) {f['name']}     (+{f.get('added',0)} / -{f.get('removed',0)})")

def show_menu() -> None:
    print("\nSelect file or action:") 
    print("  [1-N] Preview / diff") 
    print("  [l] Lints summary") 
    print("  [s] Suggestions") 
    print("  [a] Apply   [r] Reject   [b] Back") 

def handle_review_details(files_meta, lints_meta, suggestions, preview_cb, diff_cb) -> str:
    """Return one of: 'apply','reject','back'."""
    list_files_block(files_meta)
    while True:
        show_menu()
        sel = input("> ").strip().lower()
        if sel == "a": return "apply"
        if sel == "r": return "reject"
        if sel == "b": return "back"
        if sel == "l":
            items = lints_meta or []
            n = len(items); top = items[:3]
            print("\n── Lints ──")
            for i, it in enumerate(top, 1):
                print(f"  {i}) {it['file']}:{it['line']}  {it['message']}")
            if n > 3:
                print(f"  ... +{n-3} more") 
            continue
        if sel == "s":
            print("\n── Suggestions ──")
            for i, s in enumerate(suggestions or [], 1):
                print(f"{i}) {s}")
            continue
        if sel.isdigit():
            idx = int(sel) - 1
            if 0 <= idx < len(files_meta):
                preview_cb(idx)
                togg = input("(d=diff, b=back) > ").strip().lower()
                if togg == "d":
                    diff_cb(idx)
                continue
        print("(invalid)")
