# v0.3 架空campaignの子anchor照合と受入残件（2026-10-04）

正式評価前の技術保存点。作業branchは `codex/preformal-acceptance-scope`、この試行のclean source revisionは `2e10c6723df9f00999c90416954a806329546dde`。入力は固定手作り系列で、登録holdout観測を読んでいない。26H2の[S4改訂案](../anomaly-v03-s4-26h2-amendment-draft-v1.md)はreview draftのまま、旧gate `s4_acceptance_not_frozen`、正式credit 0を維持する。

## この保存点で進んだ境界

- `933053d`：Linux CIの両jobが `ImageOS=ubuntu24`、空でない `ImageVersion`、GitHub run ID/attempt、clean HEADと一致する `GITHUB_SHA` を保存・比較する。image digest、外部job log、release manifestは未取得として保持し、最終CI受入には数えない。
- `09cba01`：独立したWindows Job fixtureでrootと孫を同じJobに所有し、正常終了時のJob稼働数0、timeout・親異常終了時の終了と回収をnative 8件で検査した。既存campaign controllerへは未接続で、Job外processや個々の孫exit code、正式全工程予算を証明しない。
- `2e10c67`：生成子、初回保存reader、fresh再読取りreaderへ固定計画path・anchor raw pin・区間・attemptを渡し、各子が計画を読み直してv2返答へechoする。外側はinvocation ID、PID/start token/親PID、echoと保存pinを再照合する。後述の新しい非上書きrootで一区間を通した。

関連campaign/CI試験152件pass・1件skip、Job native 8/8 pass、`tools/safety_check.py`と`git diff --check` pass。これは上記source時点の技術試験であり、最終Linux両jobの実runやS4独立受入ではない。

## 新しい架空campaign `72f754b3`

`D:\develop\banto-ai\artifacts\anomaly-v03-preformal-campaign-72f754b3` と外部control root `D:\develop\banto-ai\artifacts\anomaly-v03-preformal-campaign-control-72f754b3` を分離した。slot 0・attempt 1・path code `h001` のprepare、started、run-budget、fresh再読取り、completedを順に非上書き保存した。旧 `486f28cd`、`c001/c011` 等の区間と加算しない。

次のpinは保存ファイルの **bytes / SHA-256**。`campaign` と `control` は上記rootを指す。

| 保存ファイル | bytes | SHA-256 |
| --- | ---: | --- |
| campaign `plan.json` | 95,753 | `ac8fc232281ec8277e0f66c959a3de1f2dd883eb9320568fd3bdaf0855b6808e` |
| control `checkpoint.json` | 348 | `90e414b7ef1e414c2efb2a91a84e009a360a032bf0fa19db534f3025e24b7ab6` |
| control `preflight-intention.json` | 1,598 | `0d0abeaf656509c7f57b78fb1e9352463186b5f03aae2ec890b3d9768262602f` |
| `artifacts/anomaly-v03-preformal-campaign-prepare-72f754b3/receipt.json` | 2,179 | `506d0bd04a44ab58ec228ced3de2dd3bd02d441890afbd1ff4869b4dae357ac4` |
| `artifacts/anomaly-v03-preformal-generated-pinsets-h001/pins.json` | 75,735 | `2efb31c01c0313625770259184b36fb12d73b1fc3cfdb53ad77cd0ae5bf034b1` |
| campaign `journal/000001.json` (`started`) | 1,244 | `0061eb361caa6b07504504181afcf7ee03bf1f1218aedb1445de3d56d27f26ac` |
| control `checkpoint-000001.json` | 839 | `4bfb4248259efebaf951a5fb1c44cf4a07146cc143202c4ea7776c91775a1b70` |
| campaign `intents/0001-run-budget.json` | 1,801 | `617025ea44553338f35cb26b655287346cdd218812f8fa9f4b321e58238ac6f5` |
| `artifacts/anomaly-v03-preformal-campaign-run-intent-72f754b3/request-pin.json` | 1,661 | `657e387468de1b358cfefd5f0fb9d3f553b20951c4a9fd4405d42e96d3ee4920` |
| campaign `control/000-1/run-budget/receipt.json` | 6,928 | `18a8c77a980c670adb0826c60b1df428d33bd73dd50315810eb5473de4aa185d` |
| campaign `intents/0001-saved-reread.json` | 2,115 | `48e516c46f09827f9aa2f00a196f8ab8cd0f0a89c94de3db5002e89453fdc263` |
| `artifacts/anomaly-v03-preformal-campaign-reread-intent-72f754b3/request-pin.json` | 2,119 | `80810ff8beaeed2b31e7ae57c73b6f71c4443888e979e5e0000e1c4b016f13dd` |
| campaign `control/000-1/saved-reread/receipt.json` | 2,470 | `0dd157a02c3289e1c6add3e81d1c6bad1a0ce3f6e754be0a2f3d394be179c006` |
| `artifacts/anomaly-v03-preformal-saved-row-reread-h001/rows.json` | 116,085 | `c0ac5199eebdcdd2c11ded98191e24ee7cd16ce8b7ab861841098550dd1a434c` |
| campaign `journal/000002.json` (`completed`) | 6,641 | `ebe27668e663baefb004831b984df5ae60f6db93aa40fd3756f3239df75d8ece` |
| control `checkpoint-000002.json` | 1,190 | `b7b950406035adcea40a1fef3ff02525c16213526038e45a7e43860fc38802b5` |

