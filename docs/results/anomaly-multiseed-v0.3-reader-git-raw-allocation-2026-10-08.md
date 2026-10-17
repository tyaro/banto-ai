# Reader call inventoryの明示失敗raw上限

2026-10-08 JST。code `37b7feb400c754c5030b3164f020390cf36572d7`、formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。

## 接続した範囲

ReaderGitParent.createのopt-in `pipe_raw_limits` はhead/status/source_blobごとのcaller明示raw maxima。元source pins/limitsを検証・shared/source IOより先に保持/copyし、全callのexpected output pinとraw inventoryへ保持copyを固定する。defaultは既存generic maximaを維持。新module0/名前30source/phase32要求/予定64Jobは維持するが完全runtime閉包ではない。

closed operation/raw名、positive integer/bool拒否、既存MAX_OUTPUT/MAX_STDERR/MAX_RECEIPT/archive上限以内、32KiB以下のallocation、空outerでもreserve後に収まる必要条件を検証する。正常source pinはfailed stdout capを生成する入力ではなく、caller capに正常bytesと最後の検知byteが収まることだけを確認する。headも41B payloadに検知byteを足せないcapを拒否する。generic1MiB failure stdout等の不適合はchannel/root/clock作成前に拒否。

exact64call inventoryのpin/readbackへlimitsを結び、元GitSinkAdmissionが同じcall/raw maximaとactual root bytes/entriesを再照合する。テストのsource allocation例はstdout128KiB/stderr16KiB/receipt16KiB/partial-archive64KiB、合計229376B。これは明示的な保存枠の部品であり、全parent-child並行control/partial archive/global/memory/全経路wallの容量証明ではない。

## 新焦点と原失敗

raw `artifacts/preformal-reader-git-raw-allocation-20261008-prep/`。

- 初回7件6pass/error1/fail0、1.5029002秒。参照fixture osにfstat/fsyncがないため実FileIOケースがsink途中で停止。原log保持。
- fixtureのその実fileケースだけ訂正し、失敗1件のみ0.3292495秒pass/fail0/error0/skip0。pass6/旧suite反復0。7distinct/最終unique7、最終source単一7success runではない。
- 各36source/science pin前後不変、test以外35pin両component一致、先行entry共通33pin不変。変更2file safety findings0、clean code-save36working/Git一致。
- exact64call/pin、mutable source/limitsのIO前copy、generic上限/closed不正値/sentinel拒否、実512KiB保持file＋32KiB control fileのsnapshot計上、overfillで原raw保全・新sink/Job前拒否を確認。保持fileは未検証placeholderで、実archiveや正式control witnessへ読み替えない。

| 原証拠 | bytes | SHA-256 |
| --- | ---: | --- |
| focused.json | 11302 | cf85a2c6439352d0eb2479c4fed103d5bd6e79fd2b57a297f6c536c6511b8aff |
| focused.log | 3262 | 27eee2c3b69b65041a48c843851287d8083affd98da03885cb33a292898cbd8e |
| focused-v2.json | 11302 | 4fcaf62de612e61c9ad9ca10baee2b8cc274df75709de7cf42451dcf9aafe7b0 |
| focused-v2.log | 355 | 5ef57d085031fc2fc2942bcb2a13a59ad0635d45e8b2d5b6fafec33646d6e540 |
| focused-components-final.json | 1007 | 607b378fdf6701fef2e8ad519a3aa2ed211d50f06a162186fc93ed77a918d547 |
| code-save-checkpoint.json | 6422 | db61d5d89591c89be4207f03060f944b8c6336cd61975eec82b580f700a08a7c |

focus49792/creation134358760023248364/tokend0238a0c433ceed9e88fb642136e9249c9cc9e0dfd740af0a0bfa400c68b00ea、訂正19684/134358760606119568/tokena0312bcb4564d7754b0b32924e897fff603e55b97853595f0e8b832698e88c4eはexit1/0・CIM残存なし。全helper終了/critical ownerなし/native0/追加agent0。fake channel/shared budget＋実小FileIO/保持fileのprotocol gate、実Win ABI/exe/pipe/worker/native認証/全経路容量合格ではない。

## 未接続境界

上位external plan descriptor/実callerへのallocation forwardingと、parent-childのcontrol/pending/partial archive予約・coupled peakは未接続または未実証。次は同じcaller-held plan pinでallocationをforwardし、実request/binding/stop/manifest/proof/ackの保持順/最大残余を元shared outerへ結ぶ小さい単位。native createはroot/channel/Job前拒否を維持する。latest clean revisionのfresh source/runtime/profile/policy/request/unusedrootと元owner保持限定launcherのexclusive準備完成前にnative入口を開かず、全7役whole.runを限定readerとして起動しない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。正の小capを全失敗保存保証にしない。unknown Close/Delete/既存Unclosed/未回収/IO・割込みは元owner/raw/pending/inflight/partial archiveを保持、blind retry/後続Git-worker拒否。0-job/途中成功prefix/metadata/root exit/EOF/worker kill-waitはlease/ackの代用ではない。

## 同時に保存した先行CI

CI37670193576は外部fullHEAD `869b27a58c91b119d7328550efc86f017ca62045`/attempt1、両minor3504/fail0/error0/skip237/source不変、全3job success。専用 `artifacts/ci-diagnostic-37670193576/` に10raw14pin/local-remote一致/共有29必須28/runner v2 consistent_candidateを保存。index2783B/54e96569efaf0164ff89797ff41566a3ca6c549358d3e742b9aa03749d0475ee。3.12/3.14新版20261004.327.1/prerelease=true、compare旧20260927.320.1、公式pin一致のみ・digest未取得/候補未採択。CLI7は6raw一致/skip1file既知CRLF6差を両pin保持。本codeの実native/容量/正式受入へ読み替えない。
