# 架空480区間のproducer/campaign由来anchor案 v1（未採択）

この文書はS4前の架空登録形式fixtureを結合するための**契約案**である。実登録holdoutの実行許可、正式評価credit、S4採択を与えない。g02の１区間６評価と、別由来の40 cluster/50,000 drawを結合したものとして扱わない。

## 共有anchorと保管

campaign controllerは最初の生成子を起動する前に、次のcanonical JSONを一度だけ確定する。raw bytesの`{bytes, sha256}`をcampaign出力rootの外に保持する。anchor中の文字列やdigestを個々のchunkへコピーしただけでは、同一producer由来の証明にはならない。

| 項目 | 固定する内容 |
|---|---|
| campaign識別 | 新規の一意な`campaign_id`、`mode=preformal-fixture`、`invented_only=true`、専用root、契約版 |
| 科学的登録 | 凍結registry raw pin、順序付き480区間/2,880評価identityの計画hash、40 seed×12 layout×２strata×３candidateの数と順序 |
| 生成方法 | recipe IDと引数、seed消費の有無。`hand-normal-v1`は固定手作り系列であり、登録seedを消費しない |
| 実行入力 | producer/controller/readerの選定revisionとsource byte pins、予定runtime policy、各役割の責任範囲。選定fileの照合を完全source/runtime閉包と表示しない |
| 資源 | producerから保存reader・行結合・算術・文書・監査・公開後readerまで測る外側予算の上限と対象root、外部入力の容量集計範囲、停止規則 |

計画identityは凍結registryから再構成して照合する。`campaign_id`は衝突回避用であって信頼の秘密鍵ではない。anchorの作成者、保持場所、raw pinを実行記録で特定し、同じanchorで二つ目のcampaign rootを開始させない。

## 所有実行と区間記録

controllerが480区間を順に所有する。各起動前に、anchor pin、区間番号、attempt番号、凍結６identity hash、専用attempt root、予定22-fileの正確なpath/上限、入力source/runtime期待値をinvocationへ固定する。決定的fixtureで起動前の出力pinsetを作る場合は、そのraw pinを**attempt rootの外**に保持し、生成後の実rawと一致させる。

各attemptでcontrollerは子のPIDと作成時start token、invocation pin、開始/終了runtime、supervision、exit code、回収完了、停止理由を記録する。PID/start token/exitは子の自己申告だけで済ませず、controllerのOS監督結果と照合する。生成子が保存したreceipt/report/registry/savepointと全payloadは親または別所有readerがrawを再読取りし、各`{bytes, sha256}`、物理path、６identity/最新attempt、観測→profile/score→主/slice行を照合する。readerにも独立のPID/start token/exit/回収記録を要求し、結果pinをattemptへ結ぶ。PIDsだけでは再利用や別実行の混同を防げない。

controllerはattemptごとにanchor hash、`previous_sha256`、連番、区間/attempt、状態、子とreaderの証拠pin、22-file pin、６行pin、予算標本/停止理由を含む追記recordを保存する。record countと最終head hashはjournal外へ保持する。失敗と再試行は上書きせず全履歴を残し、integrity failure、source/runtime変化、未回収子、予算停止、欠損したraw/pinではfail closedする。異なるanchor、孤立attempt、重複・欠番・順序違い、失敗した最新attempt、宣言だけのworker exitも拒否する。

## 集約の出口

全480区間の**最新成功attempt**が同一anchor、連続journal、凍結identity順、各６行の保存raw再照合と所有子終了確認を満たした場合だけ、2,880行を40 seed clusterへ集約する。clusterは各seedの12 layout/72評価が揃ってから確定する。各集約出力にはanchor pin、journal head/count、入力行pin集合、集約実装source pin、資源receiptを保持する。ここまで成立しても架空データだけなら`registered_observations_read=false`、`campaign_evaluations_credited=0`、`formal_permission=false`、`promotion_allowed=false`を維持する。

## 現在のg02との距離

[g02起動前pinset](../artifacts/anomaly-v03-preformal-generated-pinsets-g02/pins.json)はchunk 0の22 file/131,144,119 Bと選定sourceを固定し、[g02予算result](../artifacts/anomaly-v03-preformal-registered-attempt-g02/budgeted-result.json)は生成子・reader子のPID/start token/exitと１回の共有予算を残す。[保存receipt](../artifacts/anomaly-v03-preformal-registered-attempt-g02/saved/receipt.json)は最新attempt１、６評価であり、[保存savepoint](../artifacts/anomaly-v03-preformal-registered-attempt-g02/saved/savepoint.json)は個別root・区間番号・`campaign_completed=false`だけを持つ。後続の[再読取り](../artifacts/anomaly-v03-preformal-saved-row-reread-r01/result.json)はこの保存rawを別の予算で検証した。

g02には共有campaign ID/480計画hash、残り479区間、controller所有の区間間journal/head pin、全工程の単一外側予算がない。`anomaly_v03_registered_fixture`の480区間や別rootの40 clusterはcallerが与えたfixture宣言で、g02の所有producer証拠へ昇格させない。g02のrecipeは登録seedを消費していないため、架空480区間を満たしても実S5 holdoutの代替にはならない。

S4前の受入は架空固定入力と正式pin上の最終dev８/smoke２、platform・source/runtime・容量予算の確認で進める。実holdout 40 seed/480区間はS4採択後のS5で一回実行し、S6で全件を独立再監査する。本案の実装・試行はその開始条件も結果も変更しない。
