<!-- generated-by: scripts/generate_engineering_docs.py -->
# claude-code-session-health — One Pager / オンボーディング概要

> 生成日: 2026-07-15 / 対象: `claude-code-session-health` / 確度: [低]
> 実装・manifest・既存資料の静的棚卸しに基づく。外部サービスの稼働状態と本番構成は未検証。

## コンセプト

claude-code-session-health は `active_project` として存在するが、目的・owner・実行対象は現在のcheckoutから確認できない。ディレクトリ名から用途を推測しない。

## 誰の何を解くか

- 対象領域: active_project
- 想定利用者: 未確認（source request / owner未配置）
- 価値仮説: 未確認。実装または元要求が入るまで価値仮説を確定しない。

## 現在地

| 項目 | 観測結果 |
|---|---|
| 技術スタック | manifestから未特定 |
| API | 0 endpoint signal |
| データモデル | 0 unique entity signal |
| 画面 | 0 route/screen signal |
| 実行基盤 | 構成ファイル未検出 |
| package / module | 1 component signal |
| tests | 0 file signal |

## ソースマップ

| Component | Path | 責務 |
|---|---|---|
| `scripts` | `scripts` | CLI・バッチ・運用入口 |

## 最初に使うコマンド

| 目的 | Command |
|---|---|
| 未検出 | READMEまたはCIから確認 |

## 変更箇所の入口

| 変更対象 | 最初に読むpath | 同時に確認するもの |
|---|---|---|
| 実装入口未検出 | `README.md` | manifestと実装構造を確認 |

## 引継ぎ時の未解決ギャップ

| Priority | Requirement | 状態・理由 | Evidence |
|---|---|---|---|
| P1 | `entrypoints` | missing: 実行entrypointを特定できない。資料/資産なら「実行物なし」の明記が必要。 | `docs/engineering/README.md` |
| P1 | `major_modules_and_packages` | partial: package/moduleはあるが、責務、依存方向、公開境界、影響範囲が不足。 | `.claude/` |
| P1 | `startup_and_verification_commands` | missing: 起動・検証commandを静的証拠から特定できず、生成文書にも実行可能な手順がない。 | `docs/engineering/README.md` |
| P2 | `infrastructure_services_and_environment_names` | missing: runtime/service構成と環境変数名を特定できない。local/資料のみでも明示が必要。 | `README.md` |

## スコープ境界

- [高] productionの稼働、外部provider設定、secret値は未確認。
- [高] API・DB・画面が未検出の場合は推測せず、実装入口の追加を課題として残す。
- [中] 初回変更前に `07_traceability.md` の根拠と未確認事項を確認する。
