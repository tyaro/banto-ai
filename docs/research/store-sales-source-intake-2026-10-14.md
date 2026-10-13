# Store Sales 原本の受領と研究入力

受領日: 2026-10-14 JST

人がbanto-aiのトップに配置した `store-sales-time-series-forecasting.zip` を確認し、Git管理外の `data/public/store-sales-user-provided-20261014/` へ移した。ZIP内の7CSV、全memberのCRC・bytes・SHA-256、列名・行幅・行数・日付ラベルの範囲を確認した。モデル実行と変換は行っていない。

## 原本と利用条件

- 原本: `data/public/store-sales-user-provided-20261014/store-sales-time-series-forecasting.zip`
- [source manifest](../../data/public/store-sales-user-provided-20261014/source-manifest.json)
- ZIP: **22,416,355 bytes**
- SHA-256: `12e9c1dc4833cc804b3ff1515bd7b688f45fd8216fb2b340525036b006d625be`
- 申告取得元: [Kaggle Store Sales Time Series Forecasting](https://www.kaggle.com/competitions/store-sales-time-series-forecasting/data)
- 利用条件: **Subject to Competition Rules**。CC BY等へ読み替えない。agentは規約への同意・認証を代行していない。

今回のpinはユーザー提供原本から実測した値であり、Kaggleが発行した期待hashとの照合ではない。申告元・file構成・schema・実観測値の対応を保持する。原本やデータ本文をGitへ追加しない。ZIPは32MiB以下なので分割を要しない。閉鎖rootへ追記・上書きをしない。

## 実測の構成

| CSV | データ行数 | 日付ラベルの範囲 | 役割 |
| --- | ---: | --- | --- |
| train.csv | 3,000,888 | 2013-01-01～2017-08-15 | 日次の店舗×商品群のsalesとonpromotion |
| test.csv | 28,512 | 2017-08-16～2017-08-31 | 16日分の競技入力。sales列はない |
| holidays_events.csv | 350 | 2012-03-02～2017-12-26 | 休日・行事の種類、地域、振替 |
| stores.csv | 54 | — | 店舗属性 |
| transactions.csv | 83,488 | 2013-01-01～2017-08-15 | 日次の店舗取引件数 |
| oil.csv | 1,218 | 2013-01-01～2017-08-31 | 原油価格。43行に空欄がある |
| sample_submission.csv | 28,512 | — | 投稿形式の例。実売上の正解ではない |

train/testに54店舗・33商品群を観測。trainの日付ラベルは1,684種類。train/testの全列名と行幅は期待schemaに一致し、空欄を含む行は0。これは重複key、暦の連続性、ゼロと欠品、型・有限値の全品質gateの完了ではない。日付の範囲はCSVのISO日付ラベルを字句比較した結果で、timezoneや時刻品質の検証ではない。

train列: `id,date,store_nbr,family,sales,onpromotion`。testはsalesを除く同じ5列。全memberをZIP内でstream読取りし、121.8MBのtrain.csvを展開して新fileへ書かず、原本を保存した。

## 研究で扱える問い

複数年の暦・季節、販促対象数と商品群売上の関係を研究する候補となる。菓子品目に直接対応したSKUデータではなく、小売の商品群集計である。食品の商品群としてBREAD/BAKERY、GROCERY I、DAIRY等があり、研究する対象を一つ選んでから少数店舗へ絞る。

`onpromotion` は商品群内の販促対象品目数。施策内容・割引率・メーカー出荷ではない。過去の予定版と利用可能日時は今回の原本だけでは確定できず、実施値を起点で既知だった予定へ置き換えない。[公式データ説明](https://www.kaggle.com/competitions/store-sales-time-series-forecasting/data)

原油価格や店舗取引件数の将来実績を将来既知入力へ混ぜない。休日のlocal/regional/nationalと振替を区別する。販売0を欠品と断定せず、商品群salesの単位を菓子メーカーの個数・箱数へ換算しない。観測期間を選ぶ前に、日付欠落・重複・取引件数との対応と入力の役割を確認する。

競技testには正解salesがないため、初回の公開データ評価はtrain内に時系列の過去/将来を分けて設計する。今回testのschemaを読んだことを、モデルのtest評価実行や新しい登録holdoutへ読み替えない。大規模なモデル比較を開始せず、季節naiveと統計モデル一つの少量評価へ進める条件を決める。

## 保存と次のunit

原確認: `artifacts/representative-store-sales-intake-20261014-records`（complete閉鎖）。約10秒の処理で3,000,888行をstream確認。移動は元fileのサイズ・mtime/inodeが確認中に変わらないことを照合後、両絶対pathがworkspace内であることを確認したPowerShell Move-Itemを一度だけ実行した。移動後もfile identity/bytesを照合した。

本文保存: `artifacts/representative-store-sales-intake-20261014-doc-records`。Git後の確認は同git-recordsのpost-save/root-closedを優先する。失敗が発生した場合は原例外とprefixを保全し、元helperを再実行しない。

次は少数の食品商品群×店舗を選び、過去/将来入力の可用性、暦、単位、欠測・ゼロ、時系列splitを固定する入力契約を作る。原本の受領だけで将来販促の実用性・菓子メーカー精度・PSI採択を補わない。

既存automation PAUSEDを維持し更新0。実行側・記録側上限不変、登録holdout未読、native reader禁止、formal_permission=false/credit0。今回モデル・評価・試験・CI反復0。既存公開データroot・完成評価・元失敗は保持。
