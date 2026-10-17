# 入力・ラベル分離と仮定に基づく時点契約の検証完了

2026-10-15 JST。[事前契約](../research/demand-input-boundary-design-2026-10-15.md)に沿って、2013/14の保存済み470窓を入力・変換・ラベルへ分離した。23fixtureと、許可10店の原snapshot7300行からの独立照合がpass。今回は新fit・候補予測・score・2015内容参照/再評価を行っていない。四季の非悪化条件を達成したという性能結果ではない。

[Astra実装前確認](../research/demand-input-boundary-astra-review-2026-10-15.md)に加え、コード/保存結果の[方法・評価監査結果確認](../research/demand-input-boundary-astra-result-review-2026-10-15.md)を受けた。loaderに対する指摘はv2で修正し、v1のコード/complete成果も保持した。

## 分離したもの

| ファイル | 内容・境界 |
|---|---|
| inputs.json | raw past56/観測mask/日付、target14暦、既存同休業mean28、assumed_open_mask、営業unknown、keyとpolicy参照。actual/complete/raw_prediction/profile/encoded/scale値なし |
| transforms.json | full2013尺度、尺度・休業仮定の根拠期間とusable_from。origin特徴とcutoff時点の変換を別管理 |
| labels.jsonl | raw actual/null・観測maskとkey/target/仮定available_at。入力hashを変えない独立payload |
| label-index.json | byte offset/length/rowpin/identity/availability metadata。fitで可用性を確認してから過去rowだけdecode |
| binding.json | 各ファイルの独立pinとkeyの一対一対応。label hashや混在source pinはinput bytesへ混ぜない |
| issue-schedule.json | 2014Jan1+14*k、k0..25×FIT10をinput側で定義。label存在・完全性から発行対象を作らない |

新しいconsumer入口は[単一readのv2 loader](../../tools/demand_input_boundary_v2.py)。[v1共通schema/時点契約](../../tools/demand_input_boundary.py)を継承し、[migration/checker v2](../../tools/demand_input_boundary_check_v2.py)が旧混在packetを読む一回の移行を担当する。input-only consumerは入力と変換だけを受け取り、検査中は混在source/label/indexのopenとlabel decodeをspyで禁止した。

470=保存済み2013学習資料210＋独立定義の2014発行対象260。2013の元選別履歴は残り、分離によって母集団の選択バイアスが消えたとは扱わない。2013資料を将来の発行母集団へ転用しない。

## 時点契約と四半期cutoff

pastはorigin−56..origin−1、targetはorigin..origin+13。full2013尺度・2013だけを根拠とする01-01/12-25休業仮定は2014-01-01から利用可能とする。2013当時のprediction readinessは拒否し、2014cutoffで過去2013行を学習変換する用途は許可する。

| cutoff | 完全ラベル候補 / decode行 | 2013由来 / 2014由来 |
|---|---:|---:|
| 2014-01-01 | 210 | 210 / 0 |
| 2014-04-01 | 270 | 210 / 60 |
| 2014-07-01 | 330 | 210 / 120 |
| 2014-10-01 | 400 | 210 / 190 |

target末日<cutoffかつ仮定available_at<=cutoffを、label rowをdecodeする前に検査する。available_at==cutoffは許可、target末日==cutoffや利用可能日が翌日は拒否するfixtureを含む。全10店同発行日を同一groupとし、2014input-only readiness260/26groupを確認。将来の欠測有無を予測readinessへ入れず、cutoff前の完全性だけを学習候補の別条件にする。

日次contextは対象日翌日、14日labelはorigin+14日に利用可能という日単位の仮定。source dateの暦を使い、実配信時刻/改訂遅延/timezoneは不明で検証していない。Asia/Tokyo時刻での実運用再現や配信時点の証明とは言わない。Q開始で係数固定する規則はpolicy保存のみで、今回はモデルや逐次予測を作っていない。

## カナリア・厳密loader・独立照合

実470窓でtarget欄を全0/全欠測/大きい値/欠落へ変え、行順も逆転し、派生予測・profileへcanaryを置く5ケースを検査した。inputsのcanonical bytes/pin、2014発行group、契約readinessは全て不変。完全ラベルかどうかは別の情報なので、label変更に応じて学習ラベルの適格性が変わり得る点は維持する。

23fixtureはJSONオブジェクト重複key、record重複、余剰/入れ子field、NaN/Infinity/bool数量、長さ・日付・store/target/identity/観測mask、変換根拠・usable_from、availability境界、未来decode禁止spy、payload/rowpin改ざん、一対一key、label scenario、input group、単一read競合を検査した。

