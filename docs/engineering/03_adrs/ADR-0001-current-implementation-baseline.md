<!-- generated-by: scripts/generate_engineering_docs.py -->
# claude-code-session-health — ADR-0001 資料資産の正典と変更管理

> 生成日: 2026-07-15 / 対象: `claude-code-session-health` / 確度: [低]
> 実装・manifest・既存資料の静的棚卸しに基づく。外部サービスの稼働状態と本番構成は未検証。

## Status

Proposed — runtime実装が追加された時点で再レビュー

## Context

`claude-code-session-health` は現在のcheckoutで実行manifest、entrypoint、API、永続schema、画面実装を確認できない。アプリケーションが存在するような架空の技術判断をAcceptedにしない。

## Decision

- 現在は `active_project` として扱い、既存資料を正典候補として保持する。
- 実行可能性、production構成、API/DB/UIの存在を文書から推測しない。
- 実装追加時はmanifest、entrypoint、verification command、ownerをREADMEに追加し、新しいADRでruntime/data/delivery境界を決める。

## Existing evidence

- `README.md`
- `README.ja.md`
- `docs/verification-2026-07-05.md`
- `docs/zenn-draft.ja.md`
- `docs/verification-2026-07-04.md`

## Consequences

- 後発担当者は資料資産と実行可能なproductを混同しない。
- 現時点ではbuild/test/deploy手順を提供できない。これは欠落として明示する。
