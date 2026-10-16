# Astra 入力・ラベル境界の実装前確認

2026-10-15 JST。人の依頼で方法担当 /root/astra_method_review と評価監査担当 /root/astra_process_audit（gpt-6-astra）が提示案をread-onlyで確認。編集/fit/予測/score/2015内容参照/追加agentなし。以下は回答の要約。

両担当は概ね妥当とし、次を実装条件にした。現段階は設計確認であり未実装のpass認定ではない。

- origin時点の原contextと、cutoff時点の尺度/休業仮定を別schemaへ。full2013尺度は2014学習の2013行に使えるが、2013擬似予測は不可。一律に2013行を学習候補から消さない。
- input hashへlabel hash/完全性を混ぜない。別manifestでkey/schema/file pinを結合。label変更でinput bytes・発行group・入力適格性は不変、学習ラベル完全性は変わり得る。
- 470件は保存済み学習資料で、元の生成/選択履歴が残る。将来の発行母集団をlabelの行数/存在/完全性から作らない。2014発行日×FIT10は独立した固定カレンダーで定義。
- 日付と配信時点は別。past56日<originだけでは実際に届いていた証明にならない。contextは翌日、14日labelはorigin+14日に利用可能という明示的日単位仮定に留め、実測timestamp/timezone検証とは言わない。由来期間だけでなく派生物のusable_fromも検査。
- null/真0を維持。01-01/12-25は休業の仮定、営業unknownのまま。future maskでraw labelを上書きしない。mask名をassumed_open_maskへ。
- strict allowlistは入れ子まで。JSON内の重複key/レコード重複/余分なfield/NaN/Infinity/bool数量/日付順/長さ/store/identity/target相違/改ざんを別々に拒否。
- 同日全10店を入力側で固定。label欠落・値・欠測・順序を変えるcanaryでも発行対象と入力適格性を変えない。対応しないlabelは結合時に拒否し、未来欠測で店舗を発行groupから除かない。
- migrationの混在source読込と、予測consumerがlabelを参照しないことを分けて記録。今回の完了表現は『分離schemaと明示した可用性仮定に対する契約チェックを実装・照合』まで。逐次予測/独立性回復/実際の到着時点の実証とはしない。

470=2013の210+2014の260、Q開始以前完全label候補210/270/330/400はmetadata照合基準。入力支持/独立例/回帰情報量とは呼ばない。旧Bのcopy/pin一致と再計算による整合を区別する。新fit/候補予測/scoreへ接続せず終了する設計を支持。
