# 小型独自モデルのデータ・学習前準備（2026-10-14）

## 今回の到達点

独立モデルの最小実装確認に続き、固定MetroPT探索日を読むadapterと、full/self-onlyを同stepで進めるtrainerを実装した。この記録時点で実データ学習0step。
[adapter](../../models/mini-transformer/data.py) / [trainer](../../models/mini-transformer/train.py) / [新確認](../../models/mini-transformer/check_preparation.py)。
既存10構造確認は反復していない。

新9種類を確認した。初回7bodyは6passed/1failed（sandbox tempの書込みとcleanup拒否）。workspace内の新専用fixtureへ修正し、失敗1件だけpassed。別に指標手計算1件、原例外保持1件を追加して各passed。
合計9distinct/10body、複数source/runの証拠で、最終sourceで単一9success runとはしない。原failed/rootと返却stdout/stderrを保全している。

| 新確認 | 内容 |
|---|---|
| window | train128..832、validation864+32k、test1152+32k。context/label切出しとsplit跨ぎlabel拒否 |
| train尺度 | train864だけからpopulation std。validation/testの大幅変更でも尺度不変、等差数列の手計算 |
| 品質 | 全3targetのcontext/label品質で除外。欠測を埋めず、不能windowへbatch要求拒否 |
| 行対応 | target順/単位/60秒時刻。duplicate timestamp/誤単位を拒否 |
| batch列 | local RNG seed20261014、128×8共通origin列、global RNG不変更 |
| 選択とoptimizer | 同値なら早いstep、nonfinite拒否、AdamW指定と未更新state |
| 出力root | 未使用root、上書き/閉鎖後追記拒否 |
| 評価指標 | 固定分位点例でMAE/pinball/WIS/coverage/width/lead/固定尺度集約、点baselineを手計算 |
| 原失敗 | 入力例外＋診断保存例外のfixture。stderrへ双方を保存し、同じ最初の例外objectを再送出 |

Astraのread-onlyレビューで、閉鎖前complete表示と保存側二次例外を修正した。summaryはcandidate-completeで、root-closed成功と合わせて完了と判定。stdout completeは閉鎖後で、stdout障害時も閉鎖rootへ追記しない。保存できないときはstderrへ元例外/二次例外を記録して元例外を再送出する。
32/64/96/128共通stepのjournal/best/checkpoint対応を別名prefixへ保存。学習・validation・test推論時間を分けて測る。
これらのfixtureは実障害の全種類やOS強制中断を網羅する証明ではない。

## 探索用データの実対応

指定24h observationsの実SHAを照合: d74b53979a051270f045265ccce3a582f3164500f8c7d3a8cf6940ce9a1a5077 / 1502235B。
fingerprint e6210e4e48e05c025fc8895ddeddf0c53a49dc53fd1c2f49e8c3272a3c7b37b0。metadata6fileも保存fingerprintのdigestへ照合した。
対象tp3(bar)/oil_temperature(ºC)/motor_current(A)、1440minute、bin-end00:01から24:00、train864/validation288/test288。
有効origins705/9/9、今回3target windowの品質除外0。過去contextの前split跨ぎは許し、labelの跨ぎは拒否。
train scale [0.5197559595108032,2.9969608783721924,1.8041737079620361]、floor [0.005197559483349323,0.029969608411192894,0.018041737377643585] をtrain prefixだけから固定。
全3targetの正常確認や故障なしの認証ではない。登録holdout未読。過去評価済み公開日なので探索用であり、未使用holdout・実設備汎化の実証へしない。

元metadata選択でsplit.json/transform.jsonの誤った名前を読もうとしたtool errorは、manifestのsplit-manifest.json/transform-config.jsonへ訂正して観測記録を保存。元payload変更0。原環境warningはexit0tool観測でモデル学習失敗へしない。

## 資源と原保存

初回準備checksは2.623456500004977秒、OS peak pagefile1036541952B。1件のcontinuation0.00472秒/903614464B、metrics0.00312秒/937435136B、原例外fixture2.79859秒/987414528B。
optimizerの作成だけで、optimizer step0。OS counterによるcheckpointで、blocking中断/allwriter/global/native容量証明ではない。

実行900秒/private2GiB/output1GiB/single32MiB/files32を維持。trainer normal24file/768MiB枠、failure8file/256MiBを残す。新root、一回保存、最大checkpoint32MiB、source/input/schedule/initial/8checkpoint/4prefix/2予測/journal/summary/closureを23fileで計画。
EvidenceStore16MiB/512entry/256KiB part/失敗予備2MiB16entryも不変。

原保存は artifacts/representative-small-model-data-inspection-20261013-records、representative-small-model-preparation-20261014-{check,continuation,metrics,first-error,doc}-records。
fixture2rootは output-fixture / first-error-fixture の20261014専用root。閉鎖root追記・元failedの書換え・同じ完成確認の反復0。
Git後は artifacts/representative-small-model-preparation-20261014-git-records のpost-save/root-closedを優先。

## 次の一回と停止

固定recipeの128共通step pairを一度だけ実行し、各variantの4validation候補から選択後、探索testを各一度評価する。testでrecipeを変更せず、grid/追加seedへ広げない。異なるC120/H15の旧TimesFM結果を同条件比較へ流用しない。
工程失敗では原prefixを保全し、自走をPAUSEDにする。解消不能な入力・許可・環境・判断の不足でも同じ停止方針。
次の独立した運用区間や行動/必要lead timeは未確定であり、単日探索の結果だけでBanto採択・自作TimesFM3再現成功を宣言しない。
formal gate=s4_acceptance_not_frozen / formal_permission=false / credit0 / native reader禁止。
