# session-health

**Claude Code のトークンの95%は cache read（コンテキスト再読）に消えていた** —
このプラグインは、セッションが「トークン浪費フェーズ」に入ったことを検知し、
可視化だけの既存ツールと違って**ループを閉じます**: モデル自身に「/compact
提案・サブエージェント委譲」を指示し、statusline と通知に「切り時」を表示します。

English version: [README.md](README.md)

## 問題

Claude Code のプロンプトキャッシュは自動で、トークン単価も安い。しかし
**毎リクエストがキャッシュ済みコンテキスト全体を再読**するため、1セッションを
数時間続けると実測でこうなります（2026-07-02 の丸1日・12プロジェクト・
重複排除後2,592リクエストの集計）:

```
input      1.5M
output     1.6M
cacheRead  347M   <- 全トークンの95%
```

最悪のセッションは **cacheRead/output 比 231〜313倍**。statusline の警告だけ
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

さらに `/session-health:usage-report` で **プロジェクト×セッション×サブエージェント×モデル**
の4軸トークン内訳を出せます。requestId ベースの重複排除つき（ストリーミングは
1リクエストを複数JSONL行に書くため、素朴に合計すると2〜3倍水増しされます）。
サブエージェントのトランスクリプト（`<セッション>/subagents/` 配下の別ファイル。
見落とすと「委譲ゼロ」という誤結論になる）も集計対象です。

すべてローカルのトランスクリプトファイルだけで動きます。**外部送信は一切ありません。**

## Performance notes

Full usage report は `~/.claude/projects/` 配下のローカル transcript を
サブエージェント分も含めて走査するため、履歴が大きい環境では時間がかかることが
あります。日常の確認では対象を絞ると速くなります。

```bash
python3 scripts/usage_report.py --project agent-company-os
python3 scripts/usage_report.py --current ~/.claude/projects/.../session.jsonl
python3 scripts/usage_report.py --transcript ~/.claude/projects/.../session.jsonl
```

将来的には、繰り返しの full report を速くする増分キャッシュを追加する余地があります。

## セキュリティ / このプラグインが追加するもの

Claude Code のプラグインは commands / hooks / agents / MCP servers を追加できる
強力な仕組みです。個人リポジトリのプラグインを警戒するのは正しい感覚なので、
このプラグインが何を追加するかを明示します。

追加するもの:

- slash command: `/session-health:usage-report`
- `UserPromptSubmit` hook: `scripts/session_health.py hook`

追加しないもの:

- MCP server
- 外部API連携
- 常駐daemon
- ネットワーク送信
- Python標準ライブラリ以外の依存

解析対象はローカルの Claude Code transcript（`~/.claude/projects/`）だけです。
外部送信はしません。

信用より検証で判断したい場合は、まず [`hooks/hooks.json`](hooks/hooks.json)
（Claude Code がどのタイミングで何を実行するかの宣言）を読み、次に
[`scripts/`](scripts/) の2スクリプトと
[`commands/usage-report.md`](commands/usage-report.md) を確認してください。

## インストール

```
/plugin marketplace add House-lovers7/claude-code-session-health
/plugin install session-health@house-lovers7
```

フックと `/session-health:usage-report` は即座に有効。任意の2つ:

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

## compaction 対応（v0.3.0）

リクエスト数と cacheRead/output 比は、トランスクリプト全体ではなく
**最後の `/compact` 以降の「現在の生きたセグメント」**で測ります。`/compact`
するとモデルの実コンテキストは実際に縮む（実測26件で中央値約64%減）ため、
statusline はリセットされ（`🔥req231·246x` → `req20·76x`）、フックも圧縮後に
「また compact しろ」と鳴り続けません。`SESSION_HEALTH_CUMULATIVE=1` で
従来の全期間集計に戻せます。

## 既存ツールとの違い

[ccusage](https://github.com/ryoppippi/ccusage)（コストレポート）や
[Claude HUD](https://github.com/jarrodwatts/claude-hud)（コンテキスト可視化）
など優れた監視ツールは既にあります。ただしどれも read-only で、**人間に**
知らせるだけです。本プラグインの賭けは「最も安い介入点はモデル自身の行動」
だということ — 適切な瞬間に注入される1つの指示は、見なくなったダッシュボード
に勝ちます。閾値トリガーの自己是正をやっているツールは調査した範囲では
存在しませんでした（2026年7月時点の調査。反例は Issue で歓迎します）。

## サンプル出力（マスク済み）

`/session-health:usage-report` の実出力（プロジェクト名・セッション名はマスク）:

```
since 2026-07-01T19:00:00Z (local 07/02 04:00)  deduplicated away: 516.5M tok

== By project ==
                                     in      out   cacheRd   cacheCr   req
project-a                        176.0k   254.4k     58.6M      1.5M   371
project-b                        167.8k   197.9k     47.2M      1.7M   396
project-c                         92.0k   134.2k     39.3M      1.2M   202
...

== Top 15 sessions ==
project-a/session-01             176.0k   254.4k     58.6M      1.5M   371
      models=fable-5 cacheRd/out=231x retry=2 apiErr=3
project-b/session-02             125.3k   165.7k     45.2M      1.3M   354
      models=fable-5,opus-4-8 cacheRd/out=273x
...

== By agent ==
main                             779.8k     1.5M    312.6M      8.6M  1717
Explore                          440.2k    42.2k     14.7M      2.4M   454
general-purpose                  219.9k    50.1k     11.3M      1.7M   221
routine-worker                     4.4k     7.9k      3.6M    557.3k    81
Plan                              69.0k     5.5k      3.2M    408.7k    79

Health: cache re-reads 95% of all tokens (lower is better) /
main-thread share 89% (delegation keeps this moderate)
```

## 現状と限界

- **一部は計測済みです。** セッション内では、compaction によって実コンテキスト
  （1リクエストあたり input+cache_read+cache_creation）が実測26件で**中央値64%**
  縮み、縮小率は圧縮前サイズに単調依存します（Spearman ρ=0.975）。圧縮後フロアは
  約46〜69kトークンなので、フロアの約2倍未満での早期 `/compact` は得が小さいです。
  [`scripts/compaction_effect.py`](scripts/compaction_effect.py) で再現できます。
  **未検証:** 閉ループ運用での日跨ぎ*集計*コスト傾向。日次のワークロード量が約10倍
  変動するため生の日次%比較は交絡し、正規化した複数日系列が必要です。
- 解析は非公開のトランスクリプト内部仕様（JSONL のレコード形状、`subagents/`
  の配置）に依存します。2026-07-02 時点の Claude Code で検証済みで、将来の
  更新で修正が必要になる可能性があります。
- 閾値は私のワークロードに合わせた既定値です。環境変数で調整してください。

## 動作要件

- プラグイン対応の Claude Code
- Python 3.8+（標準ライブラリのみ）

## ライセンス

MIT
