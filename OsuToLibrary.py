#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OsuToLibrary - osuファイルから音楽情報を抽出し、Spotifyライブラリに追加するツール

このスクリプトはosuファイルを読み取り、楽曲情報を抽出してSpotifyで検索し、
プレイリストに追加する機能を提供します。
"""

import os
import re
import json
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Dict, List, Optional, Tuple
import argparse
import sys
from pathlib import Path


class OsuFileParser:
    """osuファイルを解析するクラス"""
    
    def __init__(self):
        self.metadata = {}
    
    def parse_osu_file(self, file_path: str) -> Dict[str, str]:
        """
        osuファイルを解析して楽曲情報を抽出する
        
        Args:
            file_path: osuファイルのパス
            
        Returns:
            楽曲情報の辞書
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Metadataセクションを抽出
            metadata_match = re.search(r'\[Metadata\](.*?)(?=\n\[|\n$)', content, re.DOTALL)
            if metadata_match:
                metadata_text = metadata_match.group(1)
                
                # 各フィールドを抽出
                title_match = re.search(r'Title:(.*)', metadata_text)
                artist_match = re.search(r'Artist:(.*)', metadata_text)
                version_match = re.search(r'Version:(.*)', metadata_text)
                creator_match = re.search(r'Creator:(.*)', metadata_text)
                
                # GeneralセクションからAudioFilenameを抽出
                general_match = re.search(r'\[General\](.*?)(?=\n\[|\n$)', content, re.DOTALL)
                audio_filename = ""
                if general_match:
                    audio_match = re.search(r'AudioFilename:(.*)', general_match.group(1))
                    if audio_match:
                        audio_filename = audio_match.group(1).strip()
                
                self.metadata = {
                    'title': title_match.group(1).strip() if title_match else "",
                    'artist': artist_match.group(1).strip() if artist_match else "",
                    'version': version_match.group(1).strip() if version_match else "",
                    'creator': creator_match.group(1).strip() if creator_match else "",
                    'audio_filename': audio_filename
                }
                
                return self.metadata
            else:
                print(f"警告: {file_path} からMetadataセクションが見つかりませんでした")
                return {}
                
        except Exception as e:
            print(f"エラー: {file_path} の解析中にエラーが発生しました: {e}")
            return {}


