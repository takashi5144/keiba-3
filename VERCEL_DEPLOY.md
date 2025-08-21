# Vercelデプロイガイド

## 前提条件
- Vercelアカウント
- GitHubリポジトリ連携
- バックエンドAPI（別途デプロイ必要）

## デプロイ手順

### 1. Vercel CLIでのデプロイ

```bash
# Vercel CLIインストール
npm i -g vercel

# フロントエンドディレクトリに移動
cd frontend

# Vercelにログイン
vercel login

# デプロイ実行
vercel

# プロダクションデプロイ
vercel --prod
```

### 2. GitHub連携でのデプロイ（推奨）

1. [Vercel Dashboard](https://vercel.com/dashboard)にアクセス
2. "New Project"をクリック
3. GitHubリポジトリ`takashi5144/keiba-3`を選択
4. 以下の設定を行う：

#### Framework Preset
- **Framework**: Next.js
- **Root Directory**: `frontend`
- **Build Command**: `npm run build`
- **Output Directory**: `.next`

#### 環境変数設定
| 変数名 | 値 | 説明 |
|--------|-----|------|
| `NEXT_PUBLIC_API_URL` | `https://your-api.onrender.com/api` | バックエンドAPIのURL |

### 3. カスタムドメイン設定（オプション）

1. Vercel Dashboard > Settings > Domains
2. カスタムドメインを追加
3. DNSレコードを設定：
   ```
   Type: CNAME
   Name: www
   Value: cname.vercel-dns.com
   ```

## バックエンドAPIデプロイ

### Render.comでのデプロイ

1. [Render Dashboard](https://dashboard.render.com/)にアクセス
2. "New +" > "Web Service"を選択
3. GitHubリポジトリを接続
4. 以下の設定：
   - **Name**: keiba-api
   - **Root Directory**: backend
   - **Environment**: Docker
   - **Region**: Singapore
   - **Plan**: Free or Starter

5. 環境変数設定：
   ```
   DATABASE_URL=postgresql://user:pass@host/db
   REDIS_URL=redis://host:6379
   SECRET_KEY=your-secret-key
   ```

### Railway.appでのデプロイ（代替案）

```bash
# Railway CLIインストール
npm i -g @railway/cli

# プロジェクト作成
railway login
railway link
railway up
```

## デプロイ後の設定

### 1. Vercel環境変数更新

```bash
# Vercel CLIで環境変数設定
vercel env add NEXT_PUBLIC_API_URL production

# 値を入力: https://keiba-api.onrender.com/api
```

### 2. CORS設定（バックエンド）

backend/app/main.pyでCORS設定を更新：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://keiba-3.vercel.app",
        "https://your-custom-domain.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. 本番環境テスト

```bash
# API疎通確認
curl https://your-api.onrender.com/api/health

# フロントエンド確認
open https://keiba-3.vercel.app
```

## トラブルシューティング

### ビルドエラー

1. **TypeScriptエラー**
   ```bash
   # 型チェックをスキップ
   NEXT_TYPECHECK_DISABLE=1 vercel --prod
   ```

2. **依存関係エラー**
   ```bash
   # package-lock.json削除して再インストール
   rm package-lock.json
   npm install
   vercel --prod
   ```

### APIエラー

1. **CORS エラー**
   - バックエンドのCORS設定確認
   - Vercelのドメインを許可リストに追加

2. **接続エラー**
   - 環境変数`NEXT_PUBLIC_API_URL`確認
   - バックエンドAPIの稼働状態確認

## デプロイ状態確認

### Vercel
- Dashboard: https://vercel.com/takashi5144/keiba-3
- Deployments: https://vercel.com/takashi5144/keiba-3/deployments
- Analytics: https://vercel.com/takashi5144/keiba-3/analytics

### 監視設定

1. **Vercel Analytics**有効化
2. **Sentry**統合（エラー監視）
3. **Checkly**でアップタイム監視

## CI/CD設定

`.github/workflows/deploy.yml`:

```yaml
name: Deploy to Vercel

on:
  push:
    branches: [main]
    paths:
      - 'frontend/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: vercel/action@v1
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./frontend
```

## 料金プラン

### Vercel (フロントエンド)
- **Hobby**: 無料（個人利用）
- **Pro**: $20/月（商用利用）

### Render (バックエンド)
- **Free**: 無料（制限あり）
- **Starter**: $7/月
- **Standard**: $25/月

### 推定月額費用
- 開発環境: $0
- 本番環境（小規模）: $27/月
- 本番環境（中規模）: $100+/月