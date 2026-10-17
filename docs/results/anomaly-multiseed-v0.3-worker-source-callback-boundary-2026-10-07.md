# v0.3 producer / initial-readerのsource callback境界（2026-10-07）

## 保存したcodeと範囲

code `e4cb23aeff8501ab91cfdcf34d804612f856352f` をoriginへpush済み。producerとinitial-readerの実 `_source` に `git_identity` / `git_blob` を追加し、`_generate_attempt` / `_read_attempt` の前後確認へ渡す境界を保存した。producerの `_validated_snapshots` もblob callbackを受ける。

identityはhead/statusの正確なraw bytes inventory、blobはrevision/path/working raw pinを受けたbytesを要求する。source順序・既存reply/schema・clean HEAD・raw一致の検証を保持する。invalid callback、違うHEAD/dirty status、非bytes・raw不一致を拒否し、指定callbackの失敗時にbare Gitへのfallbackや次のreadを行わない。ResourceStop、UnreapedJob/UnclosedHandlesは元exceptionと元handleを保持したまま伝播する。

worker invocationへ外部policy/予算を渡す経路、actor生成、子worker内の共有stop、critical keeperは未接続。通常worker入口は従来の経路を使用する。このunitは新nativeや業務workerを起動していない。

## 焦点と保存pin

新13試験と既存negative10試験は実23件pass。追加の既存source dirty試験は初回指定クラス名が誤り、loader error1を保全した。実在クラス `OwnedSavedAttemptMaterializerTests` の対象1件だけを実行してpassし、完了済み23件の反復0。24 distinct実試験の証拠を集約し、単一の24件success runとは扱わない。対象7 source/test/science pinは全工程で不変。

対象はsource callbackの正確なrevision/path/pin、元critical owner保持、共通stopの無再試行、identity/raw不一致と未読拒否、default HEAD/status/blob argv・10秒、snapshot raw binding、initial-readerの前後callbackと実read一回、postflight owner failure時のreply拒否、producer preflight failure時の未生成。

全repository safety CLIは30秒でTimeoutExpiredとなり、未確認として保存した。変更3fileを既存 `scan_repository(paths=...)` で明示して検査しpassしたが、全repository PASSへ読み替えない。タイムアウト後に終了待ちしたsafety helper／Git列挙processの照会は残存なし。code-saveではHEAD=origin/cleanと7 working/Git pinを照合した。

rawは `artifacts/preformal-worker-source-callback-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| focused-components-final.json | 4,504 | b22bcde36c88ddd00725a20b1a199d5964eaf1415e9b1db41ba0c0a18f41d669 |
| code-save-checkpoint.json | 545 | d88d6146c4132a5fecb0825274a2a0fca58395a4f963399e9eb20f0d25d98082 |

初回 `focused.json/log`、訂正1件の `corrected-selection.log`、`repository-safety-timeout.json`、`changed-files-safety.json` を保持する。science plan/registry pinを変更していない。

## 次のactorへ固定する在庫

| worker | selected source / phase | pre blob要求 | post blob要求 | 同phase重複をcacheした予定blob Job | 予定HEAD/status Job |
| --- | ---: | ---: | ---: | ---: | ---: |
| producer | 24 | 26（snapshot2＋source24） | 24 | 48 | 4 |
| initial-reader | 14 | 14 | 14 | 28 | 4 |

これらは保存codeのcall siteから得た準備分母で、native終了数ではない。producerではsnapshot2がselected sourceの部分集合であり、pre/postの要求数が異なる。親actorの対称111/111 inventoryをそのまま渡さない。既存生成／consumer内部の他のGit、caller boundaryのGitは別の対象で、表は全Git閉包ではない。

最初のactorはinitial-readerの小さい14/14境界を対象に、caller保持の外部policy/request pin、同revision source inventory、専用未使用root、実行前HEAD/cleanと正確なcall order、shared stop/clock、pending/inflight raw保全を固定する。workerがcritical ownerを持つ間はそのPython ownerを親supervisor終了で失わない終端方式を先に接続する。直接workerのkill/waitだけでGit Jobの回収を宣言しない。現在の親archive520,852 Bへ新receiptを追加せず、新しい測定rootの予算内へ保存する。

runtime profileを使う場合はこの新revisionのsource raw pinへ再準備し、343c863／9c49c4a等の旧pinを読み替えない。新code CI [37576149693](https://github.com/tyaro/banto-ai/actions/runs/37576149693) はin_progress、各minor3,144件予定。親actor旧code CI37572914427は両minor各3131件・全3job success・10 raw/14 pin・回帰/runner v2保存照合まで完了。この旧CIを新e4cb23aの全repository safety合格へ読み替えない。

全repository safety確認、worker内Git actor/共通stop/keeper、実ロード依存、業務異常子孫、正式5残件を継続する。正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0、登録holdout観測未読、追加agent0。旧raw/pin/失敗を保全し、完成済み親native・全7役nativeを反復しない。
