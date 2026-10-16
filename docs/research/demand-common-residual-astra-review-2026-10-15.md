# Astra prefix受渡し・単一残差モデルの設計と結果確認

2026-10-15 JST。既存方法担当 /root/astra_method_review と評価監査担当 /root/astra_process_audit（gpt-6-astra）へ人の「続けてください」に基づき継続相談。双方read-only、新計算・編集・再fit・2015内容参照なし。以下は回答の要約。

## 実行前

accepted keysを渡して全データから検索させず、許可rowの具体的入力/確定ラベル/cutoff変換だけをfresh payloadへコピーする。consumerへ全470入力・reader・index・sourcepathを渡さない。API境界でありPython sandboxとは呼ばない。

固定2特徴と切片、全係数を罰するλ=1の一仕様は妥当。損失を重み総和1の平均MSEと定義し、未支持cellの再配分を結果後に変えない。2×週差は未来mask期待量ではなく過去変化の14日換算説明変数で、両特徴は独立証拠でない。入力支持だけの監査を先に行い、結果で特徴/λを選び直さない。

prefix監査・独立reader完了後の別契約に、beta用のfeature適格n_qs、alpha用の同Q全complete集合（D=0fallback含む）、floor→固定D→alpha順、B=0/支持不足/数値失敗を明記すれば2014-only一巡へ進めると両者が確認した。beta/alpha同じラベルの内部最適化で独立校正でない。前Qの確定ラベルを次cutoffの固定規則で使うことは許可するが、同originの未到来target利用やouter後差替えは不可。全係数ベクトルbeta=0と切片beta0を混同しない。

## 結果確認

方法担当はコード・契約・保存状態を確認し、「学習支持は広がったが、固定された補正方向が過去同季節のリスク制約を通らず、全Q補正停止」が正確とした。Q1はover、Q2/Q3はunder上限0、Q4はC<0/MSE上限0に加えてover上限0。固定Dの幅をさらに小さくするだけでは厳密非増加を回復できないが、別の特徴/λ/方向一般の不可能性ではない。eligible=trueも全B同値による条件充足で、改善・補正有効性の証拠ではない。

評価監査担当は予定通り一巡終了・救済なし・採用なしを支持。全40cellは構造的支持で独立標本/安定性保証でない。非ゼロbetaを推定したが過去校正alpha0で止まった点を、支持消失やouter後B差替えと区別する。全Bは予測力・安全性の実証ではなく、追加改善0は本固定仕様だけの結論。

双方の回答時点でcommon独立readerは実行中と明記された。後に親agentがreadback complete/別solve・有理数境界・48scalar passを確認して[結果](../results/demand-common-residual-2026-10-15.md)へ保存した。エージェントがテストや独立readerを再実行したとは主張しない。2014既読・内部校正・2015停止を保持し、一巡後にλ救済/特徴追加/2015確認へ接続しない。
