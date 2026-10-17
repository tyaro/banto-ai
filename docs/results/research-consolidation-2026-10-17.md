# 研究ブランチの整理とmain取り込み

2026-10-17 JST。人の「おすすめでお願いします」に従い、保存地点を残して整理ブランチを作成した。mainの自動mergeや旧ブランチ削除は行わない。

## 保存と統合

- 保存tag: `archive/preformal-research-20261017`、原版commit: `50d69b6`。元ブランチは保持。
- 整理ブランチ: `codex/research-consolidation-20261017`。
- mainの`6f1285d`までに含まれる4コミットを取り込む。Windows fixtureのDACL/handle修正とnative testを保持する。
- CI競合は共通Python 3.14のjournal検証を維持し、Windows native fixture互換jobを別に残した。旧3.12 matrixは現在の3.14方針へ戻さない。Windows CIは正式Windows 11受入ではない。

## 現役と履歴

停止済みRust拡張3module、診断example、単発調査・報告toolの計67ファイルを[テキスト資料](../../experiments/archive/rust-r1-20261016/README.md)へ退避し、全byteとSHA256を[catalog](../../experiments/archive/rust-r1-20261016/catalog.json)で保存した。拡張子に.txtを付け、Cargoのtarget探索とPython import/compile対象から外した。ポインタ/once/TLS/PAC/SGEMM調査は実行していない。

model/input/checkpoint/error、predict example、既存の比較器・参照producer・metadata・閉鎖検証helperは残した。未定義featureのexportを削除し、暗黙のCargo example探索を無効化。旧JSON/過去結果/frozen planは元パスを保持する。履歴sourceを実行する場合の入口にはしない。

[引継ぎ](../current-handoff.md)は3,407行から36行に整理し、過去分を[履歴](../history/current-handoff-through-20261016.md)へ保存。移設では相対リンクだけを補正し、元文書は原版commitと宣言snapshotに残した。main側の過去状態台帳も[別履歴](../history/main-document-status-20260925.md)へ保護した。

[検証済みlock案](rust-r2p-lock-and-python-reference-2026-10-16.md)を適用。banto-aiからgemmの直接edge1行だけを削除し、package/versionの更新は行っていない。`.gitignore`にローカル隔離workspaceのoutputs/を追加し、既存ファイルは削除していない。

## 検証

| 確認 | 結果 |
| --- | --- |
| Cargo metadata / locked offline | library・predict・reference-tests opt-inのneutral_integrityだけ。未定義featureと暗黙の診断targetなし |
| Cargo default-feature all-targets test | unit 2件pass、predict compile/test-harness pass。CARE参照は未開封 |
| Rustfmt | pass。model.rsの既存to_vec非推奨warningは保持し、モデル演算を編集していない |
| Python構文 / JSON | tracked Python 928件 / JSON 156件pass |
| 文書リンク | 現在の入口と退避した履歴のローカル参照642件pass |
| archive / 固定値 / import境界 | 67sourceのbytes保持、固定5pin・閉鎖済み参照root不変、現役コードから退避moduleへのimportなし |
| YAML / smoke / safety / diff --check | 全pass。naive smokeは7manifest、MAE 0.75。rawデータ・cache・重みのGit追加なし |

Pythonは既存10module/146testを実行した。最初はMacのtemp経路のsymlink祖先により1failure/15error/2skip。失敗rootを保持し、検査を変えずcanonical `/private/tmp`を使って同じmoduleを一度だけ再確認した。その結果は**139pass・5error・2skipで、suite全体は未通過**。

共通runtime/Phase0/Phase1/Phase2/benchmark/docs/CI検証の95件はすべてpass。公開・受入関連は44件pass。残る5errorはMac未実装のatomic no-replace公開4件と、Linux `/proc/self/mountinfo`に依存するnative収集1件で、共通モデルの回帰と混同しない。Windows native2件はskipで未実行。これらを除外して元suiteをgreen扱いにはせず、元assertionと失敗証跡を保存した。Mac対応の追加実装・OS別の正式受入は今回行っていない。Linux/Windows CIの結果は別途PR上で確認する。

初回publicationはTraceback中の引用を例外数へ重複計上してassertで停止した。集計を例外の最終行だけの照合へ修正し、元失敗root/source/stdioを保持して新規rootに保存した。試験結果・assertion・数値条件を変更せず、テストの再実行も行っていない。

最大観測（監視process込み）はphysical footprint 292,572,184B、RSS 419,643,392B、cache+target 1,043,335,685B。各2GiB/1.5GiB内で、全commandは親900/子870秒内。samplingでありhard OS capとは主張しない。source/stdio/exit/state/closureと失敗2rootを`artifacts/research-consolidation-20261017-*`、publicationの文書前後と監査を`artifacts/research-consolidation-20261017-evidence`へ保存した。

整理ブランチはmainの自動merge条件を設定せず、Draft PRとして提出する。累積の研究変更を含むため、今回の整理差分は保存commit `50d69b6`との比較、全統合差分はPRのmain比較で確認する。旧ブランチ・保存tag・既存artifactは削除しない。

## 維持する境界と次工程

model.rs・原R0.1・R2P protocol/fixture/固定契約と既存closed rootsを保護する。数値参照の再生成、R1再評価、学習、CARE/MetroPT/需要2015再評価、データ取得、下流編集、製品採用は行わない。Mac共通試験とWindows native/OS依存試験を分ける。親900/子870秒、physical footprint/peak RSS各2GiB、cache+target1.5GiB、元artifact/EvidenceStore/stdio枠を維持する。

次は固定R2P条件内の小型Rust loss/autodiff/clip/互換AdamW/checkpoint実装。原R1の1点未達、正式R2実データ学習停止、heartbeat PAUSED、需要の2014以前・同休業mean28・四季平均の過小量/過大量非増加・観測のみ/欠測0分離を維持する。PRはレビュー用に作成し、自動mergeは行わない。
