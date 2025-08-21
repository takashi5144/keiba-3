# 競馬予測AIシステム 仕様書

## 1. システム概要

### 1.1 目的
- 競馬レースの予測を行い、100%以上のROIを目指す
- Kelly基準を用いた最適な賭け金配分
- 機械学習による高精度予測

### 1.2 主要機能
- レースデータの自動収集（netkeibaからのスクレイピング）
- XGBoostを用いた勝率予測
- バックテスト機能
- リアルタイム予測
- Webダッシュボード

## 2. システムアーキテクチャ

### 2.1 技術スタック

#### バックエンド
- **言語**: Python 3.11
- **フレームワーク**: FastAPI
- **データベース**: PostgreSQL 15
- **ORM**: SQLAlchemy (Async)
- **タスクキュー**: Celery + Redis
- **機械学習**: XGBoost, scikit-learn
- **スクレイピング**: BeautifulSoup4, httpx

#### フロントエンド
- **フレームワーク**: Next.js 15.5.0
- **言語**: TypeScript
- **スタイリング**: Tailwind CSS
- **状態管理**: React Query (TanStack Query)
- **グラフ**: Recharts
- **アイコン**: Lucide React

#### インフラ
- **コンテナ**: Docker, Docker Compose
- **デプロイ**: Vercel (フロントエンド)
- **CI/CD**: GitHub Actions

### 2.2 ディレクトリ構造

```
keiba-analysis/
├── backend/
│   ├── app/
│   │   ├── api/           # APIエンドポイント
│   │   ├── core/          # 設定、セキュリティ
│   │   ├── models/        # データベースモデル
│   │   ├── schemas/       # Pydanticスキーマ
│   │   ├── scraper/       # スクレイピング処理
│   │   ├── ml/            # 機械学習モデル
│   │   └── tasks/         # Celeryタスク
│   ├── alembic/           # DBマイグレーション
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js App Router
│   │   ├── components/    # Reactコンポーネント
│   │   ├── lib/           # ユーティリティ
│   │   └── types/         # TypeScript型定義
│   ├── package.json
│   └── next.config.js
├── docker-compose.yml
└── vercel.json
```

## 3. データモデル

### 3.1 主要テーブル

#### races（レース情報）
```sql
- id: UUID (Primary Key)
- race_id: String (Unique, netkeiba ID)
- race_date: Date
- place: String (競馬場)
- race_number: Integer
- race_name: String
- grade: String
- race_type: String (芝/ダート)
- distance: Integer
- weather: String
- track_condition: String
- prize_money: JSON
```

#### race_results（レース結果）
```sql
- id: UUID (Primary Key)
- race_id: UUID (Foreign Key)
- post_position: Integer
- horse_number: Integer
- horse_name: String
- horse_id: String
- jockey_name: String
- jockey_id: String
- trainer_name: String
- finish_position: Integer
- finish_time: String
- odds: Float
- popularity: Integer
- weight: Float
- weight_change: Float
```

#### predictions（予測結果）
```sql
- id: UUID (Primary Key)
- race_id: UUID (Foreign Key)
- model_name: String
- horse_id: String
- win_probability: Float
- place_probability: Float
- expected_value: Float
- features: JSON
- created_at: DateTime
```

#### ml_models（機械学習モデル）
```sql
- id: UUID (Primary Key)
- model_name: String
- version: String
- model_type: String
- parameters: JSON
- metrics: JSON
- filename: String
- trained_at: DateTime
```

## 4. API仕様

### 4.1 エンドポイント一覧

#### スクレイピング
- `POST /api/v1/scraping/start` - スクレイピング開始
- `GET /api/v1/scraping/status/{task_id}` - タスク状態確認
- `GET /api/v1/scraping/races` - レース一覧取得

#### 予測
- `POST /api/v1/prediction/predict/race` - 単一レース予測
- `POST /api/v1/prediction/predict/batch` - バッチ予測
- `GET /api/v1/prediction/predict/today` - 本日の予測
- `POST /api/v1/prediction/backtest` - バックテスト実行

#### モデル管理
- `POST /api/v1/training/train` - モデル訓練
- `GET /api/v1/training/status/{task_id}` - 訓練状態確認
- `POST /api/v1/training/evaluate/{model_name}` - モデル評価
- `GET /api/v1/prediction/models` - モデル一覧
- `GET /api/v1/prediction/features/importance/{model_name}` - 特徴量重要度

#### レースデータ
- `GET /api/v1/races` - レース一覧
- `GET /api/v1/races/{id}` - レース詳細
- `GET /api/v1/races/{id}/results` - レース結果

