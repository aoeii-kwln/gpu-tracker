# GPU Price Tracker — セットアップガイド

毎日自動でGPU価格を6つの販売店から収集し、価格変動・新着モデルをメール通知するツールです。

---

## 📁 ファイル構成

```
gpu-tracker/
├── scraper.py          # 爬蟲メインスクリプト
├── dashboard.html      # 価格推移グラフ表示ページ
├── requirements.txt    # 必要Pythonパッケージ
├── setup_scheduler.bat # Windowsタスクスケジューラ登録
├── data/
│   └── prices.json     # 蓄積された価格データ（自動生成）
└── logs/
    └── scraper.log     # ログファイル（自動生成）
```

---

## 🚀 セットアップ手順

### Step 1 — Python のインストール

1. https://www.python.org/downloads/ を開く
2. 最新の Python 3.x をダウンロード・インストール
3. **インストール時に必ず「Add Python to PATH」にチェックを入れる**

### Step 2 — Gmail アプリパスワードの設定（メール通知用）

1. https://myaccount.google.com/security を開く
2. 「2段階認証プロセス」を有効にする（まだの場合）
3. https://myaccount.google.com/apppasswords を開く
4. アプリ名「GPU Tracker」で生成 → 16桁のパスワードをコピー
5. `scraper.py` を開き、以下の行を編集：

```python
EMAIL_APP_PASSWORD = "ここに16桁のパスワードを貼り付け"
```

> ⚠️ メール通知が不要な場合はそのままでOKです（通知をスキップします）

### Step 3 — 自動スケジュール設定

`setup_scheduler.bat` を **右クリック → 管理者として実行**

- 必要パッケージが自動インストールされます
- 毎朝 **08:30** に自動実行するタスクが登録されます
- 初回実行するか確認されます → Y を入力して即実行もできます

### Step 4 — ダッシュボードを開く

`dashboard.html` をブラウザで開くだけです。
（Chrome / Edge 推奨）

---

## ⚙️ カスタマイズ

### 実行時刻を変更する

`setup_scheduler.bat` 内の `/ST 08:30` を好みの時刻に変更してから再実行してください。

### 価格変動の通知閾値を変更する

`scraper.py` の以下の行を変更（デフォルト: 3%）：

```python
PRICE_CHANGE_THRESHOLD = 0.03   # 0.05 にすると 5% 変動から通知
```

### 追跡するGPUを追加・削除する

`scraper.py` の `GPU_MODELS` 辞書を編集してください：

```python
GPU_MODELS = {
    "RTX 5090": {"keywords": ["RTX 5090"], "series": "RTX50", "vendor": "NVIDIA"},
    # ここに追加...
}
```

---

## 📊 機能一覧

| 機能 | 説明 |
|------|------|
| 価格推移グラフ | 各GPUの日次最安値を折線グラフで表示 |
| 販売店別価格 | kakaku / ドスパラ / ツクモ / ユニットコム / Joshin / Amazon |
| 価格変動Pick Up | 前日比 ±3% 以上の変動を赤・緑でハイライト |
| 新着モデルPick Up | 初めて検出されたGPUを自動マーク |
| メール通知 | 変動検出時に weilahm@gmail.com へ自動送信 |
| シリーズフィルター | RTX50 / RTX30 / AMD RX9000 で絞り込み表示 |

---

## ❓ トラブルシューティング

**ダッシュボードにデータが表示されない**
→ `scraper.py` を先に実行して `data/prices.json` を生成してください

**スクレイピングがほぼ全部失敗する**
→ 各サイトの HTML 構造が変わっている可能性があります。`logs/scraper.log` を確認して Claudeに共有してください

**メールが届かない**
→ Gmail のアプリパスワードを確認してください（通常のパスワードではなく、アプリパスワードが必要です）