class SpotifyManager:
    """Spotify APIを管理するクラス"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "http://127.0.0.1:8888/callback"):
        """
        SpotifyManagerの初期化
        
        Args:
            client_id: SpotifyアプリのClient ID
            client_secret: SpotifyアプリのClient Secret
            redirect_uri: リダイレクトURI
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        
        # Spotify認証の設定
        scope = "playlist-modify-public playlist-modify-private user-library-modify playlist-read-private"
        
        self.sp_oauth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            cache_path=".spotify_cache"
        )
        
        # 認証トークンを取得
        token_info = self.sp_oauth.get_cached_token()
        if not token_info:
            token_info = self.sp_oauth.get_access_token()
        
        self.sp = spotipy.Spotify(auth=token_info['access_token'])
    
    def search_track(self, title: str, artist: str) -> Optional[Dict]:
        """
        Spotifyで楽曲を検索する
        
        Args:
            title: 楽曲タイトル
            artist: アーティスト名
            
        Returns:
            見つかった楽曲の情報、見つからない場合はNone
        """
        try:
            # 検索クエリを作成
            query = f"track:{title} artist:{artist}"
            
            print(f"検索中: {query}")
            
            # Spotifyで検索
            results = self.sp.search(q=query, type='track', limit=10)
            
            if results['tracks']['items']:
                # 最初の結果を返す
                track = results['tracks']['items'][0]
                print(f"見つかりました: {track['name']} - {track['artists'][0]['name']}")
                return track
            else:
                print(f"楽曲が見つかりませんでした: {title} - {artist}")
                return None
                
        except Exception as e:
            print(f"検索エラー: {e}")
            return None
    
    def create_playlist(self, name: str, description: str = "") -> Optional[str]:
        """
        新しいプレイリストを作成する
        
        Args:
            name: プレイリスト名
            description: プレイリストの説明
            
        Returns:
            作成されたプレイリストのID、失敗した場合はNone
        """
        try:
            user_id = self.sp.current_user()['id']
            playlist = self.sp.user_playlist_create(
                user=user_id,
                name=name,
                public=True,
                description=description
            )
            
            print(f"プレイリストを作成しました: {name}")
            return playlist['id']
            
        except Exception as e:
            print(f"プレイリスト作成エラー: {e}")
            return None
    
    def get_playlist_tracks(self, playlist_id: str) -> List[str]:
        """
        プレイリスト内の楽曲IDリストを取得する
        
        Args:
            playlist_id: プレイリストID
            
        Returns:
            楽曲IDのリスト
        """
        try:
            tracks = []
            results = self.sp.playlist_tracks(playlist_id)
            
            while results:
                for item in results['items']:
                    if item['track'] and item['track']['id']:
                        tracks.append(item['track']['id'])
                
                if results['next']:
                    results = self.sp.next(results)
                else:
                    break
            
            return tracks
            
        except Exception as e:
            print(f"プレイリスト取得エラー: {e}")
            return []
    
    def is_track_in_playlist(self, playlist_id: str, track_id: str) -> bool:
        """
        楽曲がプレイリストに既に存在するかチェックする
        
        Args:
            playlist_id: プレイリストID
            track_id: 楽曲ID
            
        Returns:
            存在する場合はTrue、存在しない場合はFalse
        """
        try:
            playlist_tracks = self.get_playlist_tracks(playlist_id)
            return track_id in playlist_tracks
            
        except Exception as e:
            print(f"重複チェックエラー: {e}")
            return False
    
    def add_track_to_playlist(self, playlist_id: str, track_id: str, check_duplicate: bool = True) -> Tuple[bool, str]:
        """
        プレイリストに楽曲を追加する
        
        Args:
            playlist_id: プレイリストID
            track_id: 楽曲ID
            check_duplicate: 重複チェックを行うかどうか
            
        Returns:
            (成功フラグ, メッセージ)のタプル
        """
        try:
            # 重複チェック
            if check_duplicate:
                if self.is_track_in_playlist(playlist_id, track_id):
                    return False, "楽曲は既にプレイリストに存在します"
            
            self.sp.playlist_add_items(playlist_id, [track_id])
            return True, "楽曲をプレイリストに追加しました"
            
        except Exception as e:
            return False, f"楽曲追加エラー: {e}"
    
    def get_or_create_osu_playlist(self, playlist_name: str = "osu! 楽曲ライブラリ") -> Optional[str]:
        """
        osu楽曲用のプレイリストを取得または作成する
        
        Args:
            playlist_name: プレイリスト名
            
        Returns:
            プレイリストID
        """
        try:
            # 既存のプレイリストを検索
            playlists = self.sp.current_user_playlists()
            
            for playlist in playlists['items']:
                if playlist['name'] == playlist_name:
                    print(f"既存のプレイリストを使用: {playlist_name}")
                    return playlist['id']
            
            # プレイリストが存在しない場合は作成
            return self.create_playlist(
                playlist_name,
                "osu!ファイルから抽出した楽曲のライブラリ"
            )
            
        except Exception as e:
            print(f"プレイリスト取得エラー: {e}")
            return None


