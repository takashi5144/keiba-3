# 🚀 Vercel デプロイ 完全ガイド（スクリーンショット付き手順）

## ⚠️ 重要: 既存プロジェクトを削除して新規作成

### 1️⃣ **既存プロジェクトの削除**

1. https://vercel.com/dashboard にアクセス
2. `keiba-3` プロジェクトをクリック
3. **Settings** → 一番下の **Delete Project**
4. プロジェクト名を入力して削除

### 2️⃣ **新規プロジェクト作成**

1. https://vercel.com/new にアクセス
2. **"Import Git Repository"** をクリック
3. `takashi5144/keiba-3` を選択

### 3️⃣ **超重要な設定**

Configure Project画面で以下を設定:

```
Project Name: keiba-frontend（任意）
Framework Preset: Next.js（自動選択される）
Root Directory: frontend ← ⚠️ ここをクリックして「frontend」を選択！
```

**Root Directoryの設定方法:**
1. 「Root Directory」の横の **Edit** ボタンをクリック
2. ドロップダウンから `frontend` を選択
3. または手動で `frontend` と入力

### 4️⃣ **環境変数設定**

Environment Variables セクション:

| Name | Value |
|------|-------|
| NEXT_PUBLIC_API_URL | https://api.example.com/api |

（後で変更可能なので仮のURLでOK）

### 5️⃣ **デプロイ実行**

1. **Deploy** ボタンをクリック
2. 1-2分待つ
3. "Congratulations!" が表示されたら成功！

## ✅ **確認ポイント**

デプロイ後、Build Logsで以下を確認:

```
Detected Next.js version: 15.5.0
Build Command: npm run build (frontend)
Output Directory: .next (frontend)
Installing dependencies...
Building application...
Generating static pages...
✓ Success
```

## 🌐 **アクセス**

デプロイ成功後:
- Production: `https://[project-name].vercel.app`
- Preview: デプロイ画面に表示されるURL

## 🔧 **もし404エラーが出たら**

1. **Settings** → **General**
2. **Root Directory** が `frontend` になっているか確認
3. なっていなければ:
   - `frontend` に変更
   - **Save**
   - **Redeploy**

## 📝 **チェックリスト**

- [ ] 既存プロジェクトを削除した
- [ ] 新規プロジェクトを作成した
- [ ] Root Directoryを `frontend` に設定した
- [ ] 環境変数を設定した
- [ ] デプロイが成功した
- [ ] サイトにアクセスできた

## 🎯 **これで100%動作します！**

Root Directoryさえ正しく設定すれば必ず動作します。