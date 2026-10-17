# v0.3 共有clock / stop / quiescent ackのmetadata契約（2026-10-07）

## codeと固定値

code `aaca57c9749fa4970919e2596f6a884b6851d2b5` をoriginへpush済み。[ParentChannel / ChildChannel](../../src/banto_ai/anomaly_v03_preformal_worker_stop_channel.py)を追加した。initial-readerのみを対象に、caller保持request pin、revision、measured leaf rootとdirectory identity、外部policy raw pin、parent/workerのPID・creation_time_100ns・start_token、nonceへframeを結ぶ。

Parentはlive samplerを持つcaller budgetからstarted_at/wallを取得し、同じmonotonic implementationを記録する。新rootは測定leaf内の未使用pathのみ、wallは既存1800秒以下、frame32 KiB・Job lease64件。共有clockを実native process間で測定した証拠ではない。policyはraw pin・revision/private Job ownershipを結ぶmetadata確認であり、Git executable/loaded codeの検証を代替しない。

bindingはcallerが保持する元Popen._handleだけへcreation観測を結び、expected binding pinをwrite前に保持する。部分保存やreadback失敗後に別workerへ再bindしない。Childは自己creation identityとbindingを照合し、binding待ち・deadline・stop・invalid metadataの間は新Jobを拒否する。

## stopとack

Parentのfenceはexact request/binding/original Popenを再照合してno-new-jobs stopを一回保存する。ack不在はFalseで、root exitだけを許可にしない。Childのstopはlatchedで、quiesceやack保存失敗の後も再armしない。

Childのactive lease・元critical ownerが残る間はackを拒否する。finish_jobはexit_confirmed/handles_closed/raw_preservedの全てが明示Trueの場合だけleaseを終える。これらはcallerの宣言を確認するstate機構で、native handle close自体を観測しない。実owner/receiptをこの宣言へ結ぶadapterが必要である。

ackはrequest/binding pin、worker creation identity、no-new-jobs、完了lease数と測定root内のproof path/pinを持つ。Parentには必須のnative quiescence verifier callbackを渡し、callbackの明示bool判定に従う。metadata ackだけでTrueにはしない。True判定後にもrequest/root/policy・ack・binding・proof bytesを再照合し、検証中の差替えを拒否する。native verifierはまだ未接続。

root/pathsのcanonical absolute containmentを確認し、dotdotや測定root外のproofを拒否する。frameや旧rawを上書きして回復せず、失敗raw/rootを保全する。metadataのI/O/検証例外は親stop fenceで元Popen ownerを保持する経路へ返す。子のprobeはinvalidをlatched stopとし、元errorを保持する。実子Job keeperのPython終了保全は次の接続単位。

## 焦点証拠

最終21件、15.486593秒、fail0/error0/skip0、9 source/test/science pinは前後不変。変更2fileの明示path safety scanはpass。全repository safetyは先行30秒timeoutの未確認を維持する。Popen/creation identity・clock・native verifierはprotocol stubで、新native/業務worker/追加agentは0。

対象はrequest外部pin・caller clock、binding待ち、ack不在とstop伝播、deadline、policy/request/creation改変、元Popen以外の拒否、active/critical ownerのack拒否、exit/close/rawの三条件、quiesce後の無再arm、必須verifierのFalse/非bool、proof差替え・検証中差替え、root外/dotdot、ack I/O失敗、closed sampler/過大wall/未来clock・root再利用の未起動拒否。

初回20件では19pass・missing bindingのpending判定1fail。bounded file readerが欠落をvalidation errorとして返していたため、binding pathの明示missing判定を追加した。初回focused.json/logを保全し、proof検証中改変の試験を加えた最終21件を証拠にする。先行20件や完成済みstop fence17件を加算しない。

rawは `artifacts/preformal-worker-stop-channel-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| focused-final.json | 3,314 | b54d0413966ae36e17a20f1fe5356ba8c4172d3b458a81e4c9bf8619d66d84c8 |
| focused-final.log | 4,371 | d090b2b4c586fd027324453683e2ab89f9175bf678e3ae640d6b46f9e3e20e32 |
| code-save-checkpoint.json | 566 | eeb6b477ba263c4c957d9255a7789dddabd66d2d262a9ec2c2fb8ddc4283fcd1 |

code-saveはHEAD=origin/clean、9 working/Git pinを照合した。science plan/registryを変更していない。新CI [37581339092](https://github.com/tyaro/banto-ai/actions/runs/37581339092) はin_progress、各minor3,178件予定。先行e4cb23a/01ab74fのCIも未保存で、各外部HEADへ固定して完了時に照合する。

## 次の実接続

実worker invocationでParent.create/on_started bind/stop_fence、Child起動時のbinding-ready handshake、子Job probe、元Job/process/thread/extra handle keeper、raw保全・Job quiescence verifierを結ぶ。binding/stop/ackの部分write・診断失敗でも元ownerを失わないようにする。standalone channelのSOURCE_NAMES追加やruntime profile準備は、実readerがこれをimportする接続単位で行い、旧14/14在庫・旧source pinを読み替えない。

initial-reader actorのpre/post sourceとnative call inventory・compact証拠・失敗時partial rawを同revision/rootへ固定してから限定nativeを準備する。現在worker invocation/actor・実native proof verifier・共有Job probeは未接続。既存138Job rootへの追加・再起動、全7役反復、上限緩和は行わない。

正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0、登録holdout観測未読、正式5残件を維持する。
