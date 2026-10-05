# v0.3 保存controlのdisk読取りを含む50,000 draw公開予算（2026-10-05）

状態: **架空controlの予算内読取り・再照合が成功 / S4未採択 / 正式許可なし**。成功sourceはclean `d997020f6a399ff32f5156491aac191f3bc7e167`、初版は `a7522578eeabbc6d193854f0a614ce191f9bb551`。Windows 11 Pro 26H2/build26300/UBR9457・CPython3.14.0・local NTFSの候補環境で実測した。追加agentなし、gate `s4_acceptance_not_frozen`、正式credit0、登録holdout40 seed未読を維持する。

## 接続範囲と検証

[`run_saved_control_files`](../../src/banto_ai/anomaly_v03_preformal_saved_row_document_budget.py)は、[固定名control reader](../../src/banto_ai/anomaly_v03_saved_control_file_reader.py)のdisk読取りを、既存の保存行projection→50,000 draw→別process算術監査→文書・slice・件数監査→owned writer→終了後fresh reader→disk再照合と同じsampler内へ接続する。旧caller-supplied bytes入口は維持した。既存の数値fixtureの8 draw上限、共有1,200秒・parent512 MiB・root96 MiB・128 entries・depth5、資源下限、control input256 MiB、budget receipt64 KiBは緩めていない。

callerが独立して保持するpinset pinを固定し、canonical indexの480区間・各10名・個別bytes・全bytesを検証してからcontrolを読む。物理pathは `controls/{index:03d}/{fixed-name}.json` から導出し、descriptorのpathを読取り先として使わない。欠落・重複位置・迂回path・余分なファイル・非regular/hardlink・サイズ超過・raw/index改変を拒否する。終了前の再読取りは、初回と同じ外部pinとraw indexに照合し、再集約せずdiskの全pinを再確認する。

これは**保存readerが出力した架空controlの読取り**である。実保存readerによる観測payload読取り、producer生成、raw観測→profile/score/ledger再導出、共通campaign実行由来は検証しない。実データ作業は保存済み合成dev8/smoke2のengineering読取り・記述まで、実設備・顧客データは対象外。

初版の新reader・既存保存行・publication関連41試験は69.070秒でpass。checkpoint修正後の焦点16試験は38.866秒でpass。後者は全966 control checkpointのsample/probe継続とphase履歴の上限、反復phase中のlatched stopも検証する。これらは別runで合算しない。compile、repository safety、diff checkもpass。凍結計画68,889 B／`e7c761f83d4657f39e1b5709fb022ad887a43f166327ff3258a36757d20eadec`、registry10,679 B／`61af9100f8daa96d8200a0d2ab23aa7209cab52f0dd5543f9e35797de7332a70`は変更なし。

## 初回failedの保全と修正

初回root `artifacts/anomaly-v03-preformal-saved-row-document-budget/trial-20261005-04`、helper `artifacts/anomaly-v03-saved-control-budget-20261005-a1`。4 workerはexit0・回収、disk再照合も終了したが、各区間のcheckpointをphase履歴へ繰り返し記録したbudget receiptを64 KiB以内に保存できず、`saved_row_document_budget_close_failed`／`ValueError` となった。resultのwall273.869秒、`same_budget_control_disk_to_fresh_reader_measured=false`。完成したpublicationは保持するが、共有予算passには扱わない。resource-budgetファイルは保存されていない。

初回result34,379 B／`7a2b2f2e47a6ad2b42be6a8adafe00de4568a0e280c6f5f12b8f33f580772bfd`。失敗helper216 B／`7b9dd7a65ea144174fee50fc3db7b1719c24ced99fcd4272decfa5d8d10671c0`。別stdlib手順で42 raw、元revisionの39選択Git source、analysis PID37780／audit31996／writer30208／reader18936の終了記録を照合した。`failed-postcheck.py`3,279 B／`c3c3bdb5a4cbc87393f89fc8b6ee90cc27740ffe39ea94285a632c5cc8eb49fa`、`failed-postcheck.json`8,494 B／`eb7a02c1a890f38902f98a7015eee7763602f64899d3211ccc75d596071cb5c7`。budget passは未確認のまま保持する。

修正では全checkpointの `_observe` とlatched stop確認を維持し、同じcontrol phaseの反復をcountへ集約する。phase遷移とそれ以外のcheckpoint履歴、first/last/extrema、sampler sample数、4 role終了、出力pinは保持する。新rootで再実行した。旧rootやcontrol rawは上書きしない。

## 成功した新root

pipeline `artifacts/anomaly-v03-preformal-saved-row-document-budget/trial-20261005-05`、helper `artifacts/anomaly-v03-saved-control-budget-20261005-a2`。入力control rootは以前の `artifacts/anomaly-v03-saved-row-projection-20261005-a1`。外部index690,985 B／`67032c5e61102b2063ece1674e4445d0b2811953132a6074b4ff93adb5ae2ab5`、control4,800 files／129,026,491 B、index込み129,717,476 Bを予算内で読んだ。期待pinの準備とhelper importは予算外、control rawの事前ロードはしていない。fixture構築source `a9f1882`、内部の歴史的source宣言 `aaaa…`、今回の実source `d997020` は区別する。

