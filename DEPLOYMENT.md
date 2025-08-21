# デプロイメントガイド

## 目次
- [開発環境セットアップ](#開発環境セットアップ)
- [本番環境デプロイ](#本番環境デプロイ)
- [クラウドデプロイ](#クラウドデプロイ)
- [メンテナンス](#メンテナンス)
- [トラブルシューティング](#トラブルシューティング)

## 開発環境セットアップ

### 前提条件
- Docker Desktop
- Python 3.11+
- Node.js 18+
- Poetry

### クイックスタート

#### Windows
```bash
# リポジトリクローン
git clone https://github.com/your-repo/keiba-analysis.git
cd keiba-analysis

# 環境変数設定
copy .env.example .env
# .envファイルを編集

# システム起動
scripts\start_system.bat
```

#### Mac/Linux
```bash
# リポジトリクローン
git clone https://github.com/your-repo/keiba-analysis.git
cd keiba-analysis

# 環境変数設定
cp .env.example .env
# .envファイルを編集

# 実行権限付与
chmod +x scripts/*.sh

# システム起動
./scripts/start_system.sh
```

### 手動セットアップ

1. **Docker サービス起動**
```bash
docker-compose up -d postgres redis
```

2. **バックエンド設定**
```bash
cd backend
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

3. **フロントエンド設定**
```bash
cd frontend
npm install
npm run dev
```

4. **ワーカー起動**
```bash
cd backend
poetry run celery -A app.core.celery_app worker --loglevel=info
poetry run celery -A app.core.celery_app beat --loglevel=info
```

## 本番環境デプロイ

### 1. 環境準備

```bash
# 本番環境設定ファイル作成
cp .env.production .env

# 必要な値を設定
vim .env
```

### 2. SSL証明書準備

```bash
# Let's Encrypt使用例
mkdir -p nginx/ssl
certbot certonly --standalone -d your-domain.com
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem
```

### 3. デプロイ実行

```bash
# 本番用イメージビルド
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# サービス起動
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# ログ確認
docker-compose logs -f
```

## クラウドデプロイ

### AWS デプロイ

#### 必要なサービス
- EC2 (アプリケーションサーバー)
- RDS PostgreSQL (データベース)
- ElastiCache Redis (キャッシュ)
- S3 (静的ファイル)
- CloudFront (CDN)
- ALB (ロードバランサー)

#### セットアップ手順

1. **VPC作成**
```bash
aws ec2 create-vpc --cidr-block 10.0.0.0/16
```

2. **RDS設定**
```bash
aws rds create-db-instance \
  --db-instance-identifier keiba-db \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 15.4 \
  --master-username keiba_admin \
  --master-user-password <password> \
  --allocated-storage 100
```

3. **ElastiCache設定**
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id keiba-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1
```

4. **EC2インスタンス起動**
```bash
# Amazon Linux 2023
aws ec2 run-instances \
  --image-id ami-xxxxxxxxx \
  --instance-type t3.medium \
  --key-name your-key \
  --security-group-ids sg-xxxxxxxxx \
  --subnet-id subnet-xxxxxxxxx
```

5. **アプリケーションデプロイ**
```bash
# EC2にSSH接続
ssh -i your-key.pem ec2-user@your-instance-ip

# Docker インストール
sudo yum update -y
sudo yum install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user

# Docker Compose インストール
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# アプリケーションクローン
git clone https://github.com/your-repo/keiba-analysis.git
cd keiba-analysis

# 環境変数設定
cp .env.production .env
vim .env  # AWS RDS/ElastiCacheのエンドポイントを設定

# デプロイ
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### GCP デプロイ

#### Cloud Run使用

1. **コンテナレジストリにプッシュ**
```bash
# 認証
gcloud auth configure-docker

# ビルド&プッシュ
docker build -t gcr.io/your-project/keiba-backend:latest ./backend
docker push gcr.io/your-project/keiba-backend:latest

docker build -t gcr.io/your-project/keiba-frontend:latest ./frontend
docker push gcr.io/your-project/keiba-frontend:latest
```

2. **Cloud Run デプロイ**
```bash
# バックエンド
gcloud run deploy keiba-backend \
  --image gcr.io/your-project/keiba-backend:latest \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=$DATABASE_URL,REDIS_URL=$REDIS_URL

# フロントエンド
gcloud run deploy keiba-frontend \
  --image gcr.io/your-project/keiba-frontend:latest \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated
```

### Vercel デプロイ (フロントエンドのみ)

```bash
cd frontend

# Vercel CLI インストール
npm i -g vercel

# デプロイ
vercel

# 環境変数設定
vercel env add NEXT_PUBLIC_API_URL
```

## メンテナンス

### バックアップ

#### データベース
```bash
# バックアップ作成
docker-compose exec postgres pg_dump -U keiba_user keiba_db > backup_$(date +%Y%m%d).sql

# S3にアップロード
aws s3 cp backup_$(date +%Y%m%d).sql s3://your-backup-bucket/
```

#### 自動バックアップ設定
```bash
# crontab追加
0 2 * * * /path/to/backup_script.sh
```

### アップデート

```bash
# コード更新
git pull origin main

# 依存関係更新
cd backend && poetry update
cd ../frontend && npm update

# イメージ再ビルド
docker-compose build

# ローリングアップデート
docker-compose up -d --no-deps --build backend
docker-compose up -d --no-deps --build frontend
```

### モニタリング

#### ヘルスチェック
```bash
# API
curl https://your-domain.com/api/health

# フロントエンド
curl https://your-domain.com/
```

#### ログ確認
```bash
# Docker logs
docker-compose logs -f --tail=100 backend

# アプリケーションログ
tail -f logs/api.log
tail -f logs/celery-worker.log
```

#### メトリクス確認
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001
- Flower: http://localhost:5555

## トラブルシューティング

### よくある問題

#### 1. データベース接続エラー
```bash
# 接続確認
docker-compose exec postgres psql -U keiba_user -d keiba_db -c "SELECT 1"

# 権限確認
docker-compose exec postgres psql -U keiba_user -d keiba_db -c "\l"
```

#### 2. Redis接続エラー
```bash
# 接続確認
docker-compose exec redis redis-cli ping

# メモリ使用量確認
docker-compose exec redis redis-cli info memory
```

#### 3. ポート競合
```bash
# 使用中のポート確認
netstat -an | grep :8000
netstat -an | grep :3000

# プロセス終了
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

#### 4. メモリ不足
```bash
# Docker リソース確認
docker stats

# 不要なコンテナ削除
docker system prune -a
```

#### 5. マイグレーションエラー
```bash
# マイグレーション状態確認
cd backend
poetry run alembic current

# ロールバック
poetry run alembic downgrade -1

# 再実行
poetry run alembic upgrade head
```

### ログレベル変更

```python
# backend/.env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR

# 再起動
docker-compose restart backend
```

### パフォーマンスチューニング

#### PostgreSQL
```sql
-- 接続数調整
ALTER SYSTEM SET max_connections = 200;

-- メモリ調整
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET work_mem = '4MB';

-- 再起動
SELECT pg_reload_conf();
```

#### Redis
```bash
# メモリ上限設定
docker-compose exec redis redis-cli CONFIG SET maxmemory 512mb
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

## セキュリティ

### チェックリスト
- [ ] 本番環境の SECRET_KEY を変更
- [ ] データベースパスワードを強化
- [ ] SSL証明書を設定
- [ ] ファイアウォール設定
- [ ] レート制限を有効化
- [ ] セキュリティヘッダーを確認
- [ ] 定期的なセキュリティアップデート
- [ ] ログ監視設定

### セキュリティアップデート
```bash
# 依存関係の脆弱性チェック
cd backend
poetry show --outdated
poetry audit

cd ../frontend
npm audit
npm audit fix
```

## サポート

問題が解決しない場合は、以下をご確認ください：
- [Issue Tracker](https://github.com/your-repo/keiba-analysis/issues)
- [Wiki](https://github.com/your-repo/keiba-analysis/wiki)
- ログファイル（`logs/`ディレクトリ）