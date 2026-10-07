# v0.3 親blob Job・archive・共通予算のactor接続（2026-10-07）

## 保存点と接続

code `9c49c4a9c15e7f754572eb1add8b834203f1100d` をoriginへpush済み。[ParentBlobActor](../../src/banto_ai/anomaly_v03_preformal_parent_git_blobs.py)を[実caller](../../src/banto_ai/anomaly_v03_preformal_generation_publication_budget.py)のopt-in `parent_git_blob_archive=True`へ接続した。外部pin付きparent identity Job policyが必須で、invalid option/未指定policyは新root生成前に拒否する。既定経路は従来のまま。

source inventoryにactor/archiveを加え、現在document44＋generation67 pathを各phaseで読む。同phaseの重複44はcacheし、実blob Jobは各67、前後134。親HEAD/clean4 Jobを含む限定親nativeは138 Job・読取り222要求を予定する。準備後、clean docs HEAD d57326eで[限定nativeと別保存checker](anomaly-multiseed-v0.3-parent-git-blob-budget-native-2026-10-07.md)が完了した。138 Job exit0/active0・67 source前後一致・30.874/90秒、archive520,852 B、sampler/helper終了。正式経路の容量証明ではない。

各missは元Job executor、10秒上限、`budget.probe`へ接続する。callbackに渡されたrevision/path/raw pin、policy raw pin、返却receipt/stdoutと保存rawの一致を確認し、common checkpointをcall前後・archive前後・cache hit前後に置く。postflight source pinはpreflightと同じ値であることを要求する。

正常時はarchive append/readbackの後に、その新しい `git-blob-inflight/` のstdout・stderr・receiptを全pin再照合し、固定3fileだけunlinkして空directoryをrmdirする。resolveした絶対pathが当該測定root/ROOT artifacts内であることを確認し、再帰処理・旧root整理はしない。extra file・cleanup errorではrawを残し、後続call/phaseを拒否する。cleanup途中の失敗でも先にarchiveへ原文を保存済みである。

停止・返却binding不一致・保存失敗ではpending callとinflight receipt pinを保持する。UnreapedJob/UnclosedHandlesは元exceptionとhandle所有権をそのまま返し、成功扱い・後続Git/workerを拒否する。実native launcherへownerを生かすkeeperを保存し、6 protocol試験を確認した。限定nativeではcritical ownerは発生していない。

## 保存indexと64 KiB制限

preflight/postflight終了時に、要求の全分母・unique source順序・各pin・native call順序・phase・archive frame coverageを照合する。phase別indexは64 KiB以内のcompact形式で、source paths/pinsを一度だけ記録し、call IDとphase inventoryを再構成する。外側resultには小さいstate/pinだけを載せ、既存64 KiB result上限を拡げない。

preflight indexはarchiveの外部pin付きprefixを検証するため、後段append後にも照合可能。postflight indexではtailも全長一致を要求する。indexのroot/path、policy、revision、source/request inventory、全frame pinを固定し、copied root・欠落・差替えを拒否する。実callerはpreflight照合失敗時にproducerを開始しない。

## 焦点証拠

actor専用11＋実caller追加2＋既存32の計45件を2.194935秒で実行し、fail0/error0/skip0。11 source/test/science pinは前後不変、repository safety PASS。archive部品の完成済み19試験をこのunitで再収集していない。

対象は実Jobへのtimeout/probe/policy受渡し、phase cache、prefix保存照合、copied index/在庫差替え、policy stop前の未起動、Job終了直後stopのraw/pin保全、返却stdout不一致、元Unreaped owner/stdio handle保持、cleanup error/extra file・旧root不変更、不足/余分な要求・phase順、producer前の実preflight拒否。これらのJobは明示的なprotocol fixtureで、native Jobを起動していない。

rawは `artifacts/preformal-parent-git-blobs-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| focused-final.json | 1,855 | 1e6851ea33f63482cffdf59f514cfcad03bb0248c75a6e952d97a28167b28b6a |
| focused-final.log | 9,511 | 5cda0a95bd1bdc131726248f13776bb6dfe815b95875d49696abbe638d79d5d6 |
| code-save-checkpoint.json | 2,304 | 55c309ab57a1521912ec5af6ad56ac1e4a0941b54ad2d925dff0cd786ee0306d |

初回42件passはroot binding・caller拒否試験追加前の保存履歴で、加算しない。code-save checkerはHEAD=origin・cleanと11 working/Git source/test/science pinを照合した。

## 限定nativeの準備と残件

文書保存後のclean HEADへ固定したnative preparationを `artifacts/preformal-parent-git-blobs-20261007-prep/native-request.json` に準備する。外部Git policy、全67 source working/Git pin、pre/post call inventory、4 disjoint新root、既存outer1 MiB/32 entry/depth2/reserve128 KiBと全体321 MiB/672 entry/depth12、各10秒、限定90秒の時計を固定する。policy/pin準備は時計外であり、capacity creditに含めない。

この準備を終えたd57326eで専用nativeを一回実行し、正常終了・別保存照合まで完了した。元handle keeper付きlauncherと開始前のHEAD/clean/root未使用確認を保存した。worker/helper live-runに終端がなければ保存PID/creation identityへ確認を結び、既存実行に任せる。失敗時に原ownerをPython終了で失わず、inflight・partial archiveを保全し、新worker/重複trial/ tracked編集を行わない。既存の全7役nativeや旧4Jobのみのnativeを反復しない。

新CI37572914427（HEAD9c49c4a）はin_progress。先行CI37568898031（HEAD9af4a96、各minor3099件）と37570913852（HEAD1159b9a、各minor3118件）は全3job success・10 raw/各14 pin・local verifier/runner v2照合まで保存した。残る新CI完了時に同HEAD/run/attempt固定の保存を行う。文書のみの追加CIは抑止する。

実worker内Git、Git/helperの実ロード依存、業務異常子孫、全経路same-target最終受入と[正式5残件](anomaly-multiseed-v0.3-preformal-evidence-index-2026-10-07.md)は残る。formal false、credit0、holdout観測未読。自走heartbeatはACTIVE、追加agent0。Sol容量エラー/停止指示では保存・安全な終端後PAUSEDとする。
