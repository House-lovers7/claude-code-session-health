# session-health

**Claude Code のトークンの95%は cache read（コンテキスト再読）に消えていた** —
このプラグインは、セッションが「トークン浪費フェーズ」に入ったことを検知し、
可視化だけの既存ツールと違って**ループを閉じます**: モデル自身に「/compact
提案・サブエージェント委譲」を指示し、statusline と通知に「切り時」を表示します。

English version: [README.md](README.md)

## 問題

Claude Code のプロンプトキャッシュは自動で、トークン単価も安い。しかし
**毎リクエストがキャッシュ済みコンテキスト全体を再読**するため、1セッションを
数時間続けると実測でこうなります（実際の1日・12プロジェクトの集計）:

```
input      736k
output     1.4M
cacheRead  284.7M   <- 全トークンの95%
```

最悪のセッションは **cacheRead/output 比 200〜300倍**。statusline の警告だけ
では行動は変わりませんでした（閾値の2倍を超えても無視していた実績あり）。
効いたのは**モデル側に自覚させる**こと — 閾値を超えたら、以降のプロンプトに
「区切りで畳め・委譲しろ」という指示が自動注入されます。

## 機能

判定エンジンは1つ（`scripts/session_health.py`）、出口は3つ:

| 出口 | 仕組み | 見えるもの |
|---|---|---|
| **モデルの自己是正** | `UserPromptSubmit` フック（自動で有効化） | 切り時になると、モデルがタスクの区切りで `/compact` や新セッションを提案し、探索をサブエージェントに委譲し始める |
| **statusline** | 任意設定（下記） | `📜req56·120x` → `🟡` → `🔥req231·246x ⚠️/compact` |
| **Stop通知** | 任意設定（下記） | 応答完了通知に ` \| cut point: req231 / re-read 246x -> /compact` が付く |

さらに `/usage-report` で **プロジェクト×セッション×サブエージェント×モデル**
の4軸トークン内訳を出せます。requestId ベースの重複排除つき（ストリーミングは
1リクエストを複数JSONL行に書くため、素朴に合計すると2〜3倍水増しされます）。
サブエージェントのトランスクリプト（`<セッション>/subagents/` 配下の別ファイル。
見落とすと「委譲ゼロ」という誤結論になる）も集計対象です。

すべてローカルのトランスクリプトファイルだけで動きます。**外部送信は一切ありません。**

## インストール

```
/plugin marketplace add House-lovers7/claude-code-session-health
/plugin install session-health@house-lovers7
```

フックと `/usage-report` は即座に有効。任意の2つ:

**statusline** — [`scripts/statusline-example.sh`](scripts/statusline-example.sh)
を参照。既存の statusline スクリプトなら1行追加:

```bash
health=$(printf '%s' "$input" | python3 "<plugin>/scripts/session_health.py" statusline 2>/dev/null)
```

**Stop通知** — Stop フックから送っている既存の通知に `status` モードの出力を連結:

```bash
extra=$(printf '%s' "$input" | python3 "<plugin>/scripts/session_health.py" status 2>/dev/null)
notify "応答完了$extra"
```

## 閾値

既定: **切り時（hot）** = リクエスト80回 or cacheRead/output比150倍 /
**注意（warn、statuslineのみ）** = 50回 or 100倍。環境変数で変更可能
（`SESSION_HEALTH_HOT_REQS` 等 — 一覧は
[`scripts/session_health.py`](scripts/session_health.py) のヘッダ参照）。

フックの再発火は20リクエストに1回まで、注入は1回約60トークンなので、
是正コスト自体は安く収まります。

## 既存ツールとの違い

[ccusage](https://github.com/ryoppippi/ccusage)（コストレポート）や
[Claude HUD](https://github.com/jarrodwatts/claude-hud)（コンテキスト可視化）
など優れた監視ツールは既にあります。ただしどれも read-only で、**人間に**
知らせるだけです。本プラグインの賭けは「最も安い介入点はモデル自身の行動」
だということ — 適切な瞬間に注入される1つの指示は、見なくなったダッシュボード
に勝ちます。閾値トリガーの自己是正をやっているツールは調査した範囲では
存在しませんでした（2026年7月時点の調査。反例は Issue で歓迎します）。

## 動作要件

- プラグイン対応の Claude Code
- Python 3.8+（標準ライブラリのみ）

## ライセンス

MIT
