# v0.3 worker Git終了guardの保存（2026-10-07）

code初版 `13ac6a18a7681a0d85185d7e4fdad92940ae1bc0`、callback保持順序修正 `e1b892409fa22e45c9757f34bfe0f6655d1bc08d`。正式gate s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。実データは保存済み合成dev8/smoke2のengineering読取り・記述報告のみ。

## 固定した終了境界

- `run_guarded(actor, operation)` はbody例外・原critical owner・ack例外を分けて保持。bodyがnative例外を飲み込んでも原critical ownerを優先し、元ChildGitKeeperのrecoveryと原失敗raw確認後に元例外をそのまま再送出する。ackはGit回収の証拠で、業務成功の宣言ではない。
- keeper呼出し、保存raw読取り、診断、sleepのIO/割込みを記録してPython保持を継続する。閉じた原handleを再実行せず、元keeper/completion/closed set・exact lease・原rawとsaved eventを再照合する。unknown close/Delete/Unclosedは回収済みへ読み替えない。
- 外部inventoryにないnative ownerも診断前にguardへ保持し、原keeperまたはoriginal native handle keeperへ委ねる。未登録のlease/rawを発明せず、このownerではackを許可しない。
- zero-job、active/owner未解決、成功prefix途中の終了、ordinary actor error、poison archive、lease未確認はackを拒否する。全call完了、または最後のraw確認済みfailed callで停止したprefixだけ、caller-held inventory/manifestを再読取りしたproofへ渡す。partial proof/ack公開のIO失敗は原error/pending rawを残し、再公開で上書きしない。
- 初版はcallback callable検証がguard生成前だった。既にcritical ownerを持つactorでも検証失敗をguard内catchへ入れるよう、保持→検証の順に修正した。

## 焦点試験と保存pin

初版の新10件/2.987592秒はfail0/error0/skip0、22 source/science pin前後不変・変更2file safety・unique10 discovery・clean code-save22 working/Git一致。保存後に上記callback検証境界を修正し、新1件だけ0.456592秒pass。初回10件反復0、他20 pinは両runで一致、最終unique11 discovery/22 working-Git pin/safetyを確認。初版10件を最終source単一11件success runへ読み替えない。旧actor13distinct/archive16/proof18等も反復0。

raw: `artifacts/preformal-worker-git-terminal-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json（初版10件） | 8685 | `c83922eaa62e0bc33f06c3c6dd862b093934c33ffaec599c4bb33d43a836a7a8` |
| extra-one.json（保持順序1件） | 7445 | `d2725356b14f59d7d9ebbe3d056e255f2b33bd791ab6a9ec3841ff7d86a988df` |
| focused-components-final.json | 5404 | `dd816037c7fc58fe64e1f4db438e2f036ca70e2c29ec742b0e177ce7ad0b4595` |
| code-save-checkpoint.json（13ac6a1） | 683 | `f48d8e8afd7658771eb911becb97f3499c3d90bf4469fc219487079b0a6e1027` |
| code-save-checkpoint-v2.json（e1b8924） | 876 | `4821638820eeeb46e4b2d2d85807155d3273d3fbad2fc748d00e4f926759fbc6` |

helper PID32556/creation134358407802953904/token1f3a66bbf30a73226f114327cc900a55af42a68db35a3f9519ba38090b566e33、追加PID34968/creation134358412325458396/token4e0104ec0b858ad054ad9f780e9c47a253e555fc3c7c7a6d7448c7de9d848e49はexit0/CIM残存なし。全helper終了・critical ownerなし・新native0・追加agent0。

## 次の範囲

fake executor/Kernel/creation/checkpointによるprotocol gateで、実worker/実exe/Win ABI/native認証/容量合格ではない。guard APIのcatch/保持は接続したが、既存reader_worker_mainはまだ既定のJSON報告/終了経路のまま。Parent.create/on_started bind/stop_fence、Child binding wait/actor/guardを実invocationへ渡す経路、worker側共通budget checkpointは次の小さい単位。Popen回収やworker kill/waitだけを子Gitの回収証明へ読み替えない。

新importを含むsource/runtime inventory/profileを新revisionで準備し、旧14/14や古いpinを使わない。producer非対称pre26/post24は親111/111へ渡さない。archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB/32entry/depth2/reserve128KiB・全体321MiB/672entry・cleanup30秒/poll0.25秒を保持。control完成4+pending4/proof-pending/caller inventory-manifest/archive/inflight失敗raw-partial archiveを測定rootへ計上し、実入口/拒否/停止保全とexclusive準備が完成するまでnativeを開始しない。

CI37598762191（外部HEADba6f82e）は各minor3263/fail0/error0/skip237/source不変・全3job success、10raw/14pin/local-remote回帰一致/共有29fixture/必須28/runner v2 consistent_candidate/保存後照合まで完了。全job20260927.320.1、digest未取得・候補未採択。詳細は[CI保存](anomaly-multiseed-v0.3-worker-stop-boundary-ci-save-2026-10-07.md)。actor CI37602415125（f0ecd89/3276予定）、初版guard CI37604591211（13ac6a1/3286予定）、修正guard CI37605468456（e1b8924/3287予定）は終端未確認。doc-only新CI追跡を増やさず、各外部HEADへ固定して保存する。正式5残件・正式採択・最終受入は未完了。
