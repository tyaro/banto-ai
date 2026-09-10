# S4-B1 初期化失敗地点で bcrypt.dll 候補を取得

状態: **限定診断1回完了 / DLL候補を確認 / 意図した停止・終了処理・証跡保存確認済み / child E2E未達**。

## 今回の実行

ユーザーの「お願いします」を[初期化失敗地点計画](anomaly-multiseed-v0.3-s4-b1-init-failure-plan-2026-09-10.md)の1回への了承として、
cleanなa76439b（実装0b19750）で新規fixture1個を実行した。
init-failure-once.pyは2736 bytes、SHA-256
2de5eb72f155257271d3c7aa638abc2373713dbe6e8a9e6010bbc0e72fc408c2を起動前に照合した。runは1回、自動再試行なし。

初期reportまで2.175秒。driver/observerはfailed、primary=init_failure_observed_stop、secondaryなし、resource_stop=false。
このfailedは観測後に通常Continueを行わず意図して停止した結果であり、collectorの取得失敗ではない。
contextはcompleted/status confirmed、Set readback verified。起動要求0x40e、creation created、ownership transferred。

通常19 events/Continue18。slot17のbootstrapを照合して1回継続し、slot18の初期threadのsingle-stepで停止。
bcrypt.dllはslot16のconfirmed LOADと対応した。取得値は次のとおり。

| 項目 | 実測 |
| --- | --- |
| 停止命令 | ntdll RVA e86e |
| 例外 | first chance 80000004、flags0、chained null、parameters0 |
| 初期process/thread | CREATEと一致 |
| R14D / R12B | C0000142 / 0 |
| 対象DLL候補 | bcrypt.dll、LOAD slot16 |
| SizeOfImage | 172032 bytes |
| callback RVA | 11140 |
| loader flags | 2ca2ec |
| DR6 arm / hit | 0 / ffff0ff1 |
| DR7 arm / hit | 1 / 401 |

flagsは失敗bit100000を書き込む命令の実行前の値で、当該bitは未設定。
callbackのFALSEだけでなく例外経路もこの地点へ合流するため、callback実行や特定APIの失敗、根本原因を断定しない。
今回の観測範囲は初期threadに限る。

bootstrapはGet1/RPM3回75 bytes、contextはGet3/Set1/RPM2回957 bytes（code845＋entry112）。
合計Get4/Set1/RPM5回1032 bytes。code/caller/pending/初期thread/load寿命と各register条件を照合した。

## 終了処理と証跡

hitは通常Continueせずowned terminationを要求し、pendingを解放した。
drain4件（thread exit3/process exit1、全code1）をContinueし、process signal/ownership解消を確認。
teardown pass/failure_count0、所有process/thread handles closed、driver teardown failures0。
自然EXITは未観測。drainのcode1を自然な障害理由とは扱わない。

private117499 bytes、SHA-256
494901a58011faa315f03acd029bfe0d3cacb8f91077f8df1c8191eb03d2621a。
write/flush confirmed、evidence file closed。有界held-file read1回でhash、通常/drainの全events、
bootstrap CONTEXT/code/caller、3回のdebug CONTEXT、hit CONTEXT/entry112、LOAD対応、launch/stopを照合した。
reader close済み、inflight false、未確定buffer領域は全zero。
fixtureは保持方針で存在はunverified、cleanup/repair/再測定なし。

公開要約はinit-failure-native-summary.jsonl、readbackはinit-failure-native-readback.jsonへ保存。
raw/private path/絶対addressを公開要約へ転記していない。

## 資源と参照DLL

同run preflightは24 sources/262701 bytes、verified、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
memory167 samples、親＋child peak commit26488832 bytes（25.26 MiB）、peak working36392960 bytes（34.71 MiB）。
実行前空きRAM7.71 GiB、C107.91/D75.36 GiB。最終bootは2026-09-09T10:43:08.5000000+09:00。
Windows Update後のUBRは記録し、承認済みの固定条件緩和を維持する。単発値からリーク有無は未判定。他project操作なし。

現在のSystem32/bcrypt.dllを、証跡のconfirmed LOADのname/volume/file IDと照合して同一handleで1回有界readした。
前後のidentity/size等の不変、全handle closeを確認した。file183376 bytes、SizeOfImage172032、
SHA-256 b5691584e857caf0c6c590dda13779966b383d66be3c87d5b3cbbc2f5005495b。
現在fileとの対応であり、過去のloaded code bytesとの一致証明ではない。

bcrypt-reference-entry.jsonへ参照bytesとPE metadataを保存し、以後はそのcacheのみで解析した。
entrypoint RVA11140、code範囲11140..1131b、475 bytes/hash7ad0379a750d6a424bdae27d8d4800b5562e59bc73a59547915a86806990e75a。
内部関数b1c0..b2b7は247 bytes/hash4deae110e20cec3932557987e6fcc1814cad99931cc2d02ac0499cf192f3260b。
PE import tableと固定命令列をbcrypt-initialization-static.jsonへ保存。PDB/download追加なし。
参照RSDSはbcrypt.pdb / GUID5F1077ED8D3ABC83AD7D378F94EA4190 / age1だが、symbol lookupはしていない。

次は[DLL内部の失敗値取得計画](anomaly-multiseed-v0.3-s4-b1-bcrypt-failure-plan-2026-09-10.md)で具体的な候補値を調べる。
全acceptance gate no、本流統合/formal/B2/publisherは未実施。

作業後の空きRAM8.55 GiB、C107.98/D75.36 GiB。本流889cfc3 clean、追加nativeなし。