class OsuToLibrary:
    """メインのクラス - osuファイルからSpotifyライブラリへの変換を管理"""
    
    def __init__(self, spotify_client_id: str, spotify_client_secret: str):
        """
        初期化
        
        Args:
            spotify_client_id: Spotify Client ID
            spotify_client_secret: Spotify Client Secret
        """
        self.parser = OsuFileParser()
        self.spotify = SpotifyManager(spotify_client_id, spotify_client_secret)
        self.added_tracks = []
        self.duplicate_tracks = []
        self.skipped_tracks = []
    
    def process_osu_file(self, osu_file_path: str, playlist_id: str = None, check_duplicate: bool = True) -> Tuple[bool, str]:
        """
        単一のosuファイルを処理する
        
        Args:
            osu_file_path: osuファイルのパス
            playlist_id: プレイリストID（指定しない場合は自動で作成）
            check_duplicate: 重複チェックを行うかどうか
            
        Returns:
            (成功フラグ, メッセージ)のタプル
        """
        print(f"\n処理中: {osu_file_path}")
        
        # osuファイルを解析
        metadata = self.parser.parse_osu_file(osu_file_path)
        if not metadata:
            return False, "osuファイルの解析に失敗しました"
        
        print(f"楽曲情報: {metadata['title']} - {metadata['artist']}")
        
        # Spotifyで検索
        track = self.spotify.search_track(metadata['title'], metadata['artist'])
        if not track:
            return False, f"楽曲が見つかりませんでした: {metadata['title']} - {metadata['artist']}"
        
        # プレイリストIDが指定されていない場合は自動で取得/作成
        if not playlist_id:
            playlist_id = self.spotify.get_or_create_osu_playlist()
            if not playlist_id:
                return False, "プレイリストの取得/作成に失敗しました"
        
        # プレイリストに追加
        success, message = self.spotify.add_track_to_playlist(playlist_id, track['id'], check_duplicate)
        
        if success:
            self.added_tracks.append({
                'title': track['name'],
                'artist': track['artists'][0]['name'],
                'spotify_url': track['external_urls']['spotify'],
                'file_path': osu_file_path
            })
        elif "既にプレイリストに存在します" in message:
            self.duplicate_tracks.append({
                'title': track['name'],
                'artist': track['artists'][0]['name'],
                'spotify_url': track['external_urls']['spotify'],
                'file_path': osu_file_path
            })
        else:
            self.skipped_tracks.append({
                'title': track['name'],
                'artist': track['artists'][0]['name'],
                'file_path': osu_file_path,
                'reason': message
            })
        
        return success, message
    
    def process_directory(self, directory_path: str, playlist_name: str = None, check_duplicate: bool = True, recursive: bool = True) -> int:
        """
        ディレクトリ内のすべてのosuファイルを処理する
        
        Args:
            directory_path: ディレクトリパス
            playlist_name: プレイリスト名
            check_duplicate: 重複チェックを行うかどうか
            recursive: サブディレクトリも再帰的に検索するかどうか
            
        Returns:
            新規追加されたファイル数
        """
        directory = Path(directory_path)
        if not directory.exists():
            print(f"エラー: ディレクトリが存在しません: {directory_path}")
            return 0
        
        # .osuファイルを検索（再帰的または非再帰的）
        if recursive:
            osu_files = list(directory.rglob("*.osu"))  # 再帰的検索
            print(f"再帰的に検索中: {directory_path}")
        else:
            osu_files = list(directory.glob("*.osu"))  # 非再帰的検索
            print(f"直接検索中: {directory_path}")
        
        if not osu_files:
            print(f"エラー: {directory_path} に.osuファイルが見つかりません")
            return 0
        
        print(f"{len(osu_files)}個のosuファイルが見つかりました")
        
        # プレイリストを取得/作成
        playlist_id = None
        if playlist_name:
            playlist_id = self.spotify.get_or_create_osu_playlist(playlist_name)
        
        # 各ファイルを処理
        added_count = 0
        for osu_file in osu_files:
            success, message = self.process_osu_file(str(osu_file), playlist_id, check_duplicate)
            if success:
                added_count += 1
            print(f"結果: {message}")
        
        return added_count
    
    def print_summary(self):
        """処理結果のサマリーを表示"""
        print(f"\n=== 処理結果 ===")
        print(f"新規追加された楽曲数: {len(self.added_tracks)}")
        print(f"重複でスキップされた楽曲数: {len(self.duplicate_tracks)}")
        print(f"その他の理由でスキップされた楽曲数: {len(self.skipped_tracks)}")
        
        if self.added_tracks:
            print("\n新規追加された楽曲:")
            for track in self.added_tracks:
                print(f"  ✓ {track['title']} - {track['artist']}")
                print(f"    Spotify: {track['spotify_url']}")
        
        if self.duplicate_tracks:
            print("\n重複でスキップされた楽曲:")
            for track in self.duplicate_tracks:
                print(f"  ⚠ {track['title']} - {track['artist']} (既に存在)")
        
        if self.skipped_tracks:
            print("\nその他の理由でスキップされた楽曲:")
            for track in self.skipped_tracks:
                print(f"  ✗ {track['title']} - {track['artist']}")
                print(f"    理由: {track['reason']}")


