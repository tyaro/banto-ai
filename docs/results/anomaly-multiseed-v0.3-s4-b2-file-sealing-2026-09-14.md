# S4-B2 file権限固定と保持世代の実機結果

2026-09-14。基準c73a602896f6eeef2b63e109f6c10c7760c5515a。
実装・native実行savepoint **48f701f51fdf3d8e4312dc097b9a6d8bc18066f8**。

**新規19＋既存124＝143 tests pass。実Windowsの新規2 filesにfrozen DACLを設定し、
同一ID/bytes・固定後SD・保持権限を読み戻して、全tracked handleとworkerの終了を確認した。**
[設計・試行仕様・公式API資料](../anomaly-v03-file-sealing-design.md)を参照。

## 接続と試験

writerの確定close後、payloadは0x160081、markerは0x170081で取得する。
WRITE_DACとmarker DELETEを固定前に取得し、データ書込み用の権限は持たせない。
全対象の元pin/bytes/private SDと実権限が一致してから、各対象を再検査し同handleでDACLを変更する。
固定後は元ID/bytes、frozen ACE列、owner/group/integrity/mandatory policy不変と実GrantedAccessを確認する。

全対象の検査後、親borrowと子handleがliveの間だけ同期continuationを呼ぶ。
今回は保持rootのID/SD不変を確認する観測callbackで、renameは実行していない。
戻り値/guard確認後に新世代を逆順closeする。閉じた旧writer slotsは再利用・復活させない。
動的slot追加や恒久的な所有移管を実装したものではない。

SetSecurityInfoはDWORD0だけを成功とし、NULL/defaulted DACLを拒否する。
descriptor作成・DACL抽出・設定後のguard、1回のLocalFree、元例外と後発資源停止の保持を追加した。
初期対象検査・設定前再確認・変更応答喪失・不正返却・誤SD/ID/bytes・親停止・再入・
continuation失敗・close応答喪失を模擬した。close失敗後のscenario passも拒否する。

部品段階52件pass/0.075秒の後、記録済み143件pass/0.168秒。
failure/error/skip/expected failure/unexpected successはすべて0。
initial-checks.jsonlを最終根拠とする。その後コード変更はなく、同じ試験の再実行は省略した。
本体とscenario/監視/仕様の独立レビューは各新規P0〜P3=0、read-only、進捗ポーリングなし。
最終source等23 filesを記録hashと実行Git blobのraw bytesへ照合した。
repository safety・staged diff-check・監視PowerShell構文確認pass。

## 限定実機結果

clean HEADと監視hashを固定して、新規artifacts/file-sealing-2026-09-14/attempt-1だけで実行した。

| 項目 | 結果 |
| --- | --- |
| 元writer実権限 | 2個とも0x12019f |
| 固定用file実権限 | facts.json=0x160081、marker-pending.json=0x170081。固定前後とも一致 |
| frozen file DACL | protected、Everyone deny0x10116、元private allow3個＋Restricted Code read allow。2 filesの読戻し一致 |
| 不変確認 | 元volume/file ID/hash/exact bytes、owner/group/integrity/policy。保持rootのID/SDも不変 |
| continuation | 親と新世代を保持した状態で観測callback成功、全新世代close後にscenario pass |
| 所有終了 | source13＋sink12＋new files2＝27 tracked handles、照会token2個close。worker exit0 |
| 原データ・証跡 | source exact2 files計460 bytes、prepare.json2880 bytes。終了後inventory/raw/hash一致 |
| 時間 | 外側0.555秒、worker最後の観測0.084秒 |
| メモリ観測 | 4境界、private最大18.05MiB、working/peak working25.83MiB。資源停止なし |
| 標準エラー | 0 bytes |

今回の最大2回枠は1回目成功で終了し、未使用枠は繰り越さない。旧batch/B1枠の再開なし。
journalはprepare=unknown/model_status=stopped、teardown=succeeded、commit_observation=not_started。
2 filesの局所的な権限固定であり、seal_payloadを含む全公開工程の成功として記録しない。

DACLを変えても既取得のWRITE_DAC/DELETE権限は保持されている。
独立tokenによるwrite/delete拒否、directory/rootのDACL固定、相対rename/.complete、native失敗/競合は未試験。
rootはprivateのままで、親経由delete等を含む全保護は未完成。owner/adminによる意図的DACL変更への防御ではない。
今回は変更後のfile ID/hash/正規化SDを報告に含めるが、外部認証された実行証明にはしない。

外側1秒監視は短時間終了のためsamples0。4境界の値は全期間最大メモリや長期リーク不在を証明しない。
Start-Process内部の起動後返却喪失、hard時間上限、電源断耐久性は引き続き未保証。

## 保存記録・資源・残件

新規ignored root artifacts/file-sealing-2026-09-14/へ保存した。

| 記録 | bytes | SHA-256 |
| --- | ---: | --- |
| initial-checks.jsonl | 103693 | 3f78ca2784357f6868a644b65b62fd4879b5f8636b29ae9b47cd9907d44f3b9d |
| attempt-1/probe-result.json | 16845 | 9accf1f1aad1051b225faa2769a2f52776e52f0136e471990e0ff69879d76207 |
| attempt-1/private-evidence/prepare.json | 2880 | 19ce81cbdd67af9e4146fde2424d1124373fbcce9d2f422b49f5c11ae31def1d |
| attempt-1.supervision.json | 520 | 4a6fc09ab2c6a21e11937e3fbceb3db61068647654192d8e441e6f7dce4d4c9c |
| resources-final.json | 224 | e91c3de76e7a24712313b4ba8e1bb2992ab511783fb62a177277693612645b8a |
| savepoint-evidence.json | 8005 | e9809b687bcf368f13720e9b0bdba6bdd10f3e1ee3da872ec862294445a92edb |

manifest以外15記録の論理bytesは166713。disk占有量ではない。
前回reader manifestに載る全artifact hashも不変を照合した。

開始UTC08:38:48 RAM7.56GiB/C119.96GiB/D87.07GiBは取得結果から転記。
実機前保存08:49:04と最終保存08:49:37は、ともにRAM7.83GiB/C119.95GiB/D91.03GiB。
D空きの増加原因は未調査で、本作業やリーク不在へ帰属させない。
build26200.9445、boot2026-09-09T10:43:08.5000000+09:00を記録し、正式OS pinは変更していない。
worker・短い検証processは終了。常駐処理を追加していない。

次はstage/root directoryの取得権限とDACL固定、保持source/parentを使う相対renameを具体化する。
子fileを閉じてからのdirectory rename、後続phase証跡、独立token/実故障/競合の受入は残る。
formal_permission=false、execution_authenticated=false、acceptance_status=not_completedを維持する。
正式OS整合、VM digest、runtime closure/consumer、S4受入は未完了。
src/科学config/schema/registry/正式pin、本流889cfc3は不変。旧Linux CIへ件数加算なし。
push/merge/CI、新runtime/共有環境/別project/旧failure rootsへの操作なし。