| 項目 | 結果 |
|---|---|
| 共有wall | **280.645136秒 / 1,200秒**、stopなし、sampler終了確認 |
| control disk load / reread | 1.686→5.721秒、274.334→278.952秒、各483 checkpoint |
| sampler / receipt | 2,007 samples、control phase履歴各1行、budget receipt6,745 B／64 KiB以内 |
| analysis | PID29976、61.939秒、private peak126,771,200 B、exit0・回収 |
| arithmetic audit | PID25492、137.171秒、private peak29,601,792 B、exit0・回収 |
| writer / fresh reader | PID20908／28308、13.861秒／6.592秒、両exit0・回収、別creation token |
| parent / root | private peak228,536,320 B、root最大9,567,214 B・44 entries・depth2 |
| 最小余裕 | commit14,561,648,640 B、RAM14,040,678,400 B、disk384,726,487,040 B |
| 数値・文書 | 40 cluster／50,000 draw、9主表／117主推定／72paired推定／180 gate、1,233 slice／2,835 diagnostic rows／9診断表 |
| coverage | 2,879 success／1 inconclusive、区間479のfailed attempt1／latest2を保持、正式credit0 |

外部control bytesは新rootのdirectory測定に含めない。外部inputの固定256 MiB上限で全bytesを検証し、読取り時間・parentメモリ・system余裕を同じsamplerで測る。新rootには最後のresult・budget分128 KiB／2 entriesを予約する。正式同形容量2倍の証明にはしない。

## 保存pinと別照合

| pipeline内の相対名 | bytes | SHA-256 |
|---|---:|---|
| result.json | 34568 | `61e8acf7790f9201b07534e535b3d95407e73bbadeb321e403c2ba1505fcb577` |
| resource-budget.json | 6745 | `69500ce45e2c844bbc68a53ed345662c3bf6b91b869c88674152f6722f1aa659` |
| control-files.json | 934 | `00b4a7cd0f403dc1012f1968e60ac43f69e1d38d58de339cf5933bdb9897f907` |
| projection.json | 554130 | `865feff2e1e832ecb80b4a289c9d275dedec88fc6649fdbcce7b67bff3bb7809` |
| input.json | 155375 | `5b89e7c34077118b60f0ee1bae36340efa82f4e521b8fd82d8001239029e8327` |
| document.json | 121001 | `b0d7587ad1e3877f8c417f35b2b81b5675544ba6931206cf78b083cc5e4c840d` |
| slices.json | 1928882 | `1b2ba10804cf4cdbd8c788e1a9acb34ad51295da2e7ed266da3233e099e76e13` |
| writer/result.json | 7821 | `edfe0a9a3b97c47fda57957edef80bf4e3d3792122961be85d842c65885298c5` |
| reader/result.json | 7728 | `e5a26fef1dd4def720a76f2be3942e5901bb0a89dd763a0ca0003be19aae758a` |
| published/.complete | 1281 | `eb9721a3d1b44729be6ff718f3f61c9040e1bb160aad2e6b60f4908ff90541ce` |

新helper: `run.py`4,753 B／`b1d830caf0d8617b705db0020340a60836405665c672cdcbf63e4d4aa280b05f`、`request.json`1,179 B／`db5fd5655bc5d2f14e20be1833e7f98cbb99c8d14d80c1355bb52dff64883f98`、`capacity-preflight.json`277 B／`e47502ecbb20323e6882c55181e285cdf83606679b30afeb5878422da50dd10d`、`execution.json`524 B／`04b2a741cfcb23c31e8651dd61094929db19ec4b72c8ce7ee09406c9e7a0cca1`、`postcheck.py`22,698 B／`226bed61dba316e9ba00d70e895ddff6afdd7806c9553a01dd249dc8955f0c57`、`postcheck.json`844,050 B／`a5da37605b4d31f843bedcd7f2776e46850cbcaa162b7b6d22b5ded008465c0d`。

別stdlib手順がproduct moduleをimportせず、4,841 rawのpin、全control count/slice集約、4入力、数値と文書対応、公開5 payload/marker、4終了receipt、39選択sourceのdisk/Git一致、966 checkpoint count・phase順・receipt上限を再照合してpass。50,000 drawの独立算術はaudit workerの証拠へ結び、このpostcheckでdrawを再計算しない。raw観測由来の独立検証ではない。ignored local証拠はGit pushの対象外、source・試験・本文を保存する。

## 次に残るもの

実producerと実保存readerの観測payload・latest attempt・由来検証を共通予算へ結ぶ工程、raw観測の独立再導出、正式同形のsmoke容量2倍が残る。全480区間の新規架空生成完走を自動追加の必須条件にはしない。[S4範囲案 v3](../anomaly-v03-s4-acceptance-scope-draft-v3.md)に沿って固定入力で経路と失敗拒否を結び、最終dev8/smoke2と独立受入へ進める。

bare PATH Git・限定supervisorのままで、専用Git Job、業務worker/子孫回収、stdlib・拡張/DLL/CRT・外部programの実ロード在庫と最終source/runtime closureは未接続。26H2・保証A/B・runner同定等の改訂契約採択、最終revisionのLinux/Windows・独立受入も未了。先行 `d04d723` の [CI 37315729198](https://github.com/tyaro/banto-ai/actions/runs/37315729198) は本証拠記録時に両minorが実行中。最新で保存・再検証済みの全job成功は `a7fc363` の [CI 37311338257](https://github.com/tyaro/banto-ai/actions/runs/37311338257)。今回codeのCI成功へ読み替えず、S4採択・最終受入前にS5を開始しない。
