# Codex で2台のPCから作業するためのセットアップ

## 結論

このプロジェクトでは GitHub を「共有する正本」として使います。各PCには
GitHubから同じリポジトリを clone し、作業開始前に pull、終了時に commit と
push を行います。Codexのローカル作業フォルダそのものが自動同期されるわけでは
ないため、PCを移る前の push が重要です。

現在のリモートリポジトリ:

```text
https://github.com/KakeMyo/master_BOGP.git
```

## 別PCで最初に1回だけ行うこと

### 1. GitHubにサインインする

リポジトリの閲覧とcloneは現在公開設定のため未ログインでも可能ですが、変更を
pushするには `KakeMyo/master_BOGP` への書き込み権限があるGitHubアカウントでの
認証が必要です。

初心者向けには GitHub Desktop を推奨します。

1. GitHub Desktopをインストールする。
2. ブラウザ経由で、書き込み権限のあるGitHubアカウントにサインインする。
3. GitHub Desktopの `File` → `Clone Repository` → `URL` を開く。
4. 上記URLを入力し、保存先を選んで `Clone` を実行する。

コマンドラインを使う場合は、GitHub CLIをインストールしてから次を実行します。

```bash
gh auth login
gh repo clone KakeMyo/master_BOGP
cd master_BOGP
```

HTTPSでGitHubの通常パスワードをGitのパスワードとして入力する方式は使えません。
GitHub Desktopまたは `gh auth login` のブラウザ認証を使うのが簡単です。

### 2. 作業ブランチを取得する

clone後、そのPCのリポジトリ内で次の設定を1回だけ行います。

```bash
git config pull.rebase true
git config fetch.prune true
git config push.autoSetupRemote true
```

これにより、pull時は不要なマージコミットを作らず、削除済みのリモートブランチを
整理し、新規ブランチの初回push先を自動設定できます。

このPCで現在使っているブランチを続ける場合:

```bash
git fetch origin
git switch codex/premethod
git pull --rebase
```

ただし、このPCに残っている未コミット変更は、commitしてpushするまで別PCには
現れません。

### 3. Python環境を作る

`.venv` はPCごとに作り直します。プロジェクト自体は Python 3.9 以上を要求します。

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

### 4. Codexでプロジェクトを開く

Codexでcloneした `master_BOGP` フォルダをプロジェクトとして開きます。必ず
`pyproject.toml` と `AGENTS.md` が見えるリポジトリ直下を選びます。

Codexはリポジトリ内の `AGENTS.md` を読み、セットアップ方法、テスト方法、
成果物や秘密情報の扱いを両PCで共通化できます。

## PCを切り替えるときの運用

### 作業を始めるPC

```bash
git status
git pull --rebase
```

`git status` に未コミット変更がある場合は、pullする前にその変更をcommitするか、
安全に退避する必要があります。判断できない場合はCodexに状態確認を依頼します。

### 作業を終えるPC

```bash
git status
git add -p
git commit -m "変更内容を表すメッセージ"
git push
```

新しいブランチの初回pushだけは次を使います。

```bash
git push -u origin ブランチ名
```

pushが成功したことを確認してから、もう一方のPCへ移ります。

## 同期されるもの／されないもの

GitHub経由で同期されるもの:

- commitしてpushしたソースコード、研究ノート、設定、資料
- `AGENTS.md` などリポジトリ内のCodex向け指示
- Gitのブランチと履歴

通常は同期しないもの:

- commitしていない変更
- `.venv/`、キャッシュ、`outputs/`、`results/`、`slides/`
- `.env` やAPIキーなどの秘密情報
- CodexのPC固有の認証情報、個人設定、ローカル履歴

秘密情報が必要になった場合は、値そのものをGitへ入れず、各PCで個別に設定し、
変数名だけを `.env.example` に記載します。

## 衝突を避けるルール

- 同じブランチを2台で同時に編集しない。
- PCを移る前にcommitとpush、移った直後にpullを行う。
- 長い作業は `codex/テーマ名` のような専用ブランチで行う。
- `main` へ直接大きな変更を積まず、確認後にマージする。
- PDF、PPTX、XLSXは行単位でマージできないため、同じファイルを2台で同時編集しない。

## Codexのチャットも同じ状態で続けたい場合

Gitはファイルと履歴を同期しますが、ローカル環境・認証・未保存状態の共有手段では
ありません。対応するCodexアプリでは、同じGitリポジトリを両方のホストに保存した
うえでRemote Connections/Handoffを使う方法もあります。ただし通常の開発では、
GitHubへcommit/pushして別PCでpullする運用が最も分かりやすく確実です。
