<!-- generated-by: scripts/generate_engineering_docs.py -->
# claude-code-session-health — 実装トレーサビリティ

> 生成日: 2026-07-15 / 対象: `claude-code-session-health` / 確度: [低]
> 実装・manifest・既存資料の静的棚卸しに基づく。外部サービスの稼働状態と本番構成は未検証。

## 根拠台帳

| 種別 | Path | 状態 |
|---|---|---|
| package/source | `scripts` | 静的確認済み |
| existing docs | `README.md` | 静的確認済み |
| existing docs | `README.ja.md` | 静的確認済み |
| existing docs | `docs/verification-2026-07-05.md` | 静的確認済み |
| existing docs | `docs/zenn-draft.ja.md` | 静的確認済み |
| existing docs | `docs/verification-2026-07-04.md` | 静的確認済み |

## 検出した検証command

- manifestから標準command未検出

## 設定契約（名前のみ）

- `SESSION_HEALTH_CUMULATIVE` — `scripts/session_health.py`

値、credential、顧客データは収集していない。設定のrequired/optional、format、取得元は各entrypointとruntimeで確認する。

## 既存文書との関係

- `README.md`
- `README.ja.md`
- `docs/verification-2026-07-05.md`
- `docs/zenn-draft.ja.md`
- `docs/verification-2026-07-04.md`

既存ADR・公式schema・運用runbookがある場合はそれらを正典とし、generated docsは発見用索引として扱う。矛盾を見つけたら実装・正式文書・生成器のどれを直すかをreviewで決める。

## 未確認事項

- 動的route/schema/plugin、external gateway、mobile native設定。
- secret manager、provider console、production runtimeの値と適用version。
- migration適用状態、SLO実績、実データ量、owner/on-call。

## 更新ルール

- route/schema/screen/runtime構成を変更した差分では、対応する文書を同時更新する。
- 生成し直す前に手書き文書を正典へ昇格するか、生成対象外へ分離する。
- このディレクトリの `generated-by` marker付きファイルは本スクリプトで再生成できる。
