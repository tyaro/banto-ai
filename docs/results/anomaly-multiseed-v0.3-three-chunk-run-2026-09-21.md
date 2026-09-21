# v0.3 準備済みrunの3区間連続運転

2026-09-21 JST。対象はclean `C:/Users/TKent/.codex/worktrees/v03p/banto-ai`、実装 **c01d1c978f78bab51391392d56cdcb7aab5afaab**、出力`artifacts/v03-runs/r1`。

**最終結果: 3区間・18評価すべて成功。** 実CLIの1回の呼出しで生成、保存、再計算照合、別processのledger監査、journal確定まで連続完走した。約42分43秒で明示上限に達し、`yielded`として正常に閉鎖した。次の未完了区間は3。全120区間の完了や正式受入は追加しない。以下の開始・中間保存点は実行中に保存した履歴である。

## 開始時の保存点

ユーザーの「お願いします」に基づき、準備済みの初期closed記録から`continue --max-chunks 3`を開始した。登録dev seed2486912926863618161のlayout0〜2、各core/quality-stress×3候補＝最大18評価。同じrunの完了済み区間はまだなく、旧trialを転用しない。

外部prepared hashは`be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7`、開始closedは`run/control/000000/closed.json` / hash`85a6163034c5392ce1ef78f4cbaa6da0faf9c06a66faae03c8c0f8df0c8ebf39`。全体48時間/32GiBの候補上限と区間ごとの所有process監視を維持する。

実行wrapperは候補worktreeの`artifacts/three-chunk-run-2026-09-21/run.py`、同folderの`request.json`に実argv/開始runtime/資源を保存した。CLIのstdout/stderrは外部ファイルへ保持し、診断は60秒間隔でcontroller private、空きRAM/disk、確定済みjournalの最新状態を記録する。診断表示だけを成功判定にせず、終了後のclosed pinと成果物を照合する。未終了processや未閉鎖呼出しの自動再起動は行わない。

開始時Windows26200.9457/CPython3.14.0/exe・DLL hashは前回と同じ。事前空きRAM13133750272/C174109761536/D119512887296 bytes。実行中のsourceは編集しない。保護root/principal、UAC/ACL/service/task、本流や過去trialに変更なし。

開始保存点は6aff0c1。この時点では実行中で、成功判定はまだ行っていなかった。

## 中間保存点

経過約30分でchunk0/1（12評価）のverified記録が揃い、chunk2へ自動継続した。生成workerはそれぞれ554.821秒/343572480 bytes、555.890秒/344481792 bytesで正常終了確認。controllerは照合中にpeak218877952 bytesとなり、chunk2開始時にはprivate86491136 bytesへ低下した。

verified sequence3/6のreceiptを外部`first-verified-receipt.json` / `second-verified-receipt.json`へ保持した。descriptor hashはseq3=`333de70acc1f3a94c9393e8c2cbd661bacfeeef021bcec7243c389d940f1676e`、seq6=`64620177c2dde14ff912d1f140093654c12637a336ea73e08b07751d17e892de`。中間保存点は3d4f91c。この時点では同じinvocationが稼働中だったため、これらのreceiptは再開用closed pinではない。

## 最終結果と再開位置

実CLIはexit0、`status=yielded` / `stop_reason=null` / `chunks_verified_in_invocation=3` / `next_unverified_chunk=3`。各区間6 success、failed/inconclusive/not_started各0。登録dev seed2486912926863618161のlayout0/1/2、core/quality-stress×C0/C1/C2を新規生成した。journalは各区間のrunning→saved_pending_verification→verified_complete、計9記録。producer/auditとfresh inspectionの全所有processはexit0で終了確認済み、停止理由・観測エラーなし。

| chunk / layout | producer秒 | producer peak private bytes | audit秒 | audit peak private bytes | payload bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 / 0 | 554.821 | 343572480 | 92.437 | 189153280 | 132575923 |
| 1 / 1 | 555.890 | 344481792 | 94.094 | 190722048 | 132586082 |
| 2 / 2 | 546.841 | 349065216 | 90.569 | 195768320 | 132608282 |

