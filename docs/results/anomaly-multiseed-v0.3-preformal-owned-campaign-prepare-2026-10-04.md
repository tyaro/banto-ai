# 新しい架空campaignの起動前固定と所有prepare（2026-10-04）

状態: **区間0のprepareのみ成功 / journal count 0 / 共通campaign由来未認証 / 正式評価credit 0**。

## 実装と試行

既存の[metadata](../../src/banto_ai/anomaly_v03_preformal_campaign_metadata.py)、[preflight](../../src/banto_ai/anomaly_v03_preformal_campaign_preflight.py)、[controller](../../src/banto_ai/anomaly_v03_preformal_campaign_controller.py)に対し、[起動前store](../../src/banto_ai/anomaly_v03_preformal_campaign_store.py)と[直下prepare owner](../../src/banto_ai/anomaly_v03_preformal_campaign_prepare_owner.py)を追加した。storeは新しいcampaign rootのcanonical plan、空journal/pendingと、別control rootのanchor pin、count 0/head checkpoint、区間0・attempt 1のprepare intention/pinを非上書きで固定する。ownerはその３pinと対象root不存在を起動直前に再読取りし、直下CLIの元process handleからPID・作成時token・終了を観測する。`prepare`のmanifest/sidecar、22予定論理出力pin、選定source/runtime、stdoutと空stderrを保存rawに照合し、失敗なら後続を止める。

最初のclean revision `c2dedfe6da6c300b44347b963aa00bf7d6784653` では新ID `0d3648ed`・`d001`を試した。直下CLI自体はexit 0、145.781秒、peak private 332,890,112 Bでmanifest/sidecarを保存したが、ownerは[失敗receipt](../../artifacts/anomaly-v03-preformal-campaign-prepare-0d3648ed/receipt.json) 2,021 B / SHA256 `e4ca1749d8c0645f0430be2a0e5991bfaf7be419f9ac3137a1db110293938206`に`prepare_integrity`を記録して停止した。原因は正常な0 B stderrを拒否したことと、generator manifestの選定source集合を、owner/store用fileも加えたanchorの集合と完全一致で比較したこと。失敗rootと`d001` manifestは上書きせず保全し、そのcampaignのjournalはcount 0のままである。

0 B stderrをraw pinで受け、generatorの**正確な選定file集合**がanchorの同名fileに同じpinで含まれることを検査するよう修正した。controllerの実行境界ではanchorの追加source fileも実rawと再照合する。clean revision `5197805a15562b2ae5d9adbfab8ee4f60f486340`から、別ID `ba59beff`・新root `e001`を作り直した。[store CLI](../../tools/preformal_campaign_store_trial.py)の`create`と３pin指定の`verify`はexit 0、続く[owner CLI](../../tools/preformal_campaign_prepare_owner.py)もexit 0だった。

| `ba59beff`の保存証拠 | bytes | SHA256 |
| --- | ---: | --- |
| [plan](../../artifacts/anomaly-v03-preformal-campaign-ba59beff/plan.json) | 94,275 | `e1928c57a1cb25164323b8ac3ceb40cd14b10efa7bca2a31447f4de881ad8c6c` |
| [外部checkpoint](../../artifacts/anomaly-v03-preformal-campaign-control-ba59beff/checkpoint.json) | 348 | `df84e99878e70d11e72a5bbe3f0353bfc9cee41edd7963a3d8c56d23e005792b` |
| [起動前intention](../../artifacts/anomaly-v03-preformal-campaign-control-ba59beff/preflight-intention.json) | 1,598 | `f759e8fc8db67bbc3371065da7209836bf10124d9befaadd29f87baf029a8189` |
| [所有prepare receipt](../../artifacts/anomaly-v03-preformal-campaign-prepare-ba59beff/receipt.json) | 2,179 | `2291d41b4a06a1711b1e039ee60d921d91e1b6c85093e13c00b2e7d2c046a01c` |
| [外部manifest](../../artifacts/anomaly-v03-preformal-generated-pinsets-e001/pins.json) | 72,150 | `5aa66fe859a09879478e92c05c4287004aba9f89c2ad34bf766e218fda926625` |

保存rawの別実装read-only照合では、plan rootが`plan.json`＋空`journal`＋空`pending`、control rootが厳密４fileで、checkpoint `record_count=0`、`head_sha256=plan SHA256`と一致した。prelaunch claim、元handleのPID `10760`・start token、監督report、outcome/check/receiptの全参照pinも一致した。直下CLIはexit 0で回収済み、監督reportは140.327秒・peak private 331,788,288 B、stderr 0 B、runtime前後一致。manifest sidecarとregistry pin、generator sourceの正確な部分集合、22件・計131,144,120 Bの**予定出力pin**を照合した。関連53試験、repository safety、差分検査はPASS。

## 残る境界

`e001`の生成attempt rootはまだ不存在で、22 payload rawの物理生成/再読取り、６行、区間1、共通campaign journalのstarted/completed recordはない。今回のcount 0/headは起動前の状態を示す。owner receiptは**prepare直下CLI**の終了証拠であり、将来の生成子孫や全工程予算を証明しない。`next_stage_authorized=false`、`campaign_coherence_authenticated=false`、`resume_authorized=false`、`actual_registered_observations_read=false`、`formal_permission=false`、`campaign_evaluations_credited=0`を維持する。既存の`c001/c011`をこの新anchorに後付けしない。

次は`e001`のmanifest pinを含む`started` recordをjournalへ非上書きで保存し、**外部count/headを更新して固定した後**に、正確な`run-budget` requestを起動前保存するowner transactionを接続する。異常終了時の子孫回収と内側invocationへのanchor pin伝達が未実装の間、共通producer campaign認証へ昇格しない。S4未採択、旧gate `s4_acceptance_not_frozen`を維持し、未使用の実登録holdoutはS4採択後に限る。