`tools/preformal_campaign_completion_store.py verify` は、上記plan・初期checkpoint・intention・prepare receipt・started・中間checkpoint・両pin-control・両owner receipt・completed・terminal checkpointを明示pinで受け、exit 0を返した。terminal count 2/head `ebe27668…`、完了**宣言**1/480区間・6/2,880評価、欠番479。状態 `partial_declarations_unverified` はmetadata層が保存rawや由来を全campaignとして認証しない設計上の保守値である。両owner receiptは各区間の限定scopeで `verified` だが、`campaign_coherence_authenticated=false`、`launch_authorized=false`、`resume_authorized=false`、`formal_permission=false`、`campaign_evaluations_credited=0`。

独立read-only監査で保存22 raw、合計131,144,120 Bを実ファイルから再SHA-256し、22/22でmanifest pinと一致した。生成・初回reader・fresh readerの3組とも、保存invocationと子v2 reportのinvocation ID、計画path/anchor pin/区間0/attempt 1のecho、監督記録のPID・exit 0を照合した。fresh readerの保存行は6行である。この照合は今回の架空一区間の保存証拠に限る。

同監査は、計画/manifest、選択source 42 unique raw（183 pin参照）、started→completed journalとcheckpoint 0→1→2のhash chain、terminalの4外部pin、completionの19 evidence pinを実ファイルと照合し、不一致0だった。fresh 6行と保存report 6行の共通5列も一致した。計画側source 36件と子role側追加6件は選択rawの照合であり、動的依存を含む5役の完全source closureではない。

生成・初回readerの共有予算は233.257秒・902標本でpass、最大root論理131,346,484 B。fresh再読取りは別予算56.580秒・225標本でpass。これらは別々のsampled/cooperative予算であり、producerから公開後readerまでの単一外側停止・子孫回収・容量2倍判定に読み替えない。

`artifacts/` はGit管理外で、この作業場所のraw証拠はcommitから再作成されない。引き継ぎ文書のcommit後はHEADが計画の固定sourceと異なるため、現HEADでの旧campaign `verify` は拒否される。再検証時はこのcheckoutをcleanな `2e10c6723df9f00999c90416954a806329546dde` に戻し、上記pin・同じ絶対rootを指定する。別worktreeや別pathでは計画の絶対path照合が合わない。

## 受入までの順序

1. **S4契約**：26H2の保証A改訂を版付き計画・運用契約・正式wrapperへ反映して独立再監査する。現案は未採択。
2. **S4 consumerと5役閉包**：架空登録入力から最新attempt・保存raw・profile/score/ledger・全slice/sidecar・40 cluster/50,000 draw・完全S6同形audit・公開後readerまでの由来を接続し、producer/analysis/audit/writer/readerのsource/runtime/外部program、異常子孫停止・回収を閉じる。今回のJob fixtureはcontrollerへの接続と失敗経路実証が残る。
3. **S4最終環境・予算**：最終clean revisionのUbuntu 24.04 Python 3.12/3.14両jobとrun log等のrunner同定、Windows 26H2 native、正式dev 8・smoke 2、単一外側予算と計画所定の容量2倍を一つの受入記録で検証する。CIラベルだけではrunner同定は完了しない。
4. **S5–S7**：S4採択後に限り、未使用40登録holdout seedを新rootで480区間・960 dataset・2,880評価実行する。その保存rawからS6で数値と分母を独立再導出し、別root公開・fresh readの後、S7結果文書へ反映する。

架空480区間の完走を自動的にS4の新規必須条件へ加えない。今後の小試行も新しい非上書きrootと固定sourceで行い、正式登録観測をS4採択前に読まない。
