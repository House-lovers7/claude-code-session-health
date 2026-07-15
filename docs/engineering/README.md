<!-- generated-by: scripts/generate_engineering_docs.py -->
# claude-code-session-health — Engineering Handbook / Start Here

> 生成日: 2026-07-15 / 対象: `claude-code-session-health` / 確度: [低]
> 実装・manifest・既存資料の静的棚卸しに基づく。外部サービスの稼働状態と本番構成は未検証。

## 60分で把握する

1. コンセプト: claude-code-session-health は `active_project` として存在するが、目的・owner・実行対象は現在のcheckoutから確認できない。ディレクトリ名から用途を推測しない。
2. classification: `active_project` / stack: runtime未特定
3. install: install command未検出
4. run/check: manifest script未検出
5. entrypoint: entrypoint未検出

## 実装スナップショット

| 項目 | 現在値 | 最初に読むpath |
|---|---:|---|
| package/component | 1 | `scripts` |
| API | 0 | 未検出 |
| entity | 0 | 未検出 |
| screen/entry UI | 0 | 未検出 |
| test files | 0 | 未検出 |

## 最初に確認する既存の正典候補

- `README.md`
- `README.ja.md`
- `docs/verification-2026-07-05.md`
- `docs/zenn-draft.ja.md`
- `docs/verification-2026-07-04.md`

既存ADR、OpenAPI、schema、運用runbookがある場合は、下記generated docsより先に読む。

## 引継ぎblocking / partial

| Priority | Requirement | 状態・理由 | Evidence |
|---|---|---|---|
| P1 | `entrypoints` | missing: 実行entrypointを特定できない。資料/資産なら「実行物なし」の明記が必要。 | `docs/engineering/README.md` |
| P1 | `major_modules_and_packages` | partial: package/moduleはあるが、責務、依存方向、公開境界、影響範囲が不足。 | `.claude/` |
| P1 | `startup_and_verification_commands` | missing: 起動・検証commandを静的証拠から特定できず、生成文書にも実行可能な手順がない。 | `docs/engineering/README.md` |
| P2 | `infrastructure_services_and_environment_names` | missing: runtime/service構成と環境変数名を特定できない。local/資料のみでも明示が必要。 | `README.md` |

## 読む順番

1. [One Pager](./00_one_pager.md)
2. [技術スタック比較](./01_stack_comparison.md)
3. [アーキテクチャ・システム構成](./02_architecture.md)
4. [ADR](./03_adrs/ADR-0001-current-implementation-baseline.md)
5. [API定義](./04_api.md)
6. [データモデル・ER図](./05_data_model.md)
7. [非機能要件・SLO/SLI](./05_nfr_slo.md)
8. [画面設計](./06_screen_design.md)
9. [P50/P90見積り](./06_estimation.md)
10. [実装トレーサビリティ](./07_traceability.md)
11. [学習・保守ロードマップ](./08_learning_roadmap.md)

## 使い方

- generated docsは実装発見用handbook。既存ADR、OpenAPI、schema、runbookがある場合は既存正典を優先する。
- path・数・versionは静的検出した事実。目的やpath由来の責務は `[中]` の推定を含む。
- production、external console、secret値、migration適用状態は未確認。
