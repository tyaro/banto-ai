# v0.3 上位callerの外部pin付きreader plan受渡し（2026-10-07）

code `a12c3e91883d9e79fadbdd8f4b23b06f02add2ff`。先行 [実親caller接続](anomaly-multiseed-v0.3-reader-git-parent-connection-2026-10-07.md) へ、generation_publication_budget.runから渡す外部planの形を固定した。

## 接続した範囲

実trial callerは `reader_git_plan={'path': absolute_plan_path, 'expected_pin': caller_held_pin}` を渡す。run開始時にdescriptorをdeep copyして固定する。指定なしの既定経路は従来どおりで、新keywordを生成workerへ渡さない。

planは32KiB以内のcanonical JSON、exact fields:

`format / revision / outer_root / channel_root / policy / source_pins / profile_pin / formal_permission`

- format=`anomaly-v03-preformal-initial-reader-git-plan-v1`、formal_permission=false。
- caller pinで原rawを読取り、revision／outer root／initial-readerのfresh profile pinを照合する。
- planとpolicyはartifacts配下で測定4rootの外。policyは別の固定policy.jsonと外部pin、revision／private Job ownershipを照合する。実exe／完全なpolicyは下位部品で照合され、この準備読取り自体はnative認証ではない。
- channelはunused `outer_root/reader-git-channel` に固定。30sourceのexact外部pinとworking rawを確認し、profileチェックにも追加16sourceを含める。
- 元outer clock／linked producer budgetを開始した後にplan/policy/sourceを再読取りする。保持したresolved planと一致してからgenerate_and_readへcopyを渡す。clock/sampler／inner phase logを作り直さない。
- resultへ外部plan pin、reader source pins、forwarded flagを記録する。このflagは子Job回収／native成功／正式採択を意味しない。

新runtime profile、実plan/request/native launcherは未準備。旧使用済み全7役launcherやrootは編集・実行していない。新file readは実行前のbounded準備と元clock内での再照合であり、正式全経路のwall測定完了には読み替えない。

## 焦点試験

初版の新 **9件、1.1331297秒、fail0/error0/skip0**。外部pin／revision/profile/root/closed flag、wrong measured context、source欠落/改変、元linked budgetのforwarding、既定経路、clock開始後のplan改変停止、profile不足時のroot/worker開始前拒否を確認した。

保持descriptorがcaller側の後変更に追随するriskを見直し、開始時copyを追加。その **新1件だけ0.2216016秒でpass**、旧9件は反復しない。新10 distinct、最終unique10 discovery。最終sourceの単一10success runとはしない。

39 source/science pinは各run前後不変、変更2file以外37pinは両run一致。変更2file safety、clean code-save39 working/Git pin照合がpass。fake profile/policy/owned stage/system snapshotのprotocol gate、worker/native/実exe/Win ABI/容量合格ではない。mock生成stageで意図的に停止し、saved-reader/publication等は開始しない。

証跡root: `artifacts/preformal-reader-git-plan-forwarding-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| focused.json | 14226 | 698be7fca9f24b972e99f16a7631e4a0a17b7460bd8534925efa1d45c40f36c6 |
| focused.log | 2200 | 2a3065270992f1ef36ce49a7228919ab4455ce84016546ff3b0df0a690a09842 |
| added-one.json | 12996 | 1934e6ca87723db8939781a0b64001a5bf119e983f78f7d8eaa74701efabd3f2 |
| added-one.log | 319 | 53eafbdeadead4024df7e5729dd89b5e8beb1337adcadce5ef56a1fadbfe092e |
| focused-components-final.json | 6538 | 7f097a9bf5e60ed8288f025f9711faaeeb8aa4bc16af093cdf92d2799327b019 |
| code-save-checkpoint.json | 492 | 12587189d512e10062c2134cb86690614fd9aedffdc2145325ad13e1560c1f05 |

focus47752/creation134358476059370522/tokena117c2e5ede138e870d422ada26fbc65100aec56f25268f715fb7a57cb997d6a、追加36868/134358478399341885/token5ef4879bffd374d4c5f10d77f0af8ebdfb6211de684f19f0f5409e60745b501f はexit0/CIM残存なし。全helper終了・critical ownerなし、新native0・追加agent0。

## 次の準備範囲

最新clean revisionで、30source/64callと実importを含むsource/runtime profile・外部policy/pin・専用unused root/requestを準備する。30sourceは完全runtime閉包ではない。producerの非対称pre26/post24や親111/111の旧pinを流用しない。

root inventoryにはcontrol4frameとpending、caller inventory/manifest/proofとpending、archive/inflight/失敗raw/partial archive、既存outer receipt/診断を含め、byte/entry/depth/最大残余を見積もる。archive512KiB、outer1MiB/32entry/depth2/reserve128KiB、全体321MiB/672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。既存rootへの追加・receiptの未測定root移動・上限緩和はしない。

限定reader確認のexclusive launcher／元Popen/子Job keeperの終端／正確なcall inventoryと停止・失敗raw保全を確認するまでnativeを開始しない。完成済み全7役／親138Job／焦点suiteは反復しない。未回収owner・unknown Close/Delete・partial proofは保全し、後続Git/workerを拒否する。

formal gate=`s4_acceptance_not_frozen`、formal_permission=false、credit0、登録holdout観測未読。実データは保存済み合成dev8/smoke2のengineering読取り・記述報告のみ。runner digest/候補採択・実ロード依存/業務異常子孫・正式5残件/最終受入は未完了。
