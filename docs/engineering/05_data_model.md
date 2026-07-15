<!-- generated-by: scripts/generate_engineering_docs.py -->
# claude-code-session-health — データモデル・ER図

> 生成日: 2026-07-15 / 対象: `claude-code-session-health` / 確度: [低]
> 実装・manifest・既存資料の静的棚卸しに基づく。外部サービスの稼働状態と本番構成は未検証。

## ER / データフロー

```mermaid
flowchart LR
    Input[Input] --> Process[In-memory / file processing]
    Process --> Output[Output]
    Unknown[(Persistent store: 未検出)]
```

> [中] entity名はschema/migrationから直接検出。属性・関係は誤推測を避けるため、正典schemaで確認できないものを補完していない。

## Entity台帳

| Entity | 検出field | 根拠 | 未確認事項 |
|---|---|---|---|
| 永続entity未検出 | - | manifest/schema/migration未検出 | file・外部管理・永続化なしのいずれかを確認 |

## Relation台帳

- relationを静的検出できず。relation定義・外部キー・application joinを確認

## 変更時の実務チェック

- schema/migration正典: 未検出
- API影響: APIとの結線を検索
- tenant/user境界、主キー、一意制約、外部キー、削除方式、seed/fixtureをmigrationと照合する。
- migration/apply前にbackup、forward/backward compatibility、rollback可否をレビューする。
