# v0.3 親blob・identity Gitの限定共通予算native（2026-10-07）

## 固定対象と結果

clean HEAD `d57326e0cf69f5257fe16119ddcd035aef17572d`、actor code `9c49c4a9c15e7f754572eb1add8b834203f1100d` で一回だけ実行した。[actor接続](anomaly-multiseed-v0.3-parent-git-blob-actor-2026-10-07.md)の実source callback、外部pin付きGit policy、元Job/共通stop、phase cache、archiveとpre/post indexを使用した。

document44＋generation67の各phase111要求を67 unique sourceへ固定し、pre/postの134 blob JobとHEAD/cleanの4 identity Job、計138 Jobを確認した。同phase cache hitは88、archiveのstdout原文は67。全138 original process identityは重複せず、元root handleのexit0・Job active0・対象Job全終了を保存rawから照合した。67 sourceのworking/committed raw pinはpre/postで準備値と一致した。

限定90秒・各Git10秒の既存上限内で30.873537秒。samplerはjoin済み、helper PID38808・creation_time_100ns134358229287005102・start_token `90939e4ed07b7f1dbb939471cfec7b749a9f029108c500a182b57dde4cc266a7` の実行sessionはexit0で終了し、終了後の当該PID照会にも残存processなし。critical owner keeperは今回起動していない。

## 上限と保存

4新rootを固定したEnvelopeBudgetを使用し、実際に作成したouter/producerのみを観測した。既存outer1 MiB・32 entry・depth2・reserve128 KiB、全体321 MiB・672 entry・depth12を保持した。最大root logical bytes587,727、entry22、parent private98,369,536 B、最小RAM8,815,312,896 B、commit余裕8,771,465,216 B、disk394,846,404,608 B。resource receiptはpassedだが、全7役・正式同形の容量判定ではない。

archiveは520,852 B。512 KiB上限までの余裕は3,436 Bで、source追加や正式経路の容量余裕を保証しない。pre index17,538 B、post index24,720 B、result22,960 Bで各64 KiB上限内。正常archive raw readback後に、そのcallの新inflight3fileだけを個別整理し、終端inflight/pendingなし。旧raw/rootの整理・receipt移動・上限緩和は行っていない。

rawは `artifacts/preformal-parent-git-blobs-20261007-prep/`、実測rootは `artifacts/anomaly-v03-preformal-generation-publication-git-blobs01/`。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| prep/native-request.json | 20,711 | 9407149f365ad7f699a1ad6135e9527ff5faefaa98c29ccd37272b1542fc171e |
| prep/launcher-ready.json | 787 | 982d302732d0f69fe4d01bdc85fac5ff5df9648985e015e4aa40351b46620937 |
| prep/native-execution.json | 582 | bfadeb362d6dbbcd880efe7d45ea2e9e79ce2639c4f9c398ec4f00e19f6db170 |
| outer/blob-result.json | 22,960 | 2a325598cb2158577516e76e31a5e5661c72acf3e23e7c7f9079ce35ae290138 |
| outer/resource-budget.json | 4,393 | dba391edb49c1957e52994ec0ad3101a24fdf723f4e4156eed5beeaa609b2c9e |
| outer/git-blobs.bin | 520,852 | 2a15d188dcc13a213ced4382752cb945527cb4cd2867842244f495fa0b119c94 |
| outer/git-blobs-preflight.json | 17,538 | 4221e01a727d00557565e4690dab3804a89daf828da17a7688fa2d1525730adf |
| outer/git-blobs-postflight.json | 24,720 | 805b0b4d1981160e26b99af7e1a8ced1f2decb6839ff8ad4858ff6fd39e00be0 |
| prep/saved-native-check.json | 1,107 | 8c17c7610b4cf618052f6b9ae9688ff83f800b0a15f41ef0e1b830095356f5af |

## launcherと別保存checker

launcherはrequest/policy/source/HEAD/clean/未使用4rootを開始前に照合し、helper自身のPID/creation identityをlive-runへ保存した。UnreapedJob/UnclosedHandlesを受けた場合は元exceptionとJob/process/thread/extra handleを同じPython processに保持し、EOF/通常の割込みでownerを捨てず待機する。reconcileは元handleだけに停止・終了確認を結び、失敗closeのhandleだけを保持する。6個の小さいprotocol試験で元inventory、partial close、未回収、未assign root、欠落Job、close exceptionを確認した。これらはnative異常時回収の実証ではない。

別保存checkerは外部pin付きrequest/execution/result、外部policy、pre indexのarchive prefix、post indexの全長・134 call inventory、全frame/raw receipt、138 identity/exit/Job、67 source pin、共通上限・samplerとformal false flagを再照合した。nativeの再実行は0。

初回checkerはcanonical JSONのdict key順を実行順として使用し、identity inventory hashで拒否した。失敗helperと `saved-checker-v1-failure.json` を保全し、v2で明示的なpre/post・head/status順へ修正してpass。native本体・archive/policyの失敗ではなく、raw差替えや再試行もしていない。

## 残件

worker内Git、Git/helperの実ロード依存在庫、業務worker異常子孫、全経路same-target最終受入、正式共通予算・容量2倍は別単位。全7役native343c863と旧4Job native9ddaed7は反復していない。正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0、登録holdout観測未読、[正式5残件](anomaly-multiseed-v0.3-preformal-evidence-index-2026-10-07.md)を維持する。