Astraはv1のhash照合後に別readでparseする競合余地を指摘。[補記](../research/demand-input-boundary-loader-review-2026-10-15.md)のとおり、不変v1成果を変更せずv2へ一回の上限付きread→同じbytesのpin照合→strict parseを実装した。23fixtureはv1の20＋この修正の3で、同じ成績探索の反復ではない。

独立readerは新契約moduleをimportせず、raw FIT10×2013/14の7300暦行からinput470のpast56、既定B、label470のraw target、2013尺度/休業根拠、identity/pins/offset、発行group、prefix台帳、scenario supportを照合した。元日2014Jan1の真0は10店全て保持。旧Bのコピー一致だけでなく、過去28日の観測weekday平均（真0含む/最低3）×同maskとの整合も確認した。これは既定入力の照合で、新候補予測・成績計算ではない。

## 観測のみ・欠測0仮定と評価条件

| 期間 | 窓数 | 真の観測日 | raw null | 仮定0を置く休業相当位置 | 観測完全総量 / 仮定0完全総量 |
|---|---:|---:|---:|---:|---:|
| 2013 | 210 | 2940 | 0 | 0 | 210 / 210 |
| 2014 | 260 | 3630 | 10 | 10 | 250 / 260 |

raw nullは観測へ昇格しない。評価用の欠測0は既定休業相当日だけ、その他の欠測は残す。休業相当日に正値がある場合もraw実績を0へ消さない。operating_statusはunknown。label scenarioの変換と支持数だけを確認し、今回MSE/過小/過大量を計算していない。

今後も調整は2014以前のみ、四季ごとの総量MSE非悪化・平均過小量/平均過大量非増加を同じ休業仮定のmean28とpairedで判定する。観測only/欠測0仮定は別採点、通常/元日は別表示。outer違反の事後B差替えを禁止するpolicyも保存した。既存2015の観測のみ/欠測0/元日/250窓成果は閉鎖rootに保持し、新たに内容参照・再評価しない。

## 確認できた範囲と残る制限

- 完了したのは、入力/ラベル境界と、明示した可用性仮定に対する契約チェック・原snapshot照合。2014は既読で独立性は回復しない。
- input loaderは全470行を読むので、早いcutoffから見て後のcontextもプロセス内には存在する。fit候補へ通さない契約であり、数量の物理隔離ではない。後続学習consumerはaccepted keysに限定する必要がある。
- LabelReader初期化は全payloadをhash用bytesとして読む。未到来labelをprefix内でdecode/数量利用しないことと区別する。trusted closed root/bindingのindex/pinsが前提で、hashは認証や任意Pythonへのsandboxではない。
- カナリアが示すのは固定contextに対するtarget欄からの非干渉。原値一致は独立readerの別の確認。実arrival/timezone、未決の新特徴の支持、新モデル挙動、独立性能は未検証。feature_support_for_new_model_verified=Falseを維持する。
- 特徴式・正規化・量変換・λ・過去校正/支持不足規則は未固定。今回完了をモデル学習準備完了や将来性能の認定へ拡張しない。

## 保存・OS別の実行結果

v2は16files / 3,208,422B、complete。child5.674524秒、sampled peak physical footprint224,609,072B、peak RSS264,126,464B。親900/子870秒・各2GiB・既存artifact/EvidenceStore上限内。Mac指標はOS hard limitやWindows private bytesではない。v1の20fixture/原照合completeと閉鎖root、旧source/model/state/変更/失敗も不変保持。

共通Mac/Python3.14.8は23fixture・migration/check・独立reader・文書整合がpass。Windows固有/nativeとOS依存包括suiteは未実行（Mac resource計測のみ）。新fit/候補予測/score/2015内容参照・再評価0、2016/17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部送信/commit/push/削除/本番採用なし。heartbeat PAUSED維持、明示依頼のAstra既存2名read-only。本有限工程を閉じ、新実験へ自動接続しない。

証拠: [v2 summary](../../artifacts/macos-demand-input-boundary-20261015-v2/summary.json)、[execution](../../artifacts/macos-demand-input-boundary-20261015-v2-execution-records/root-closed.json)、[readback](../../artifacts/macos-demand-input-boundary-20261015-v2-readback-records/root-closed.json)、[doc-records初回（Git起動失敗）](../../artifacts/macos-demand-input-boundary-20261015-v2-doc-records/root-closed.json)、[doc-records再閉鎖](../../artifacts/macos-demand-input-boundary-20261015-v2-doc-records-v2/root-closed.json)、[保存したv1](../../artifacts/macos-demand-input-boundary-20261015/root-closed.json)。

文書閉鎖初回だけ既定GitがXcodeライセンス未同意でexit69となったためfailed証拠を保持し、同梱Git 2.53.0を明示した文書検査で再閉鎖した。コード/入力/モデルの再実行はない。[OS検証補記](../research/demand-input-boundary-os-check-2026-10-15.md)。
