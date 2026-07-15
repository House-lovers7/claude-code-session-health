<!-- generated-by: scripts/generate_engineering_docs.py -->
# claude-code-session-health — 見積り（資料資産の引継ぎ確認）

> 生成日: 2026-07-15 / 対象: `claude-code-session-health` / 確度: [低]
> 実装・manifest・既存資料の静的棚卸しに基づく。外部サービスの稼働状態と本番構成は未検証。

## 現在の前提

runtime manifest・entrypoint・API・DB・UIを検出していないため、アプリ開発工数を推測しない。見積対象は、この資料資産を後発担当者が再利用できるか判断するための確認だけとする。

| 作業 | P50 | P90 | 根拠 | 完了条件 |
|---|---:|---:|---|---|
| 正典・owner・利用目的の確認 | 1h | 3h | `README.md` | 正典と更新責任者が明確 |
| 実行物の有無と保管場所の確認 | 1h | 4h | project root | 別repo/外部保管/未実装を確定 |
| **合計** | **2h** | **7h** | - | project/asset/archive判断が可能 |

> [低] 実装が別場所に存在すると判明した時点で、そのrepoを再棚卸しして見積り直す。
