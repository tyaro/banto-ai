# 登録dev/smoke区切りの結果形式と保存ledger検算

2026-09-21 JST。実装savepoint **60b2bdb3d2556b280b10991a2fd1d47d4566714d**。
[API仕様](../anomaly-v03-independent-audit-and-checkpoints.md#全120区切りの結果形式とpayload検算api) / [短い再開用引継ぎ](../current-handoff.md)。

`anomaly_v03_chunk_contract.py` を追加し、外部campaign plan・chunk index・attempt番号から登録6件を選び、結果のsource/runtime、dataset/slot順序、共通input hash、coverage、失敗・判定保留を検査できるようにした。dev96区切りとsmoke24区切りの計720件を対象とする結果形式であり、この件数の実データを今回処理したものではない。

新format/scopeを用い、campaignのcanonical hash、選択区切りのidentity hash、source revisionを結合する。旧engineering-devの6件用public APIは維持し、新旧形式は最初の区切りでも相互拒否する。共通の6件validatorと保存ledger検算ループだけを内部関数へ抽出した。

新 `audit_chunk_payloads` は保存bytesのmappingからplanned/context、dataset/evaluation hash、identity/input/events/source、profile状態、開始/終了journal、exact inventoryを照合し、6件の保存score以降を既存の独立実装で検算する。ファイル読取り、公開marker、source capture、consumer revision、監視、campaign journal/descriptorとの照合は呼出側責務。現行 `attempt-audit` CLIは旧形式のchunk 0専用のままで、次工程で新形式のIO/監視/report対応を接続する。

既存の資源上限は `provisional_validation_caps` として結果構造の検査に用いる。campaign実行予算は未確定、execution_authorized/budgets_frozen/formal_permission=false、campaign_evaluations_credited=0を維持。profile/score導出の独立検算と完全S6は追加していない。

## 検証と資源

新14件は単独でpass/5.936秒。全120区切りの固定順序・720 identities、dev/smokeの境界、再試行、異なるcampaign/attempt/形式の拒否、保存bytesや来歴・journalの変更、失敗時停止、判定保留を確認した。新APIの接続テストはschema/数値処理のmockを明示し、生成関数の呼出しを禁止している。

最終は新14＋旧engineering契約10＋saved-audit6＋独立ledger計算12＋attempt-files16＋checkpoint-evidence12＝**70件pass、failure/error/skip0**。独立ledger計算12件では既存の小規模数値fixtureを実際に計算する。広い重い評価moduleは実行していない。

記録helperの初回はrepo rootのimport path不足で6 moduleの読込みに失敗し、試験本体は未実行だった。helperだけを修正し、初回ログを残して最終70件を実行。終了PID4640/exit0、約15.981秒、peak private **53411840 bytes（50.94MiB）**。UTC2026-09-21T09:56:53.988620の終了観測で空きRAM **13260976128** / C **170882428928** / D **119514677248 bytes（約111.3GiB）**。D空きは着手時と同値。

独立レビューは変更差分の読取りのみ、P0〜P3所見0、進捗ポーリング0。repository safety/diff-check pass。実dataset/evaluation生成、全campaign実行、新worktree作成はない。短時間のテスト終了時のメモリ観測であり、長期リーク不在を証明するものではない。

Windows **26200.9457**、boot **2026-09-19T03:46:06.5+09:00**、CPython **3.14.0**。最終試験前後runtime一致。Windows Updateのengineering緩和を適用し、正式OS pinを変更していない。証拠は候補worktree内 `artifacts/chunk-contract-2026-09-21` の初回/最終テストログ、resource/runtime、最終保全manifestへ保存する。

## 保存と次工程

候補branchは `codex/s4-b1-windows-engineering`。本流 **889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e** はclean。既存未commitの親policy結果書（8461 bytes / SHA-256 **443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621**）は変更せず、commitから除外した。前回attempt-files証拠27 filesのpinを再照合し、全不変を確認した。

次は新結果形式を既存attemptのIO・終了監視・audit report・journal照合へ接続する。その後にcontroller、全体予算とproducer/consumer freeze、runtime inventoryを整える。旧trialのコピー・再ラベル化・campaign加算はしない。§116の専用principal試験保留、旧保護root閉鎖、j/診断の消費済みguardを維持。principal/SAM/保護root参照、UAC/ACL変更、service/task追加、push/merge/CIなし。

本件は研究ロードマップPhase 3の異常検知・全条件実行に向けた準備工程。Phase 2の予測モデル比較やPhase 3全体の完了を追加したものではない。全dev/smoke/holdout実行、profile/score導出の独立検算、性能評価は残る。