### 4.2 レスポンス形式

```json
{
  "success": true,
  "data": {},
  "message": "Success",
  "timestamp": "2025-08-21T00:00:00Z"
}
```

## 5. 機械学習モデル

### 5.1 特徴量エンジニアリング

#### 基本特徴量（20個）
- 枠番、馬番、馬齢、性別
- 騎手勝率、調教師勝率
- 過去成績統計（平均着順、勝率など）
- コース適性（芝/ダート、距離）

#### 追加特徴量（30個）
- ペース指数
- スピード指数
- 上がり3F統計
- 休養期間
- 斤量比
- 騎手×調教師コンビ成績
- 血統情報
- 賞金クラス

### 5.2 モデル構成

#### XGBoostパラメータ
```python
{
    "n_estimators": 1000,
    "max_depth": 6,
    "learning_rate": 0.01,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "early_stopping_rounds": 50
}
```

#### 最適化手法
- Optuna によるハイパーパラメータ調整
- 交差検証（TimeSeriesSplit）
- 確率キャリブレーション（Platt Scaling）

### 5.3 評価指標
- **Accuracy**: 70%以上
- **Precision**: 65%以上
- **ROC-AUC**: 0.75以上
- **ROI**: 100%以上（バックテスト）

## 6. ベッティング戦略

### 6.1 Kelly基準
```python
kelly_fraction = (p * b - q) / b
# p: 勝率
# b: オッズ - 1
# q: 1 - p
```

### 6.2 リスク管理
- 最大ベット額: 資金の10%
- 最小期待値: 1.2
- 分散投資: 最大3頭まで
- ストップロス: -30%

## 7. フロントエンド画面

### 7.1 ページ構成

#### ダッシュボード（/）
- 本日のレース予測サマリー
- 推奨ベット一覧
- モデル性能グラフ
- 収支状況

#### 予測画面（/predictions）
- 日付・競馬場選択
- レース一覧
- 詳細予測結果
- ベット戦略提案

#### バックテスト（/backtest）
- 期間設定
- パラメータ調整
- シミュレーション実行
- 結果グラフ表示

#### データ管理（/data）
- スクレイピング実行
- データ統計表示
- エクスポート機能

## 8. セキュリティ

### 8.1 認証・認可
- JWT トークン認証
- Role-based アクセス制御
- API レート制限

### 8.2 データ保護
- HTTPS 通信
- データベース暗号化
- 環境変数による秘密情報管理

## 9. パフォーマンス要件

### 9.1 レスポンスタイム
- API: 95%タイル < 200ms
- ページロード: < 3秒
- 予測処理: < 5秒/レース

### 9.2 スケーラビリティ
- 同時接続数: 100ユーザー
- データ容量: 100GB
- 処理能力: 1000レース/日

## 10. デプロイメント

### 10.1 環境構成

#### 開発環境
```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
  
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
  
  postgres:
    image: postgres:15
    ports: ["5432:5432"]
  
  redis:
    image: redis:7
    ports: ["6379:6379"]
```

#### 本番環境
- Backend: AWS ECS / Google Cloud Run
- Frontend: Vercel
- Database: AWS RDS / Cloud SQL
- Cache: ElastiCache / Cloud Memorystore

### 10.2 CI/CD

#### GitHub Actions
```yaml
- 自動テスト実行
- Linting / Type checking
- ビルド検証
- デプロイ（main branch）
```

## 11. 監視・ログ

### 11.1 メトリクス
- CPU/メモリ使用率
- API レスポンスタイム
- エラー率
- 予測精度

### 11.2 ログ管理
- アプリケーションログ
- アクセスログ
- エラーログ
- 監査ログ

## 12. 今後の拡張計画

### Phase 1（現在）
- ✅ 基本的な予測機能
- ✅ Webインターフェース
- ✅ バックテスト

### Phase 2
- [ ] リアルタイムオッズ取得
- [ ] 複勝・馬連・三連複対応
- [ ] モバイルアプリ

### Phase 3
- [ ] AI予測の説明機能（XAI）
- [ ] ユーザー管理機能
- [ ] 有料プラン

## 13. 制約事項

- netkeibaの利用規約遵守
- 1秒間に1リクエストの制限
- 個人利用目的のみ
- 商用利用不可

## 14. 参考資料

- [netkeiba](https://www.netkeiba.com/)
- [XGBoost Documentation](https://xgboost.readthedocs.io/)
- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

最終更新日: 2025年8月22日
バージョン: 1.0.0