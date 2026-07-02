---
title: "Claude Codeのトークン、95%は cache read に消えていた — 実測と、フックで直す closed-loop の作り方"
emoji: "🔥"
type: "tech"
topics: ["claudecode", "llm", "ai", "生産性"]
published: false
---

<!-- 公開前チェック: プロジェクト名・顧客名のマスキング確認 / スクショの固有名詞 / 数値の再確認 -->

## TL;DR

- Claude Code を1日回した実測で、消費トークンの**95%が cache read（コンテキスト再読）**だった。output はわずか0.4%
- 最悪のセッションは cacheRead/output 比 **246倍**。原因は「1セッションを長く続けること」そのもの
- statusline の警告は**閾値の2倍を超えても無視していた**（自分が）。効いたのは、フックで**モデル自身に是正指示を注入する**閉ループ
- 仕組みをプラグイン `session-health` として公開した: https://github.com/House-lovers7/claude-code-session-health

## きっかけ

朝4時から Claude Code（Fable 5）を回していて、ふと「どの処理が一番トークンを
食っているのか」が気になった。`~/.claude/projects/` 配下には全セッションの
トランスクリプトが JSONL で残っているので、正確な内訳はローカルだけで出せる。

## 集計してみる — 2つの落とし穴

JSONL の assistant レコードには `message.usage`（input / output / cacheRead /
cacheCreation）と `requestId`、`sessionId` が入っている。素朴に合計すると
2つの罠にはまる。

**罠1: ストリーミングの重複。** 1リクエストが複数の JSONL 行に分かれて書かれる
ため、行単位で合計すると2〜3倍に水増しされる。`requestId` で重複排除が必要
（この日の実測では、重複排除で 489M トークン分の水増しを除外した）。

**罠2: サブエージェントは別ファイル。** サブエージェントのトランスクリプトは
本体と同じファイルではなく `<プロジェクト>/<セッションID>/subagents/agent-*.jsonl`
に格納される。ここを見落とした私は一度「委譲ゼロ」という誤った結論を出した。
実際は843リクエスト分の委譲があった。**集計を疑い、構造を検証してから結論を
出すべき**という教訓ごと共有したい。

## 実測結果

1日分（12プロジェクト・2,428リクエスト、重複排除済み）:

| 種別 | トークン | 割合 |
|---|---|---|
| cache read | 318.8M | **95%** |
| cache creation | 12.8M | 3.8% |
| input | 1.5M | 0.4% |
| output | 1.5M | 0.4% |

セッション別ワーストは **371リクエスト・cacheRead/output 比231倍**。
上位セッションはどれも175〜300倍だった。

<!-- TODO: usage_report.py 出力のスクリーンショット（プロジェクト名マスク） -->

## なぜこうなるのか

プロンプトキャッシュ自体は自動で、単価も非キャッシュ入力よりはるかに安い。
問題は**毎リクエストがキャッシュ済みコンテキスト全体を再読する**構造にある。
セッションが長くなる → コンテキストが太る → 1ターンごとの再読量が増える、
という雪だるま。単価が安くても300M トークン再読すれば支配的コストになる。

もうひとつの発見: **組み込みサブエージェント（Explore / Plan / general-purpose）
はメインセッションのモデルを継承する**。「探索は安いモデルへ」と CLAUDE.md に
書いても、明示的にモデル指定した custom agent を使わない限り、探索が上位モデル
で走り続ける。この日、探索エージェントは opus で334回動き、haiku の出番はゼロ
だった。

## 対策: 可視化では行動が変わらなかった

実は statusline に「セッション1.5MB超で警告」を仕込んであった。結果:
**3.4MBまで膨張**。人間（私）は警告を見ない。

そこで発想を変えて、**モデル側に自覚させる**ことにした。Claude Code の
`UserPromptSubmit` フックは、プロンプト送信のたびにスクリプトを実行し、
標準出力の `additionalContext` をモデルのコンテキストに注入できる。

```
閾値検知（リクエスト80回超 or cacheRead/output比150倍超）
  → 「区切りで /compact か新セッションを提案せよ。
      探索・定型作業はサブエージェントへ委譲せよ」を注入
  → モデルが自分から畳み時を提案してくる
```

注入は20リクエストに1回・約60トークンなので、是正コストは無視できる。
同じ判定エンジンを statusline（3段階表示）と Stop フック通知（「切り時」
サフィックス）にも接続して、人間側の導線も残した。

## 既存ツールとの違い

ccusage（コストレポート）や Claude HUD(コンテキスト可視化)など優れた監視
ツールは既にある。ただし調査した範囲ではすべて read-only で、閾値トリガーで
モデルの挙動を変える closed-loop の実装は見つからなかった（2026年7月時点、
反例歓迎）。「最も安い介入点はダッシュボードではなくモデル自身の行動」が
このプラグインの賭けどころ。

## インストールが怖い人向け: このプラグインが追加するもの

Claude Code のプラグインは強力です。commands / hooks / agents / MCP servers
などを追加できるため、よくわからないプラグインを入れるのは普通に怖いと
思います。私もそう思います。

なので、このプラグインが何を追加するかを明示しておきます。

`session-health` が追加するものは主に2つです。

1. `/session-health:usage-report`
   - ローカルの `~/.claude/projects/` 配下にある Claude Code transcript を読み、token usage を集計する slash command
   - 集計軸は `project × session × subagent × model`
   - 外部送信はしません

2. `UserPromptSubmit` hook
   - プロンプト送信時に、現在のセッション状態をローカル transcript から読む
   - 閾値を超えている場合だけ、短い `additionalContext` をモデルに注入する
   - 目的は「次の区切りで /compact か新セッションを提案せよ」とモデルに知らせることです

このプラグインは MCP server を追加しません。外部APIにも送信しません。
Python標準ライブラリだけで動きます。

不安な場合は、インストール前にリポジトリ内の以下だけ確認してください。

- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `hooks/hooks.json`
- `commands/usage-report.md`
- `scripts/session_health.py`
- `scripts/usage_report.py`

特に見るべきなのは `hooks/hooks.json` です。ここに、Claude Code がどの
タイミングで何を実行するかが書かれています。

## 使い方

```
/plugin marketplace add House-lovers7/claude-code-session-health
/plugin install session-health@house-lovers7
```

フックと `/session-health:usage-report`（4軸内訳の slash command）は即有効。statusline と
通知の接続はREADME参照。すべてローカル完結で外部送信なし、閾値は環境変数で
調整可能。

## まとめ

- トークン最適化の主戦場は output ではなく **cache read**、つまり**セッションの長さ**
- 集計は requestId 重複排除と subagents ディレクトリを忘れると誤診する
- 可視化は見なくなる。**モデルに直させる**のが一番安い介入だった

ユーザーに残る操作は「通知か statusline を見て /compact と打つ」だけになった。
同じ構造（検知→モデルへの注入）は、委譲の徹底やセキュリティ規約の再徹底など
他の「守られないルール」にも応用できるはず。
