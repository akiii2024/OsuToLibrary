#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OsuToLibrary GUI起動スクリプト

このスクリプトはGUIアプリケーションを起動します。
"""

import sys
import os
from pathlib import Path

# 現在のディレクトリをPythonパスに追加
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from OsuToLibraryGUI import main
    
    if __name__ == "__main__":
        print("OsuToLibrary GUIを起動しています...")
        main()
        
except ImportError as e:
    print(f"エラー: 必要なモジュールが見つかりません: {e}")
    print("pip install -r requirements.txt を実行して依存関係をインストールしてください")
    sys.exit(1)
except Exception as e:
    print(f"エラー: アプリケーションの起動に失敗しました: {e}")
    sys.exit(1)
