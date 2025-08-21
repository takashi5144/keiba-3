# 競馬分析ツール

競馬のレースデータを収集・分析し、予想に役立つインサイトを提供するWebアプリケーション。

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Ftakashi5144%2Fkeiba-3&project-name=keiba-frontend&repository-name=keiba-frontend&root-directory=frontend&env=NEXT_PUBLIC_API_URL&envDescription=Backend%20API%20URL&envExample=https%3A%2F%2Fyour-api.com%2Fapi)

## 🎯 主要機能

- **データ収集**: netkeibaから過去10年以上のレースデータを自動収集
- **データ分析**: 馬の成績、コース適性、騎手・調教師の相性を分析
- **予測モデル**: 機械学習による勝率予測と期待値計算
- **可視化**: グラフとチャートによる直感的なデータ表現

## 🛠 技術スタック

### バックエンド
- **FastAPI**: 高速なPython Webフレームワーク
- **PostgreSQL**: メインデータベース
- **Redis**: キャッシュとタスクキュー
- **Celery**: 非同期タスク処理
- **SQLAlchemy**: ORM
- **BeautifulSoup4**: Webスクレイピング

### フロントエンド
- **Next.js 14**: Reactフレームワーク
- **TypeScript**: 型安全な開発
- **Tailwind CSS**: スタイリング
- **Recharts**: グラフ描画

## 📁 プロジェクト構造

```
keiba-analysis/
├── backend/           # FastAPIバックエンド
│   ├── app/          # アプリケーションコード
│   │   ├── api/      # APIエンドポイント
│   │   ├── core/     # 設定・DB接続
│   │   ├── models/   # データベースモデル
│   │   ├── scraper/  # スクレイピング機能
│   │   └── services/ # ビジネスロジック
│   └── tests/        # テストコード
├── frontend/         # Next.jsフロントエンド
├── .kiro/           # 仕様駆動開発ドキュメント
│   ├── steering/    # プロジェクト方向性
│   └── specs/       # 機能仕様
└── docker-compose.yml
```

## 🚀 セットアップ

### 前提条件
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- Poetry (Python パッケージ管理)

### 1. リポジトリのクローン
```bash
git clone https://github.com/your-username/keiba-analysis.git
cd keiba-analysis
```

### 2. 環境変数の設定
```bash
cp backend/.env.example backend/.env
# .envファイルを編集して設定値を調整
```

### 3. Dockerコンテナの起動
```bash
# データベースとRedisを起動
docker-compose up -d postgres redis

# pgAdminを起動（オプション）
docker-compose --profile tools up -d pgadmin
```

### 4. バックエンドのセットアップ
```bash
cd backend

# Poetryで依存関係をインストール
poetry install

# データベースマイグレーション
poetry run alembic upgrade head

# 開発サーバー起動
poetry run uvicorn app.main:app --reload
```

### 5. 動作確認
```bash
# ヘルスチェック
curl http://localhost:8000/api/health
```

## 📊 データ収集

### 手動実行
```bash
# APIエンドポイント経由でスクレイピング開始
curl -X POST http://localhost:8000/api/scraping/start \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "place": "東京"
  }'
```

### スケジュール実行
Celery Beatにより毎日AM2:00に自動実行されます。

```bash
# Celeryワーカーとスケジューラーを起動
docker-compose --profile worker up -d
```

## 🧪 テスト

```bash
cd backend

# ユニットテスト実行
poetry run pytest

# カバレッジレポート生成
poetry run pytest --cov=app --cov-report=html
```

## 📝 開発ガイド

### コード規約
- Python: Black, Ruff
- TypeScript: ESLint, Prettier
- コミット: Conventional Commits

### ブランチ戦略
```
main
├── develop
│   ├── feature/xxx
│   └── bugfix/xxx
└── release/vX.X.X
```

## 🔒 セキュリティ

- APIキー認証
- レート制限
- CORS設定
- 環境変数での秘密情報管理

## 📊 モニタリング

- Prometheus: メトリクス収集
- Flower: Celeryタスク監視 (http://localhost:5555)
- pgAdmin: データベース管理 (http://localhost:5050)

## 🤝 コントリビュート

1. Forkする
2. Feature branchを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'feat: add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

## 📄 ライセンス

個人利用・研究目的のみ。商用利用不可。

## ⚠️ 注意事項

- netkeibaのデータは個人利用の範囲で使用してください
- スクレイピングはサイトに負荷をかけないよう配慮してください
- 実際の馬券購入は自己責任で行ってください