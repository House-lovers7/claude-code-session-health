<!-- generated-by: scripts/generate_engineering_docs.py -->
# claude-code-session-health — 非機能要件（資料資産）

> 生成日: 2026-07-15 / 対象: `claude-code-session-health` / 確度: [低]
> 実装・manifest・既存資料の静的棚卸しに基づく。外部サービスの稼働状態と本番構成は未検証。

## 適用範囲

実行productを検出していないため、可用性・latency・throughputのSLOを設定しない。現在測れるのは資料資産の完全性だけ。

| Quality | 判定方法 | 現在の根拠 |
|---|---|---|
| 正典性 | ownerとsource requestが明記される | `README.md`, `README.ja.md`, `docs/verification-2026-07-05.md`, `docs/zenn-draft.ja.md`, `docs/verification-2026-07-04.md` |
| 追跡性 | 判断がADR・根拠pathへ辿れる | Proposed ADR |
| 再利用性 | 入力、出力、利用手順、廃止条件が明記される | 未確認 |

## runtime追加時

API/UI/job/dataの実装境界が決まった後でSLI、target、window、error budget、alert、rollbackを定義する。根拠なしの数値は先に置かない。
