# 🚀 今すぐVercelにデプロイ

## ワンクリックデプロイ

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Ftakashi5144%2Fkeiba-3&project-name=keiba-frontend&repository-name=keiba-frontend&root-directory=frontend&env=NEXT_PUBLIC_API_URL&envDescription=Backend%20API%20URL&envExample=https%3A%2F%2Fyour-api.com%2Fapi)

上のボタンをクリックして、以下の手順でデプロイしてください。

## デプロイ手順

### 1. Vercelアカウントでログイン
- GitHubアカウントでログイン推奨

### 2. プロジェクト設定
自動的に以下が設定されます：
- **Repository**: `takashi5144/keiba-3`
- **Root Directory**: `frontend`
- **Framework**: Next.js

### 3. 環境変数設定
| 変数名 | 値 | 説明 |
|--------|-----|------|
| `NEXT_PUBLIC_API_URL` | `https://api.example.com/api` | バックエンドAPIのURL（後で変更可） |

一旦仮のURLで設定してOK:
```
https://api.example.com/api
```

### 4. "Deploy"をクリック

## デプロイ後の確認

### ビルドログ確認
```
✓ Compiled successfully
✓ Generating static pages
✓ Collecting page data
✓ Finalizing page optimization
```

### アクセスURL
デプロイ完了後、以下のようなURLが発行されます：
- **本番**: `https://keiba-frontend.vercel.app`
- **プレビュー**: `https://keiba-frontend-git-main-[username].vercel.app`

## トラブルシューティング

### ビルドエラーが出た場合

1. **Root Directoryを確認**
   - Settings → General → Root Directory
   - `frontend`になっているか確認

2. **Build Commandを確認**
   - Settings → General → Build & Development Settings
   - Build Command: `npm run build`
   - Install Command: `npm install`

3. **キャッシュクリア**
   - Settings → Functions → "Purge Cache"

4. **再デプロイ**
   - Deployments → 最新のデプロイ → "Redeploy"

### 404エラーが出た場合

環境変数を確認:
- Settings → Environment Variables
- `NEXT_PUBLIC_API_URL`が設定されているか

## 動作確認

デプロイ完了後、以下のページにアクセス:

1. **ダッシュボード**: `/`
2. **予測画面**: `/predictions`
3. **バックテスト**: `/backtest`

※ APIが未デプロイの場合、データは表示されませんがUIは確認できます。

## 次のステップ

### バックエンドAPIデプロイ

以下のサービスから選択:

1. **Render.com** (無料プランあり)
   ```bash
   cd backend
   render deploy
   ```

2. **Railway.app** (簡単デプロイ)
   ```bash
   railway up
   ```

3. **AWS/GCP** (本番向け)
   - EC2/Cloud Run
   - RDS/Cloud SQL
   - ElastiCache/Memorystore

### 環境変数更新

APIデプロイ後、Vercelの環境変数を更新:

1. Vercel Dashboard → Settings → Environment Variables
2. `NEXT_PUBLIC_API_URL`を実際のAPI URLに変更
3. 再デプロイ

## サポート

問題が発生した場合:
- [GitHub Issues](https://github.com/takashi5144/keiba-3/issues)
- [Vercel Documentation](https://vercel.com/docs)
- [Next.js Documentation](https://nextjs.org/docs)