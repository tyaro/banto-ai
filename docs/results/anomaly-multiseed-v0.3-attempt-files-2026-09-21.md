# attempt実ファイル照合と最初の6件の検算接続

2026-09-21 JST。実装savepoint **072773e181a17135a34de5c662b377281352f568**。
[仕様・CLI手順](../anomaly-v03-independent-audit-and-checkpoints.md#attemptの実ファイルを読取り照合する)。

## 結果

`attempt-files` を追加し、外部に保持したjournal/descriptor hashから固定位置のdescriptor・4役割の証拠を読み、実際のサイズ/hashと照合できるようにした。markerがある場合は既存storage readerでpayload inventoryも照合する。別の場所のdescriptorから代用せず、未記録の証拠、欠落・変更・上限超過、reparseや通常ファイルのhardlink別名を拒否する。失敗・中断の不足証拠は従来どおり保持する。

`attempt-audit` は既存の6件独立consumerへ接続し、保存score以降の再検算、source来歴、manifest/journal outcome、runtime、producer監視、過去auditと再検算の一致、audit監視の出力・正常終了・上限・呼出し先を照合する。過去consumerと今回verifierは別revision/実runtimeとして保持する。**verifiedのchunk 0だけを対象**にし、chunk 1以降やsmokeへ旧6件契約を拡張していない。

新配置の `producer-control/supervision.json` を読めるよう、既存saved-auditへその固定siblingだけを許可する明示引数を追加した。未指定時の従来control位置は不変。既存preflightと新attemptの監視/本文照合部分を共用した。読取り後はcontrol、payload、source、journalを再照合する。

file検査だけでは `evidence_body_bindings_verified/saved_ledgers_revalidated/source_checkouts_verified=false`。独立検算が成功した場合だけそれらをtrueにする。両コマンドともcampaign credit=0、execution/resume/campaign_completed/formal_permission=false。読取り時の通常path確認は、将来の不変性や敵対的な同時writerへの保証ではない。

## 検証

初回47件pass/11.817秒。明示controlと従来既定位置の互換性、検算後の同サイズpayload変更の検出を補足し、最終は新規attempt-files16＋descriptor15＋preflight12＋saved-audit6の **49件pass/12.266秒、failure/error/skip0**。repository safety/diff-check pass。独立P0〜P3所見0、進捗ポーリング0。

新しいaudit接続のテストはsource capture/数値処理のmockを明示し、既存readerへの引数と結果照合、本文の再hashだけでは通らない不一致、実ファイルの再確認を検証した。実6件の再計算成功を今回追加したものではない。広い数値評価module、専用principal/同時writer試験は実行していない。

commit済み実装で、候補内 `artifacts/attempt-files-2026-09-21` に小規模な保存済み検証待ちfixtureを3組作り、実CLIを確認した。架空source/評価宣言のfixtureであり、登録datasetや実evaluationは生成していない。

| 実CLI確認 | PID | 終了コード | 秒 | peak private bytes |
| --- | ---: | ---: | ---: | ---: |
| 固定実配置とmarker/payloadの照合 | 17308 | 0 | 0.412 | 22622208 |
| 未記録audit監視の拒否 | 26376 | 2（期待値） | 0.309 | 22245376 |
| 保存後payload変更の拒否 | 31408 | 2（期待値） | 0.410 | 21999616 |
| 検証待ち状態のaudit要求拒否 | 26080 | 2（期待値） | 0.311 | 22196224 |

合計1.441秒、最大21.57MiB。所有processを各60秒/256MiB/出力2MiBで監視し、全終了確認、停止理由なし。入力16 files不変、前回attempt-descriptor証拠18 files不変。登録dataset生成0/evaluation0/実演のledger再検算0。新worktreeなし。

証拠26 files/332098 bytes（最終manifest除く）。`demo-evidence.json` は4633 bytes、SHA-256 **db718e6da385f1b5a3d9019d2ca65dc1e39c9c86354b8d95e5fcf57c7f1b263c**。

## 資源と保全

UTC2026-09-21T09:34:30の実演後、空きRAM13215277056/C170894483456/D119515004928 bytes（D約111.3GiB）。実演前後D空きは同値。前回記録以降にbootは **2026-09-19T03:46:06.5+09:00**、Windowsは **26200.9457** へ変化した。CPython3.14.0とexe/DLL hashは従来どおり。今回の実演前後runtimeは一致。Windows Updateのengineering緩和を適用して実値を記録し、旧正式pinは変更していない。短時間のprocess終了確認であり、長期リーク不在は未評価。

本流 **889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e** はclean。既存親policy結果書8461 bytes/SHA-256 **443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621** の未commit変更は保全し、今回commitから除外した。

§116の専用principal試験保留、旧保護root閉鎖、j/診断の消費済みguardを維持。principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。

## 次の工程

登録inventoryの1 chunkを引数として扱う新scopeの結果契約を整え、旧6件用契約を変更せずreader/consumerを全120 chunksへ接続する。対象選択、source/runtime、6 slot、結果/監視の対応を小規模fixtureで検証してから実行側を接続する。controller、予算・source/consumer freeze、runtime inventory、profile/score導出の独立検算は残件。新配置の実6件、全dev/smoke/holdoutの長時間実行は未実施。