def load_config(config_file: str = "config.json") -> Tuple[str, str]:
    """
    設定ファイルからSpotify認証情報を読み込む
    
    Args:
        config_file: 設定ファイルのパス
        
    Returns:
        (client_id, client_secret)のタプル
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        client_id = config.get('spotify_client_id')
        client_secret = config.get('spotify_client_secret')
        
        if not client_id or not client_secret:
            raise ValueError("設定ファイルにclient_idまたはclient_secretが設定されていません")
        
        return client_id, client_secret
        
    except FileNotFoundError:
        print(f"エラー: 設定ファイルが見つかりません: {config_file}")
        print("config.jsonファイルを作成し、Spotify認証情報を設定してください")
        sys.exit(1)
    except Exception as e:
        print(f"設定ファイル読み込みエラー: {e}")
        sys.exit(1)


def create_sample_config():
    """サンプル設定ファイルを作成"""
    sample_config = {
        "spotify_client_id": "YOUR_SPOTIFY_CLIENT_ID",
        "spotify_client_secret": "YOUR_SPOTIFY_CLIENT_SECRET"
    }
    
    with open("config.json", 'w', encoding='utf-8') as f:
        json.dump(sample_config, f, indent=2, ensure_ascii=False)
    
    print("config.jsonファイルを作成しました")
    print("Spotify Developer Dashboard (https://developer.spotify.com/dashboard) でアプリを作成し、")
    print("Client IDとClient Secretをconfig.jsonに設定してください")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="osuファイルからSpotifyライブラリに楽曲を追加")
    parser.add_argument("path", help="osuファイルまたはディレクトリのパス")
    parser.add_argument("--playlist", "-p", help="プレイリスト名")
    parser.add_argument("--config", "-c", default="config.json", help="設定ファイルのパス")
    parser.add_argument("--create-config", action="store_true", help="サンプル設定ファイルを作成")
    
    args = parser.parse_args()
    
    # 設定ファイル作成モード
    if args.create_config:
        create_sample_config()
        return
    
    # 設定ファイルから認証情報を読み込み
    try:
        client_id, client_secret = load_config(args.config)
    except SystemExit:
        return
    
    # OsuToLibraryインスタンスを作成
    try:
        converter = OsuToLibrary(client_id, client_secret)
    except Exception as e:
        print(f"初期化エラー: {e}")
        print("Spotify認証情報を確認してください")
        return
    
    # パスがファイルかディレクトリかを判定
    path = Path(args.path)
    
    if path.is_file() and path.suffix == '.osu':
        # 単一ファイルの処理
        success = converter.process_osu_file(args.path)
        if success:
            print("楽曲を正常に追加しました")
        else:
            print("楽曲の追加に失敗しました")
    
    elif path.is_dir():
        # ディレクトリの処理
        count = converter.process_directory(args.path, args.playlist)
        print(f"\n処理完了: {count}個の楽曲を追加しました")
        converter.print_summary()
    
    else:
        print(f"エラー: 無効なパスです: {args.path}")
        print("osuファイルまたはディレクトリを指定してください")


if __name__ == "__main__":
    main()
