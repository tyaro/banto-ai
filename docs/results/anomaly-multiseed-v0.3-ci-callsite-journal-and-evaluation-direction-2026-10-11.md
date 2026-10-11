# Source object callsite CI4112保存・少量評価への工程見直し（2026-10-11）

## 今回の結果

開始2026-10-11T11:51:14Z、HEAD3d29d68d84e228d857c7bece849282020ad2a75c/upstream clean。人の明示再開を維持。先行元43helperのfull saved creation-start_token/live-execution一致・CIM同original不在、原5failed/38passed・過去failedを保持。production/test/body変更0、新focus/類似ownerケース/モデル評価/native/追加agent0。

先行code55c3f86e3751b3049529a11f5a122246d624a3e4のrun38134980431をcompact一回completed-success/attempt1/push/Phase1CI/.github/workflows/ci.yml/workflow349172377へ固定。原run11711B/ebd5fa09dce6951036a7b52d9a2bb4cd3c6bb95f84f55a77a946f63eb6f3de93/stderr0/原gh exit0を判定前保存。

原2job114456896366 test(3.14)・114462685054 verify-python314-journalはfullHEAD-run-attemptと全completed-successへ固定。jobs/artifacts/2logs/2ZIPの未保存分を各一回取得、各gh stdout-stderr/原exit0を保持。ZIPは単一member/decoded8MiB/artifact digest一致、runner image digestではない。

journal4232438B/5b69cb20cb8e05726cc74dcc295de3234addf6c54e5c323d5e8012463a140a61、remote regression37192B/577d5ade7b7344baf594f03ca266d831b97af5f6c25870327881b3d27dcd9a7c。現ci_verify_python314_journalをexternal fullHEAD/workflow SHA25671f0e56eb9b0bb11a6e181e860a64ba45a6a4004cde7d4a5bf35d2b42cbf65a7/run38134980431/attempt1へ一回結びexit0/verification_status=passed。実summary後にdiscovered/tests_run4112/failure0/error0/skip237（Windows native213/non-S4 optional24）/source_unchanged=true/shared29complete/必須28passed/cross_python_comparison_performed=falseを固定した。算術予定を実件数へしていない。

CLI7の実行前working-Git pinと原Git batch fullstdout-stderr/exit0を保存。6exact、ci_windows_native_skip_ids.pyだけ既知CRLF両pinを保持し、working前後不変。local37193B対remote37192Bは末尾CRLF/LF差1byte、raw_equal=false/json_equal=true/CRLF-only=trueでJSON全field一致、両原rawを保存。verification-save4055B/64f1ef2b2d61459ed3efb7b6c0eccbd9839adc7f4872539b837fd9009ccf7fc2。旧raw-equality failed helper/元verifier再実行0。原CLI/raw pinsはhelper全process stdout-stderr又はfull loaded runtime/native認証ではない。

実Ubuntu24.04/x86_64/GCC13.3.0/kernel6.17.0-1022-azure/CPython3.14.8/SOABIcpython-314-x86_64-linux-gnu/runner20261004.327.1、image digest未取得・候補未採択。Windows正式3.14.0/実Win ABI/Job/ACL/stdio/child owner/OS排他/容量/正式S4合格ではない。

4112は55c3 callsite source/runの単一CI保存。最新a54961 output pair code、local15/body18と14/body14の複数source-run、過去failed、旧CI成功・失敗へ読み替えない。完成旧CI/焦点/native/collector/probe/profile/37Git/容量訂正1case/全14call4358432B容量拒否の再照会/download/verifier/reexecute0。

新code a54961c025fc7c9023c3a53a57993be99626240fの実fullSHA selection一回は38136585791/push/Phase1CI/in_progress。原stdout156B/fa6ed77bcb058c397674ebb72f8c050bde28721aebd19a6ddce1f4d7f113cffc/stderr0/原exit0。新attempt/jobs/終端/journal/count未固定、compact/download/待機/反復0。doc-only新CI追跡0。

## ユーザーが求めた工程見直しと回答方針

ユーザーは「入力・モデル・設定と結果の正しい対応、失敗を成功扱いしないこと、再実行できること」を土台に、少量の代表データでモデル評価を実行し、実行して困った箇所を補強する方針について意見を求めた。既存owner差替えテストは残し、類似ケースの追加を評価開始条件にしないという提案を優先する。

この方針を推奨する。ここまでのCIは土台の一部であり、実モデルの入力→設定→予測→指標の経路はまだ今回実行していない。次工程は防御ケースを増やすことではなく、少量評価に直結する最小経路の確認と具体化にする。

- 実行IDへ入力hash、モデルID/版、設定、seed、code revisionを結ぶ。
- 予測原データと指標を保存し、failed/incompleteをsuccessや集計対象へ混ぜない。
- 同じmanifestを指定して新run IDで再実行でき、元runを上書きしない。
- まず既存dev/smokeの1〜2代表ケースを対象にし、必要な修正は実行で観測した問題に絞る。

今回のメッセージは意見要求として受け取り、このunitでは既に取得したCI証拠の保存だけを完了した。モデル評価、native入口解除、正式holdout観測、science設定変更を開始していない。既存create_native早期拒否/全7役whole.run限定reader実起動禁止、formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/登録holdout未読/正式5残件・最終受入未完了を維持する。類似ownerテスト追加は少量評価開始の新条件にしない。

## 保全

115source-science working不変、検証済みa54961親tree/prior37/doc-only非交差継承。科学hash metadataだけ/holdout観測未読/credit0。旧SourceBatch14301B/0903a855f665499d9e3eba5248ceaca09387b948a7051d42704d792db18c0b17/create_native437B/0bd7b84f0a3dc0bd22a865ac8b2b4ccedc0e71ea50a177b0e6b086df07fdcc7c/元caps-v1schemas不変。named30source992758B/最大archive130691B/source差381Bはruntime/global容量保証ではない。

原run rawは今回metadata rootに一度保存した原bytesを使い、CI rootへ再取得・copyしていない。未保存CIrawはartifacts/ci-diagnostic-38134980431/（16MiB256entry/single8MiB）、metadataはartifacts/preformal-ci-output-pair-current-20261011-prep/とartifacts/preformal-ci-callsite-terminal-post-20261011-prep/（各512KiB32entry/reserve128KiB/single128KiB）。最終post-save/owners-after-save/root-closedを最終pins/count/bytesの根拠とする。閉鎖後の追加/同保存/完成4112/download/verifier/元helper再実行は禁止。

次heartbeatは38136585791/fulla54961 compact一回。終端だけ新専用rootへ未保存raw一度、現3.14単一journal/独立verifier/2logsをfullHEAD-workflow-run-attempt-jobsへ結び実summary後count固定。未終端は待機・反復なし。少量代表評価の最小経路を整理する。停止保存済み古い部分CIは履歴のまま、今回完成へ補わない。Sol容量エラー/人の停止割込みでは保全後PAUSED・重複再試行なし。追加agent禁止を維持。
