# OsuToLibrary

osuファイルから音楽情報を抽出し、Spotifyライブラリに楽曲を追加するPythonツールです。

## 機能

- osuファイル（.osu）から楽曲情報（タイトル、アーティスト）を自動抽出
- Spotifyで楽曲を検索
- 自動的にプレイリストを作成・管理
- **重複チェック機能**（同じ楽曲を何度も追加しない）
- 単一ファイルまたはディレクトリ全体の一括処理
- **GUIアプリケーション**（使いやすいグラフィカルインターフェース）
- コマンドラインインターフェース

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. Spotify Developer Appの作成

1. [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) にアクセス
2. 新しいアプリを作成
3. Client IDとClient Secretを取得
4. リダイレクトURIに `http://127.0.0.1:8888/callback` を追加

### 3. 設定ファイルの設定

`config.json` ファイルを編集して、取得した認証情報を設定：

```json
{
  "spotify_client_id": "あなたのClient ID",
  "spotify_client_secret": "あなたのClient Secret"
}
```

## 使用方法

### GUIアプリケーション（推奨）

```bash
# GUIアプリケーションを起動
python run_gui.py
```

GUIアプリケーションでは以下の操作が可能です：
- 直感的なファイル・ディレクトリ選択
- **osuのSongsフォルダの自動検出・設定**
- リアルタイムの処理進捗表示
- 詳細なログ表示（重複チェック結果を含む）
- 設定の保存・読み込み
- 重複楽曲の自動スキップ

### コマンドライン使用

```bash
# 単一のosuファイルを処理
python OsuToLibrary.py "path/to/beatmap.osu"

# ディレクトリ内のすべてのosuファイルを処理
python OsuToLibrary.py "path/to/beatmaps/"

# 特定のプレイリスト名を指定
python OsuToLibrary.py "path/to/beatmaps/" --playlist "My Osu Songs"
```

### コマンドライン引数

- `path`: osuファイルまたはディレクトリのパス
- `--playlist`, `-p`: プレイリスト名（オプション）
- `--config`, `-c`: 設定ファイルのパス（デフォルト: config.json）
- `--create-config`: サンプル設定ファイルを作成

### サンプル設定ファイルの作成

```bash
python OsuToLibrary.py --create-config
```

## 例

### GUIアプリケーション使用例

1. `python run_gui.py` でGUIを起動
2. Spotify設定でClient IDとClient Secretを入力
3. 「設定保存」をクリック
4. 「ディレクトリ選択」を選択（osuのSongsフォルダが自動設定されます）
5. 必要に応じてディレクトリを変更
6. プレイリスト名を設定（オプション）
7. 「処理開始」をクリック

**便利な機能**:
- アプリケーション起動時にosuのSongsフォルダを自動検出
- ファイル・ディレクトリ選択ダイアログでもosuフォルダがデフォルトに設定
- **レジストリ検索**: Windowsレジストリからosuの正確なインストールパスを検出
- **階層検索**: 固定パスで見つからない場合、最大3階層まで再帰的に検索
- **再帰的ファイル検索**: 楽曲フォルダ内の.osuファイルも自動検出
- **多様なパス対応**: AppData、Program Files、Documents、カスタムドライブ等
- **ユーザー名非依存**: どのPCでも動作する汎用的な検索機能

### コマンドライン使用例

#### 例1: 単一ファイルの処理

```bash
python OsuToLibrary.py "10427 Ke$ha - TiK ToK [no video]/Ke$ha - TiK ToK (EEeee) [Normal].osu"
```

#### 例2: ディレクトリ全体の処理

```bash
python OsuToLibrary.py "10427 Ke$ha - TiK ToK [no video]/" --playlist "Ke$ha - TiK ToK"
```

## 出力例

```
処理中: Ke$ha - TiK ToK (EEeee) [Normal].osu
楽曲情報: TiK ToK - Ke$ha
検索中: track:TiK ToK artist:Ke$ha
見つかりました: TiK ToK - Kesha
既存のプレイリストを使用: osu! 楽曲ライブラリ
楽曲をプレイリストに追加しました

=== 処理結果 ===
新規追加された楽曲数: 1
重複でスキップされた楽曲数: 0
その他の理由でスキップされた楽曲数: 0

新規追加された楽曲:
  ✓ TiK ToK - Kesha
    Spotify: https://open.spotify.com/track/0H8iQ4...
```

### 重複チェック機能

同じ楽曲が既にプレイリストに存在する場合、自動的にスキップされます：

```
処理中: Ke$ha - TiK ToK (EEeee) [Hard].osu
楽曲情報: TiK ToK - Ke$ha
検索中: track:TiK ToK artist:Ke$ha
見つかりました: TiK ToK - Kesha
楽曲は既にプレイリストに存在します

=== 処理結果 ===
新規追加された楽曲数: 0
重複でスキップされた楽曲数: 1
その他の理由でスキップされた楽曲数: 0

重複でスキップされた楽曲:
  ⚠ TiK ToK - Kesha (既に存在)
```

## 注意事項

- 初回実行時、ブラウザが開いてSpotifyの認証が求められます
- 楽曲が見つからない場合は、タイトルやアーティスト名の表記の違いが原因の可能性があります
- 大量のファイルを処理する場合は、Spotify APIのレート制限に注意してください

## トラブルシューティング

### 認証エラー

- Client IDとClient Secretが正しく設定されているか確認
- リダイレクトURIが `http://localhost:8888/callback` に設定されているか確認

### 楽曲が見つからない

- osuファイルのメタデータが正しく設定されているか確認
- 手動でSpotifyで楽曲を検索して、表記の違いを確認

### プレイリストが作成されない

- Spotifyアカウントの権限を確認
- ネットワーク接続を確認
