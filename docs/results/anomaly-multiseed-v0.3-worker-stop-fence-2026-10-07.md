# v0.3 元workerを保持するopt-in stop fence（2026-10-07）

## codeと境界

code `01ab74fe479ddfeb46ca781ebbd3db1ccb93c84c` をoriginへpush済み。[親supervisor](../../src/banto_ai/anomaly_v03_process_supervisor.py)へ `stop_fence(process) -> bool` を追加した。callbackは元Popen/process handleを受ける。callerはstopをlatchedにし、workerが新しいJobを開始せず、保持中Jobの回収を確認した場合だけ明示的なTrueを返す契約である。このunit自体はJob receiptを認証せず、共有stop/ack channelも未接続。

False、非bool、callbackのI/O例外・割込みでは `UnreconciledWorker` を返し、元Popen/handle・fence・元fence exceptionを保持する。kill/wait/handle close、終了後ログ読取り・final context/boundaryへ進まない。root exit0だけでackの代わりにしない。既定のfence=None経路と既存wall/memory/output上限、cleanup wait30秒は維持する。

明示的なTrueの後でも、waitでroot終了を確認できない場合はfence付きownerを返す。opt-in handle close失敗も元ownerを保持する。reportの `worker_stop_fence_confirmed` はそのチェック時のcaller ackであり、現在のJob状態・全子孫終了・source/runtime閉包の認証ではない。

## keeper

`retain_until_exit` はguarded ownerを通常のkill/wait keeperから分ける。再照合でTrueを得た場合だけ元processにkill/waitを行い、元rootの終了確認後に元handleをcloseする。False/ack read error/kill・wait・close例外/待機中の割込みでも同じownerを保持して再照合する。PIDによる再取得や別processの停止は行わない。診断出力に依存しない保持loopで、poll待機0.25秒・元cleanup30秒を保持する。

stop fenceを実workerへ渡す経路は未接続で、今回のcode追加による新native・業務workerは0。親がworkerを保持するだけでは、worker自身の元Job/process/thread/extra handle keeperや実Job回収を証明しない。

## 焦点証拠

新13＋既存4の17件、1.880108秒、fail0/error0/skip0、対象9 source/test/science pinは前後不変。変更2fileの明示path safety scanはpass。全repository safetyは先行e4cb23aの30秒timeout記録を未確認として保持する。

対象はinvalid fenceの未起動拒否、False/非bool/I/O例外でのkill/wait/readback拒否、root exitだけのclose拒否、True後のbounded cleanup、handle close失敗の原owner保全、True後のwait未確認でのfence保全、keeperのack error・sleep/kill割込み・close再照合、既定の正常/メモリ停止/未回収/cleanup割込みである。Popen/handle/ackは明示的なprotocol fixtureで、native Jobや実共有channelの証明ではない。

初回16件pass後に、True後のwait未確認から通常UnreapedWorkerへ落ちる経路を見つけてfenceを保持するよう修正した。この具体的な残存riskの17件gateを最終証拠とし、先行16件を加算しない。

rawは `artifacts/preformal-worker-stop-fence-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| focused-final.json | 3,820 | 56539e8039cb3d4e0e0b0a02e3be81308f8d732292a60b8e2c33a258ede75ee3 |
| focused-final.log | 3,328 | ec026d652a1a6bf6fed7c83dd542e3412b91048c9b1c7e8ca9eb14cc5566b819 |
| code-save-checkpoint.json | 594 | 7cdc2ad8285015d54285322f502e7e8b1c8c7e658f0e5df85affac9f5796f86a |

code-saveはHEAD=origin/cleanと9 working/Git pinを照合した。science plan/registry pinを変更していない。新CI [37578543252](https://github.com/tyaro/banto-ai/actions/runs/37578543252) はin_progress、各minor3,157件予定。

## 次の接続

initial-reader14/14 actorの前に、caller保持のrequest/policy pin、revision・root identity、元worker PID/creation identityへ結ぶ共有clock/stop/ackを固定する。markerがないだけでTrueにせず、stop後の新Job開始禁止と実Job回収済みackを検証する。request/stop/ackの読取り・保存・診断失敗でも、親Popen ownerと子Job ownerの保持を失わない。worker内のcritical keeperはPython終了に落とさず、既存予算内のinflight/partial archiveを保全する。

親supervisorのstop fenceが渡されたこと、子側が同じstopを観測すること、原Jobの終了とquiescent ack、source pre/post inventoryの照合を小さい単位で接続してから限定nativeを別exclusive rootへ準備する。旧138Job rootへの追加・再起動、全7役反復、上限緩和は行わない。旧runtime profileを新revisionへ読み替えない。

残CI37576149693（e4cb23a）と37578543252（01ab74f）は外部HEAD/workflow/run/attempt別に完了証跡を保存する。正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0、登録holdout観測未読、追加agent0、正式5残件を維持する。
