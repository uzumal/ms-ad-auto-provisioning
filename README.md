# MS AD Auto Provisioning

Active Directory の大量ユーザー・グループ作成およびメンバーシップ管理の自動化ツール

## 概要

このツールセットは、Active Directory 環境で大量のユーザー（56,000件）とグループを効率的に作成・管理するためのスクリプト群です。

### 構成ファイル

```
ms-ad-auto-provisioning/
├── README.md                           
├── generate_ad_duo_csv.py              # CSV生成スクリプト（Python）
├── Add-ADGroups.ps1                    # グループ作成スクリプト
├── Add-ADUsers.ps1                     # ユーザー作成スクリプト
└── Add-ADGroupMembership-Basic.ps1     # メンバーシップ追加スクリプト
```

## 機能

### CSV生成（Python）

#### 特徴
- **完全一意性保証**: 全てのユーザー名、DisplayName、UPN/Emailが重複しない
- **大量データ対応**: 56,000件のユーザー生成が可能
- **カスタマイズ可能**: パラメータでドメイン、OU、パスワード等を指定

#### 生成されるCSVファイル
- `users.csv`: ユーザー情報（12項目）
- `groups.csv`: グループ情報（5項目）
- `group_membership.csv`: メンバーシップ情報（2項目）

## セットアップ

### 前提条件

#### Python環境
- Python 3.7以上
- 標準ライブラリのみ使用（追加パッケージ不要）

#### PowerShell環境
- Windows PowerShell 5.1以上 または PowerShell Core 7.x
- Active Directory モジュール
- ドメイン管理者権限

#### Active Directory環境
- Windows Server 2016以上推奨
- 十分なディスク容量（56,000ユーザー分）

### インストール

1. **リポジトリのクローン**
   ```bash
   git clone <repository-url>
   cd ms-ad-auto-provisioning
   ```

2. **PowerShell実行ポリシーの設定**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

3. **Active Directoryモジュールの確認**
   ```powershell
   Import-Module ActiveDirectory
   ```

## 使用方法

### 1. CSV生成

```bash
python generate_ad_duo_csv.py \
  --count 56000 \
  --domain local.local \
  --upn-suffix local.local \
  --user-ou "OU=local,DC=local,DC=local" \
  --group-ou "OU=local,DC=local,DC=local" \
  --default-password 'Password' \
  --existing-group local \
  --auto-groups 5 \
  --outdir .
```

#### パラメータ説明
- `--count`: 生成するユーザー数（デフォルト: 56000）
- `--domain`: ADドメイン名
- `--upn-suffix`: UPNサフィックス
- `--user-ou`: ユーザー作成先OU
- `--group-ou`: グループ作成先OU
- `--default-password`: 初期パスワード
- `--existing-group`: 全ユーザーが参加する既存グループ
- `--auto-groups`: 自動作成するグループ数
- `--outdir`: 出力ディレクトリ

### 2. Active Directory への投入

#### 手順1: グループ作成
```powershell
.\Add-ADGroups.ps1 -server "dc.yourdomain.com"
```

#### 手順2: ユーザー作成
```powershell
.\Add-ADUsers.ps1 -server "dc.yourdomain.com"
```

#### 手順3: メンバーシップ追加
```powershell
.\Add-ADGroupMembership.ps1 -server "dc.yourdomain.com"
```

## パフォーマンス仕様

### CSV生成性能
- **処理時間**: 56,000ユーザー約30秒
- **メモリ使用量**: 約50MB
- **出力ファイルサイズ**: 
  - users.csv: 約15MB
  - groups.csv: <1KB
  - group_membership.csv: 約3MB

## ライセンス

MIT License