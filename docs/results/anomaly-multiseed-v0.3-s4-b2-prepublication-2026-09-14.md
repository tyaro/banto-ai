# S4-B2 公開前の証跡保存・選択解放の検証結果

日付2026-09-14。基準5c76c582607bab9a2a6cd612777ccf89c0249b40。
実装savepoint **b9b7fb168641cf078dcb5fa5692f13e709fabedf**。

**証跡保存成功後に選択handleを解放する接続部品を追加し、最終72 testsがpass。**
独立レビューと追加integration testの確認で新規P0〜P3は0件。
[設計書](../anomaly-v03-prepublication-design.md)を参照。tests/fixturesの注入backend部品である。

## 到達した範囲

HandleOwnerへ同期borrowと、prepare/seal_payload/verify_finalのpending中の選択解放を追加した。
各phaseは1回、各handleも1回だけ解放する。closed/unknownは借用・再解放できず、終端finishも再closeしない。
借用中のfinish/release/再borrowや、その拒否の握り潰しは停止する。
生きた子を残す親だけの解放を拒否し、選択群は取得の逆順で解放する。

EvidenceBarrierは全toy payload/marker bytesとowner pin/descriptor観測をcanonical記録へ固定する。
journalの独立marker hashと全owner pinに再構成照合し、保存成功応答を得てから解放する。
保存不明はunknownで停止し、確認済み保存後のclose失敗はsavedを残す。再保存や既存証跡削除はしない。
root/stage/marker等の保持対象はprotectedで解放を拒否する。

payloadは8 files/各64KiB/合計256KiB、marker16KiB、descriptor各2048 bytes/最大32 slots。
保存要求は各512KiB/3段階合計1.5MiBまで。これはprocess全体のメモリ制限ではない。
descriptorの意味や実native観測は認証しない。全acceptance/formal/authenticated flagsは未受入を維持する。

## 検証とレビュー

初回は新規19＋既存52＝71件pass、0.079秒。
独立レビューの欠陥所見は0。補強案を受け、同じowner/barrierを使う通しの1 methodを追加した。
prepare→seal_payload→verify_finalの3記録と選択解放、既存BoundRenameのpayload/.complete両操作、
終端finishまで通し、各handle一度の解放、3記録保持、名前のidentity、予算合計を確認した。
**最終20＋既存52＝72件pass、0.050秒。両回failure/error/skip/expected failure/unexpected success0。**

通常故障・応答喪失・資源停止・二重操作・再入握り潰し・protected解放・不正選択・容量超過を含む。
再hashしたflag/field/bytes/marker/source/owner pin差替えも拒否する。
同一ownerの3段階を通す試験は模擬handle/name表であり、同じ権限を実Win32で取得できる証明ではない。

1 methodだけは小さな通常tempfileをexclusive作成し、hash読戻し、既存file拒否、handle解放後のbytes保持を確認した。
この通常ローカル保存はprivate DACL、flush、電源断耐久性、実失敗fixtureの回収を証明しない。
試験用tempfileは終了時に清掃し、既存の失敗fixtureは操作していない。

最終独立確認は追加通し試験と設計書を含み、残件0。担当の試験/native/ネット/編集なし、進捗ポーリングなし。
repository safety/staged diff-check pass。最終試験の8 source filesは確定Git blobとraw bytes一致。
ローカルCPython3.14.0の選抜試験で、旧Linux CI・Windows全受入へ件数を加算しない。
src/科学config/schema/registry/正式OS pin、本流889cfc3は変更なし。push/merge/CI起動なし。

## 記録と環境条件

新規ignored root artifacts/prepublication-2026-09-14/へ初回・最終を分けて保存した。

| 記録 | bytes | SHA-256 |
| --- | ---: | --- |
| initial-checks.jsonl | 50918 | 4b3bbacb2d2199c2d723ef482c48aab58dffb817f68202c186511cdda7cc0a47 |
| final-checks.jsonl | 51679 | 160e9ea2f21cfefc0becc008fcce22a72ea111f3f2e8d1bd4ca6fd9fc9158b34 |
| resources-final.json | 589 | 47c74364e3070d7570f9706ec81f6023f234f335d6c3d113ba650ea2e9312a51 |

JSONLに各test ID/結果、Python、基準revision、実行時raw source hashを記録した。
savepoint-evidence.jsonに確定commit、raw/Git blob照合、再検証の理由とユーザー条件変更を保存した。

ユーザーより別project連続稼働テストの終了通知を受領。同時負荷を避ける追加抑制は解除し、
通常のRAM/disk確認と工程別savepointを継続する。別projectへの操作はない。
この通知でB1の終了済み試行枠や正式受入条件を更新・再開しない。

開始UTC06:45:05Z RAM空き8.37GiB/C105.24GiB/D59.78GiB。
最終06:55:54Z RAM8.39GiB/C105.21GiB/D59.78GiB。
build26200.9445、boot2026-09-09T10:43:08.5000000+09:00。
D空きは前回より開始時点で減っていたが、原因は調べず本作業やリークへ帰属させない。
今回の短い試験・記録processは終了し、常駐処理なし。新runtime導入や共有環境変更なし。

## 次の接続境界

途中取得失敗時の所有移管、writer解放後の異なる権限での再取得、実nativeのidentity/ACL/flush、
新規private sinkの取得・部分write・保存失敗の証跡を具体化する。
今回のownerは構築時に固定slotを渡す前提で、実取得途中の所有追跡を追加したものではない。
native試行の対象・時間・メモリ・空きdiskの上限を定めてから接続する。
B1枠の流用なし。native全受入、正式OS整合、VM digest、runtime closure/consumer、S4受入は未完了。
