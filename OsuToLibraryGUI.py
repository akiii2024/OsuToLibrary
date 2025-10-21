#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OsuToLibrary GUI - osuファイルからSpotifyライブラリに楽曲を追加するGUIアプリケーション

このスクリプトはtkinterを使用してGUIインターフェースを提供します。
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import json
import os
from pathlib import Path
from OsuToLibrary import OsuToLibrary, OsuFileParser

# Windowsレジストリアクセスのためのインポート
try:
    import winreg
    WINDOWS_REGISTRY_AVAILABLE = True
except ImportError:
    WINDOWS_REGISTRY_AVAILABLE = False


class OsuToLibraryGUI:
    """GUIメインクラス"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("OsuToLibrary - osuファイルからSpotifyライブラリへ")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 設定の読み込み
        self.config = self.load_config()
        
        # OsuToLibraryインスタンス
        self.converter = None
        
        # GUIコンポーネントの作成
        self.create_widgets()
        
        # デフォルトパスの設定
        self.set_default_osu_path()
        
        # 設定の検証
        self.validate_config()
    
    def load_config(self):
        """設定ファイルを読み込む"""
        try:
            with open("config.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"spotify_client_id": "", "spotify_client_secret": ""}
        except Exception as e:
            messagebox.showerror("設定エラー", f"設定ファイルの読み込みに失敗しました: {e}")
            return {"spotify_client_id": "", "spotify_client_secret": ""}
    
    def save_config(self):
        """設定ファイルを保存する"""
        try:
            with open("config.json", 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("保存エラー", f"設定ファイルの保存に失敗しました: {e}")
            return False
    
    def find_osu_from_registry(self):
        """レジストリからosuのインストールパスを検索"""
        if not WINDOWS_REGISTRY_AVAILABLE:
            return None
        
        registry_paths = [
            (winreg.HKEY_CURRENT_USER, r"Software\Classes\osu\shell\open\command"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Classes\osu\shell\open\command"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\osu!"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\osu!"),
        ]
        
        for hkey, subkey in registry_paths:
            try:
                with winreg.OpenKey(hkey, subkey) as key:
                    # インストールパスを取得
                    try:
                        install_path, _ = winreg.QueryValueEx(key, "InstallLocation")
                        if install_path and os.path.exists(install_path):
                            songs_path = os.path.join(install_path, "Songs")
                            if os.path.exists(songs_path):
                                return songs_path
                    except FileNotFoundError:
                        pass
                    
                    # コマンドラインからパスを抽出
                    try:
                        command, _ = winreg.QueryValueEx(key, "")
                        if command and "osu!.exe" in command:
                            # "C:\path\to\osu!.exe" から "C:\path\to\" を抽出
                            exe_path = command.split('"')[1] if '"' in command else command.split()[0]
                            install_dir = os.path.dirname(exe_path)
                            songs_path = os.path.join(install_dir, "Songs")
                            if os.path.exists(songs_path):
                                return songs_path
                    except FileNotFoundError:
                        pass
            except (FileNotFoundError, OSError):
                continue
        
        return None
    
    def find_osu_songs_directory(self):
        """osuのSongsディレクトリを検索"""
        # まずレジストリから検索
        registry_path = self.find_osu_from_registry()
        if registry_path:
            return registry_path
        
        # レジストリで見つからない場合は一般的なパスをチェック
        possible_paths = [
            os.path.expanduser(r"~\AppData\Local\osu!\Songs"),  # 現在のユーザーのAppData
            os.path.expanduser(r"~\Documents\osu!\Songs"),  # Documentsフォルダ
            os.path.expanduser(r"~\AppData\Roaming\osu!\Songs"),  # Roaming AppData
            r"C:\osu!\Songs",  # Cドライブのルート
            r"D:\osu!\Songs",  # Dドライブ
            r"E:\osu!\Songs",  # Eドライブ
            r"F:\osu!\Songs",  # Fドライブ
        ]
        
        # Program Filesもチェック
        program_paths = [
            r"C:\Program Files\osu!\Songs",
            r"C:\Program Files (x86)\osu!\Songs",
            r"D:\Program Files\osu!\Songs",
            r"D:\Program Files (x86)\osu!\Songs",
        ]
        possible_paths.extend(program_paths)
        
        # まず直接のパスをチェック
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 直接見つからない場合は階層検索を実行
        return self.find_osu_songs_recursive()
    
    def find_osu_songs_recursive(self, max_depth=3):
        """osuのSongsディレクトリを階層的に検索"""
        # 検索対象のベースディレクトリ
        base_dirs = [
            os.path.expanduser("~"),  # ユーザーホームディレクトリ
            "C:\\",  # Cドライブルート
            "D:\\",  # Dドライブルート
        ]
        
        # 追加のドライブがあるかチェック
        import string
        for drive_letter in string.ascii_uppercase[2:]:  # C, D以降のドライブ
            drive_path = f"{drive_letter}:\\"
            if os.path.exists(drive_path):
                base_dirs.append(drive_path)
        
        for base_dir in base_dirs:
            if not os.path.exists(base_dir):
                continue
                
            self.log(f"階層検索中: {base_dir} (最大深度: {max_depth})")
            result = self.search_songs_directory_recursive(base_dir, max_depth)
            if result:
                return result
        
        return None
    
    def search_songs_directory_recursive(self, directory, max_depth, current_depth=0):
        """指定ディレクトリからosuのSongsフォルダを再帰的に検索"""
        if current_depth >= max_depth:
            return None
        
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                
                # ディレクトリの場合
                if os.path.isdir(item_path):
                    # "osu!" フォルダが見つかった場合、その中にSongsフォルダがあるかチェック
                    if item.lower() == "osu!":
                        songs_path = os.path.join(item_path, "Songs")
                        if os.path.exists(songs_path):
                            self.log(f"階層検索で発見: {songs_path}")
                            return songs_path
                    
                    # 再帰的に検索（アクセス権限がないディレクトリはスキップ）
                    try:
                        result = self.search_songs_directory_recursive(item_path, max_depth, current_depth + 1)
                        if result:
                            return result
                    except (PermissionError, OSError):
                        continue  # アクセス権限がない場合はスキップ
        
        except (PermissionError, OSError):
            # ディレクトリアクセス権限がない場合はスキップ
            pass
        
        return None
    
    def set_default_osu_path(self):
        """デフォルトのosuパスを設定"""
        # パスが空で、ディレクトリ選択モードの場合のみ設定
        if not self.path_var.get() and self.selection_type.get() == "dir":
            self.log("osuのSongsフォルダを検索中...")
            osu_path = self.find_osu_songs_directory()
            if osu_path:
                self.path_var.set(osu_path)
                self.log(f"✓ osuのSongsフォルダを自動検出しました: {osu_path}")
            else:
                self.log("⚠ osuのSongsフォルダが見つかりませんでした")
                self.log("手動でディレクトリを選択してください")
    
    def validate_config(self):
        """設定の検証"""
        if not self.config.get("spotify_client_id") or not self.config.get("spotify_client_secret"):
            self.show_config_dialog()
    
    def create_widgets(self):
        """GUIコンポーネントを作成"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # グリッドの重み設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # タイトル
        title_label = ttk.Label(main_frame, text="OsuToLibrary", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 設定セクション
        self.create_config_section(main_frame, 1)
        
        # ファイル選択セクション
        self.create_file_selection_section(main_frame, 2)
        
        # プレイリスト設定セクション
        self.create_playlist_section(main_frame, 3)
        
        # 実行ボタン
        self.create_action_section(main_frame, 4)
        
        # 進捗表示セクション
        self.create_progress_section(main_frame, 5)
        
        # ログ表示セクション
        self.create_log_section(main_frame, 6)
    
    def create_config_section(self, parent, row):
        """設定セクションを作成"""
        # 設定フレーム
        config_frame = ttk.LabelFrame(parent, text="Spotify設定", padding="5")
        config_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        # Client ID
        ttk.Label(config_frame, text="Client ID:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.client_id_var = tk.StringVar(value=self.config.get("spotify_client_id", ""))
        client_id_entry = ttk.Entry(config_frame, textvariable=self.client_id_var, width=50)
        client_id_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        # Client Secret
        ttk.Label(config_frame, text="Client Secret:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.client_secret_var = tk.StringVar(value=self.config.get("spotify_client_secret", ""))
        client_secret_entry = ttk.Entry(config_frame, textvariable=self.client_secret_var, width=50, show="*")
        client_secret_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=(5, 0))
        
        # 設定保存ボタン
        save_config_btn = ttk.Button(config_frame, text="設定保存", command=self.save_configuration)
        save_config_btn.grid(row=0, column=2, rowspan=2, padx=(5, 0))
    
    def create_file_selection_section(self, parent, row):
        """ファイル選択セクションを作成"""
        # ファイル選択フレーム
        file_frame = ttk.LabelFrame(parent, text="ファイル選択", padding="5")
        file_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        # 選択タイプ
        self.selection_type = tk.StringVar(value="file")
        file_radio = ttk.Radiobutton(file_frame, text="単一ファイル", variable=self.selection_type, value="file", command=self.on_selection_type_change)
        file_radio.grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        
        dir_radio = ttk.Radiobutton(file_frame, text="ディレクトリ", variable=self.selection_type, value="dir", command=self.on_selection_type_change)
        dir_radio.grid(row=0, column=1, sticky=tk.W)
        
        # パス表示
        self.path_var = tk.StringVar()
        path_entry = ttk.Entry(file_frame, textvariable=self.path_var, state="readonly", width=60)
        path_entry.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # 選択ボタン
        self.select_btn = ttk.Button(file_frame, text="ファイル選択", command=self.select_file_or_directory)
        self.select_btn.grid(row=1, column=2, padx=(5, 0), pady=(5, 0))
    
    def create_playlist_section(self, parent, row):
        """プレイリスト設定セクションを作成"""
        # プレイリストフレーム
        playlist_frame = ttk.LabelFrame(parent, text="プレイリスト設定", padding="5")
        playlist_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        playlist_frame.columnconfigure(1, weight=1)
        
        # プレイリスト名
        ttk.Label(playlist_frame, text="プレイリスト名:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.playlist_name_var = tk.StringVar(value="osu! 楽曲ライブラリ")
        playlist_entry = ttk.Entry(playlist_frame, textvariable=self.playlist_name_var, width=50)
        playlist_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # 再帰的検索オプション
        self.recursive_search_var = tk.BooleanVar(value=True)
        recursive_check = ttk.Checkbutton(
            playlist_frame, 
            text="サブフォルダも検索する（楽曲フォルダ内の.osuファイルを含む）", 
            variable=self.recursive_search_var
        )
        recursive_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
    
    def create_action_section(self, parent, row):
        """実行ボタンセクションを作成"""
        # 実行フレーム
        action_frame = ttk.Frame(parent)
        action_frame.grid(row=row, column=0, columnspan=3, pady=(0, 10))
        
        # 実行ボタン
        self.run_btn = ttk.Button(action_frame, text="処理開始", command=self.start_processing, style="Accent.TButton")
        self.run_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 停止ボタン
        self.stop_btn = ttk.Button(action_frame, text="停止", command=self.stop_processing, state="disabled")
        self.stop_btn.pack(side=tk.LEFT)
    
    def create_progress_section(self, parent, row):
        """進捗表示セクションを作成"""
        # 進捗フレーム
        progress_frame = ttk.LabelFrame(parent, text="処理進捗", padding="5")
        progress_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        # 進捗バー
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # ステータスラベル
        self.status_var = tk.StringVar(value="待機中...")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        status_label.grid(row=1, column=0, sticky=tk.W)
    
    def create_log_section(self, parent, row):
        """ログ表示セクションを作成"""
        # ログフレーム
        log_frame = ttk.LabelFrame(parent, text="処理ログ", padding="5")
        log_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        parent.rowconfigure(row, weight=1)
        
        # ログテキスト
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def on_selection_type_change(self):
        """選択タイプが変更された時の処理"""
        if self.selection_type.get() == "file":
            self.select_btn.config(text="ファイル選択")
            # ファイル選択モードではパスをクリア
            self.path_var.set("")
        else:
            self.select_btn.config(text="ディレクトリ選択")
            # ディレクトリ選択モードではデフォルトパスを設定
            self.set_default_osu_path()
    
    def select_file_or_directory(self):
        """ファイルまたはディレクトリを選択"""
        if self.selection_type.get() == "file":
            # ファイル選択でもosuのSongsフォルダをデフォルトに設定
            default_dir = self.find_osu_songs_directory()
            file_path = filedialog.askopenfilename(
                title="osuファイルを選択",
                filetypes=[("osu files", "*.osu"), ("All files", "*.*")],
                initialdir=default_dir if default_dir else None
            )
        else:
            # osuのSongsフォルダをデフォルトとして設定
            default_dir = self.find_osu_songs_directory()
            file_path = filedialog.askdirectory(
                title="osuファイルが含まれるディレクトリを選択",
                initialdir=default_dir if default_dir else None
            )
        
        if file_path:
            self.path_var.set(file_path)
            self.log(f"選択されたパス: {file_path}")
    
    def save_configuration(self):
        """設定を保存"""
        self.config["spotify_client_id"] = self.client_id_var.get()
        self.config["spotify_client_secret"] = self.client_secret_var.get()
        
        if self.save_config():
            messagebox.showinfo("設定保存", "設定を保存しました")
            self.log("設定を保存しました")
        else:
            messagebox.showerror("設定保存エラー", "設定の保存に失敗しました")
    
    def show_config_dialog(self):
        """設定ダイアログを表示"""
        messagebox.showwarning(
            "設定が必要です",
            "Spotify APIの認証情報を設定してください。\n"
            "Spotify Developer Dashboardでアプリを作成し、\n"
            "Client IDとClient Secretを取得してください。"
        )
    
    def validate_inputs(self):
        """入力値の検証"""
        if not self.client_id_var.get() or not self.client_secret_var.get():
            messagebox.showerror("設定エラー", "Spotify Client IDとClient Secretを設定してください")
            return False
        
        if not self.path_var.get():
            messagebox.showerror("パスエラー", "ファイルまたはディレクトリを選択してください")
            return False
        
        path = Path(self.path_var.get())
        if not path.exists():
            messagebox.showerror("パスエラー", "選択されたパスが存在しません")
            return False
        
        if self.selection_type.get() == "file" and path.suffix != ".osu":
            messagebox.showerror("ファイルエラー", "osuファイルを選択してください")
            return False
        
        return True
    
    def start_processing(self):
        """処理を開始"""
        if not self.validate_inputs():
            return
        
        # 設定を保存
        self.config["spotify_client_id"] = self.client_id_var.get()
        self.config["spotify_client_secret"] = self.client_secret_var.get()
        self.save_config()
        
        # UI状態を更新
        self.run_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress_var.set(0)
        self.log_text.delete(1.0, tk.END)
        
        # 別スレッドで処理を実行
        self.processing_thread = threading.Thread(target=self.process_files)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def stop_processing(self):
        """処理を停止"""
        self.run_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_var.set("処理が停止されました")
        self.log("処理を停止しました")
    
    def process_files(self):
        """ファイル処理（別スレッドで実行）"""
        try:
            # OsuToLibraryインスタンスを作成
            self.converter = OsuToLibrary(
                self.client_id_var.get(),
                self.client_secret_var.get()
            )
            
            path = Path(self.path_var.get())
            
            if self.selection_type.get() == "file":
                # 単一ファイルの処理
                self.status_var.set("ファイルを処理中...")
                self.log(f"処理開始: {path.name}")
                
                success, message = self.converter.process_osu_file(str(path), check_duplicate=True)
                
                self.progress_var.set(100)
                if success:
                    self.status_var.set("処理完了")
                    self.log("楽曲を正常に追加しました")
                    messagebox.showinfo("完了", "楽曲を正常に追加しました")
                elif "既にプレイリストに存在します" in message:
                    self.status_var.set("処理完了")
                    self.log("楽曲は既にプレイリストに存在します")
                    messagebox.showinfo("完了", "楽曲は既にプレイリストに存在します")
                else:
                    self.status_var.set("処理失敗")
                    self.log(f"楽曲の追加に失敗しました: {message}")
                    messagebox.showerror("エラー", f"楽曲の追加に失敗しました:\n{message}")
            
            else:
                # ディレクトリの処理
                self.status_var.set("ディレクトリを処理中...")
                self.log(f"ディレクトリ処理開始: {path}")
                
                # .osuファイルを検索（再帰的または非再帰的）
                if self.recursive_search_var.get():
                    osu_files = list(path.rglob("*.osu"))  # 再帰的検索
                    self.log(f"再帰的に検索中: {path}")
                else:
                    osu_files = list(path.glob("*.osu"))  # 非再帰的検索
                    self.log(f"直接検索中: {path}")
                
                if not osu_files:
                    self.status_var.set("処理完了")
                    self.log("osuファイルが見つかりませんでした")
                    messagebox.showinfo("完了", "osuファイルが見つかりませんでした")
                    return
                
                self.log(f"{len(osu_files)}個のosuファイルが見つかりました")
                
                # 各ファイルを処理
                processed_count = 0
                for i, osu_file in enumerate(osu_files):
                    self.status_var.set(f"処理中: {osu_file.name} ({i+1}/{len(osu_files)})")
                    self.log(f"処理中: {osu_file.name}")
                    
                    success, message = self.converter.process_osu_file(
                        str(osu_file),
                        self.converter.spotify.get_or_create_osu_playlist(self.playlist_name_var.get()),
                        check_duplicate=True
                    )
                    
                    if success:
                        processed_count += 1
                        self.log(f"✓ {osu_file.name} を正常に追加")
                    elif "既にプレイリストに存在します" in message:
                        self.log(f"⚠ {osu_file.name} は既にプレイリストに存在します（スキップ）")
                    else:
                        self.log(f"✗ {osu_file.name} の追加に失敗: {message}")
                    
                    # 進捗を更新
                    progress = ((i + 1) / len(osu_files)) * 100
                    self.progress_var.set(progress)
                
                self.status_var.set("処理完了")
                self.log(f"\n処理完了: {processed_count}/{len(osu_files)}個の楽曲を新規追加しました")
                
                # 詳細な結果を表示
                self.log(f"\n=== 処理結果詳細 ===")
                self.log(f"新規追加された楽曲数: {len(self.converter.added_tracks)}")
                self.log(f"重複でスキップされた楽曲数: {len(self.converter.duplicate_tracks)}")
                self.log(f"その他の理由でスキップされた楽曲数: {len(self.converter.skipped_tracks)}")
                
                if self.converter.added_tracks:
                    self.log("\n新規追加された楽曲:")
                    for track in self.converter.added_tracks:
                        self.log(f"  ✓ {track['title']} - {track['artist']}")
                        self.log(f"    Spotify: {track['spotify_url']}")
                
                if self.converter.duplicate_tracks:
                    self.log("\n重複でスキップされた楽曲:")
                    for track in self.converter.duplicate_tracks:
                        self.log(f"  ⚠ {track['title']} - {track['artist']} (既に存在)")
                
                if self.converter.skipped_tracks:
                    self.log("\nその他の理由でスキップされた楽曲:")
                    for track in self.converter.skipped_tracks:
                        self.log(f"  ✗ {track['title']} - {track['artist']}")
                        self.log(f"    理由: {track['reason']}")
                
                # 完了メッセージ
                total_processed = len(self.converter.added_tracks) + len(self.converter.duplicate_tracks) + len(self.converter.skipped_tracks)
                messagebox.showinfo(
                    "処理完了", 
                    f"処理完了!\n\n"
                    f"新規追加: {len(self.converter.added_tracks)}曲\n"
                    f"重複スキップ: {len(self.converter.duplicate_tracks)}曲\n"
                    f"その他スキップ: {len(self.converter.skipped_tracks)}曲\n"
                    f"合計処理: {total_processed}曲"
                )
        
        except Exception as e:
            self.status_var.set("エラー発生")
            self.log(f"エラー: {e}")
            messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{e}")
        
        finally:
            # UI状態をリセット
            self.run_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
    
    def log(self, message):
        """ログメッセージを追加"""
        def _log():
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        
        # メインスレッドで実行
        self.root.after(0, _log)


def main():
    """メイン関数"""
    root = tk.Tk()
    
    # スタイルの設定
    style = ttk.Style()
    style.theme_use('clam')  # モダンなテーマを使用
    
    # アプリケーションを開始
    app = OsuToLibraryGUI(root)
    
    # ウィンドウを閉じる際の処理
    def on_closing():
        if messagebox.askokcancel("終了", "アプリケーションを終了しますか？"):
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # GUIを開始
    root.mainloop()


if __name__ == "__main__":
    main()