各payloadは41 files、別process監査はすべて`ledger_checks_passed`。seq9/chunk2のdescriptor hashは`fa8067004c3959a7c79de9648c21d0cd63a94d8531aeef78b4470a4598f75244`。独立監査範囲は`stored_score_ledgers_only`であり、profile/score導出・bootstrap等の独立検算ではない。

最新の外部closed pinは **`C:/Users/TKent/.codex/worktrees/v03p/banto-ai/artifacts/v03-runs/r1/run/control/000001/closed.json`**、raw SHA-256 **`bfa729b447de0ce57d32439acb65ce025e718e82e7c40ebd55dda5d316d9c2da`**。prepared pinは開始時から不変。次回は同じclean c01d1c9から、この最新pinと明示した区間上限でcontinueする。古い初期closedや中間receiptから起動しない。

## 終了後の照合と資源

累積活動時間2563.286712秒、wrapperの事前処理を含む実時間2563.527295秒。fresh inspectionは53.487秒/peak39174144 bytes。run全体は**205 files/399625685 logical bytes（約381.1MiB）**で、hardlinkの別名もそれぞれ数える。CLIの`output_bytes_before_closed_state=399148838`は予算対象のrun subrootの値で、全rootの集計とは範囲が異なる。初期prepareの7 files/749075 bytesは不変。

controller peak private226635776 bytes（約216.1MiB）、終了時82321408 bytes（約78.5MiB）。worker最大は349065216 bytes（約332.9MiB）。60秒間隔の42診断標本で空きRAM最小12900720640 bytes（約12.0GiB）、診断エラーなし・診断thread終了済み。区間確定後のcontroller privateは約83→82→78.5MiBへ低下した。今回の観測中に増え続ける挙動は見られないが、長期リーク不在を証明する試験ではない。private値は直接所有するprocessの値で、Git等を含むprocess treeの合計ではない。

実運転終了UTC2026-09-21T14:10:40.410982+00:00、空きRAM13235781632/C173706485760/D119512846336 bytes（D約111.3GiB）。Windows11 Pro25H2/AMD64/26200.9457/local NTFS、CPython3.14.0/MSC1944/source v3.14.0:ebf955dは開始・終了・各workerで一致した。exe SHA-256 `467014615a5255aca450ae88100dd2caf887da87657f00e3c2171ec44a685aec`、DLL SHA-256 `f1722bd369d79fecbc85f3ed2790c30c330b9413fd74332f95b086e60dfacc2a`。Windows Updateのengineering実値記録を継続し、旧正式pinは不変。

終了後は`open_run`と`inspect_attempt`でclosed/request/inspection、journal、3 descriptor、保存auditのhash、marker/payload inventoryを照合し、205 filesを外部`evidence.json`へpinした。collectorは62.005秒/peak185434112 bytes、数値計算は再実行していない。証拠は候補worktreeの`artifacts/three-chunk-run-2026-09-21`、最終保存点は`savepoint-evidence.json`に記録する。前回campaign-launcherのmanifest（5681 bytes/SHA-256 `aa90c244104a2d83e444407f7f38914ac2e2d80c23587154ca3bf9d9877ab55f`）と記載11ファイルを保全する。

## 次の工程

同じengineering runで残り**117区間/702評価**。今回の連続運転と資源実測を使い、次回の明示上限を決めて最新closedから進める。全体48時間/32GiBは区間境界での協調停止による候補予算で、process treeの強制上限ではない。再開時には過去verifiedの再照合時間が加わり、seed/layout差や再試行の費用も未確定。全120の自動起動は行わない。

`campaign_evaluations_credited=0`、`formal_permission=false`、完全runtime inventory/独立S6は未完了。全dev/smoke/holdout、性能評価、Phase 2/3全体の完了を今回の成功へ読み替えない。実装変更・追加agent・数値回帰の再実行なし。本流889cfc3/clean、既存dirty文書、過去trialは保持。保護root/principal参照、UAC/ACL/service/task変更、push/merge/CIなし。
