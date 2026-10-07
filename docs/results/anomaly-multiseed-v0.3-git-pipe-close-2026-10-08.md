# v0.3 Git read handle／FileIO sink close（2026-10-08）

初版code `0f9cb52e1b547ed70e0a352417b1846639afa322`、fd所有条件の補強code `0aaa12db38fe0caf03cc2d4bd4e036b10304fcc4`。先行clean文書HEAD `4217b99ac35f8d68103a9489d97f7973ec3d17ef` からの小さいopt-in部品。実pipe作成／worker caller／追加IO解除／receiptとのclose link／root admissionは未接続。`ReaderGitParent.create_native` のroot/channel/Job前拒否を維持する。

## 保存した処理

- `GitPipeClose` は元reader、GitOutputOwner、同じ原ChildGitKeeper、read handles、sink streams、先行close ownerを検証・IO前に保持する。keeperは元SpawnIOOwnerのkernelを使い、最初のJob/root終了・creation観測とkernelをcacheする。追加IOなしの既定経路は従来のkernel経路を使う。
- parent writerの実return位置からのclose event、両pipeの観測broken-pipe EOF、pending/失敗/limitなし、元keeperのcached Job/root終了・creation、原diskの全count/digestを必要とする。root exit、marker削除、released宣言、EOFだけでcloseを許可しない。
- readをfreezeし、原kernel/handle/returnを保持したnamed CloseHandleの成功位置からeventを保存する。sinkはexact FileIOかつclosefd=trueを必要とし、元streamのflush/fsync/fstat/count確認→元FileIO.closeのreturn→原disk再読取りを記録する。FileIOのfdを別のCloseHandleでも閉じない。FileIOがfdを所有する条件は [PythonのFileIO仕様](https://docs.python.org/3/library/io.html#io.FileIO)、read handle APIは [Microsoft CloseHandle仕様](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle) に対応する。
- knownFalse／不明return、raw改変、sync/clock/readback IO・割込みは元native例外、stream、handle、pending/raw、観測済みclose eventへlatchし、後続close／再closeを拒否する。正常cacheでもrawを再照合し、native closeを反復しない。
- close結果はio_released=false／parent_ack_authorized=false／execution_authenticated=false。追加IOを持つkeeperは引き続きcore close/completionを拒否する。現receipt/post-close v1へ追加IOの証拠を渡す処理はまだなく、close観測だけをlease/ackへ読み替えない。

FileIO.closeは原Pythonのfd所有streamに対する観測であり、Windows raw sink HANDLEのCloseHandle returnを得た宣言ではない。新gateのsinkは実exclusive小file／fsync／空raw、Job/process/creation/pipe EOF/read CloseHandleはfake API。実Win ABI／実pipe／実worker／native認証／全経路容量合格ではない。

## 焦点と保存

初版の新13件を一回、0.097845秒、fail0/error0/skip0。正常close/cache、EOF/reap/writer event不足、FileIO以外のsink、raw改変、knownFalse/unknown read close、close後checkpoint割込み、sink sync失敗、close後raw読取り失敗、keeper core拒否、foreign keeper保全を確認した。

仕様照合でclosefd=falseのFileIOがfdを保持する条件を確認し、closefd=true必須を追加。新1件だけ0.012294秒でpass、先行13件反復0。distinct14件／最終unique14 discoveryであり、初版13件を最終source単一14success runへ読み替えない。

各runの36 source/science pin前後不変、補強で変更したproduction/test以外34pinは両run一致。先行parent-writer gate35pinの変更production2file以外33pin不変。変更3file target safety、初版clean code-save36working/Git、補強clean code-save36working/Git一致。新production module0、名前30source／各phase32要求／予定64Jobは維持するが完全runtime閉包ではない。fresh source/runtime profile／policy／request／unusedrootは未準備で、旧HEAD/pinを読み替えない。

raw: `artifacts/preformal-git-pipe-close-20261008-prep/`

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 11295 | `578d1b470934980089396e52fe1e37f4204931f6b9d35c654f993a9e38d49bcc` |
| focused.log | 2628 | `fea756c08aaf683ef11da501c3a333a430944aeb8404ed324d3617c8394dea38` |
| supplement.json | 11315 | `274bfda0f1d60fa2a4d95077e45aa9a881467d687ad10fb1536ca9b8d1c32f34` |
| supplement.log | 294 | `9dcfc49ad64c3ba2eaf06beca461205feabb63c8a7382a13afb85988b6856f44` |
| code-save-checkpoint.json | 305 | `20d8fb52b009374a9f6102bc5ed3634493152266b5b90eca015277dbac2e4e56` |
| code-save-checkpoint-v2.json | 791 | `9367fad9f8b0c1bd9ff55f4618cc7419d9d931cb456701975bacfbd041807aad` |

helper25964/creation134358599511432271/token02224ac229dea06d27bf5d81ea5add031912e6d21a75e5642be4a78251bdf9c9、補強46728/creation134358602714806728/tokenbe773509366f4088a0ce21c99bd7c21ea05b144c032d4151f02e54214fc255ffはexit0/CIM残存なし。全helper終了／critical ownerなし／native0／追加agent0。

## 次の単位

元read/sink close observationを原receipt、post-close verifier、cached keeperへexact linkで結び、追加IO解除をmetadata宣言で許可しない。実CreatePipe／exclusive空sink／exact callの元shared root残余bytes/entries／失敗raw枠／output_limit時の元Job停止と原Python owner保全はその後の別単位。限定caller／launcherと最終clean HEADのfresh source/runtime/profile/policy/request/unusedrootを準備するまでnative入口を開かず、全7役whole.runを限定reader確認として起動しない。

archive512KiB、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。上限緩和／未測定rootへのreceipt移動／旧raw-root整理なし。先行全repository safety30秒timeoutは未確認保全・再試行なし。formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。実ロード依存／業務異常子孫／正式5残件／正式採択／最終受入は未完了。
