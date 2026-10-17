# 公開需要データの休日・営業日と予測時点可用性

2026-10-14。取得済み原本のカレンダー/店舗属性と、2013〜2015年の保存済み販売prefixを確認。新モデル・予測評価は実施していない。

## この確認を行った理由

[自己対3店舗の履歴比較](store-sales-related-comparison-2026-10-14.md)は関連追加の改善を得られなかった。販促予定がない中で、次に使える将来入力を過剰に仮定しないため、公開原本の休日/店舗情報を調べた。

原ZIPの既保存hashを照合し、`stores.csv`と`holidays_events.csv`だけ新たに読んだ。train/test/販促の原CSVは読んでいない。memberのbytes/SHAが元manifestと一致。既存rootは変更せず、原CSVは新ローカルEvidenceStoreだけへ保存した。

## 原カレンダーの意味

休日/行事350行の内訳はHoliday221、Additional51、Bridge5、Event56、Transfer12、Work Day5。transferred=Trueは12行。店舗1・2・3は全てQuito/Pichinchaで、地域・都市を一致させた適用候補は各187行。店舗typeはD、clusterは1/2が13、3が8。同じ都市の3店舗であり、地域をまたぐ需要の汎化比較ではなかった。

[公式データ説明](https://www.kaggle.com/competitions/store-sales-time-series-forecasting/data)は、元の休日と振替先を区別し、地震後の販売変動にも言及している。CSVの同日イベントを全て未来既知にする理由にはならない。

カレンダー列はdate/type/locale/locale_name/description/transferred。公表日時・改訂日時はない。店舗表にも個別営業日/営業時間はない。National/Regional/Localを区別して適用し、元のtransferred行を単純な休業指示へしない。Event/Bridge/Work Day等も、その決定を発行時点で知った証拠なしに予測へ渡さない。地震発生日以降のイベントラベルを事前の予定として与えることはできない。

## 過去だけで作れる固定月日の候補

2013〜2015のNational/Holiday行だけで、3年とも同名・同じ月日である候補を8件抽出した。これは**名目上の記念月日の季節指標**で、将来の法定休日・振替先や店舗休業を確定するものではない。例えば10月9日はprefix内でも振替の有無が年によって異なる。

保存済み2013〜2015年の3店舗販売量で、その名目月日の実績を、その日より前28暦日の同曜日平均と比較した。最低3観測がある場合だけ比較。0は観測0として保持し、未記録はnullのまま。表の比率は有効行の実績合計/比較平均合計で、日ごとの比率平均ではない。因果効果や予測成績ではなく、次の問いを作る過去側記述である。

| 月日 | 原description | 観測数/9 | 実績0 | 比較可能数 | 数量加重比率 |
| --- | --- | ---: | ---: | ---: | ---: |
| 05-24 | Batalla de Pichincha | 9 | 0 | 9 | 0.986 |
| 11-02 | Dia de Difuntos | 9 | 0 | 9 | 0.749 |
| 05-01 | Dia del Trabajo | 9 | 0 | 9 | 1.035 |
| 11-03 | Independencia de Cuenca | 9 | 0 | 9 | 1.106 |
| 10-09 | Independencia de Guayaquil | 9 | 0 | 9 | 0.947 |
| 12-25 | Navidad | 0 | 0 | 0 | — |
| 08-10 | Primer Grito de Independencia | 9 | 0 | 9 | 0.965 |
| 01-01 | Primer dia del ano | 9 | 9 | 6 | 0.000 |

元日は全9件が観測0、うち2014/2015の6件で比較可能だった。クリスマスは全9件が未記録で、比率を推定できない。人のクリスマス休業という指摘と整合するが、個別店舗の休業表で確認した証明ではない。欠測を0へ変えて休日の精度を作らない。

他の記念日には平均より小さい例・大きい例の両方があり、全休日に一律の増減を設定する根拠にはならない。各記念日は最大3年×同都市3店舗の少数で、9件を独立な標本数としてCIや有意差へ使わない。販促・振替・曜日・店舗状況の影響が重なり、祝日の因果的倍率ではない。

## 次に進められる研究

販促履歴を待たず、過去prefixから固定した月日だけの季節指標について、小さな追加比較を設計できる。将来のEventやTransfer行を参照してフラグを作る経路は使わない。名目月日指標と、真の営業日/休業予定入力は別の意味として扱う。

次unitは、単純な同曜日平均を基準に、**名目月日の補正を過去で推定する一方式**の条件を先に固定する。元日の観測0とクリスマスの欠測を混同しない代表確認が必要。支持数が少ない補正を強くし過ぎない設計、未知/未記録は補正を作らない規則、過去学習と回顧評価の境界を決める。ここでは補正倍率の採択・将来予測は未実施。既研究起点の再実行を避け、イベントを含む新しい少数窓を出力前に固定する。

実績売上から潜在需要、菓子メーカーの出荷単位、発注cost、PSIの休業期間の需要を補っていない。営業実績がない日の誤差は測れない。公開データだけで研究できる問いを続けるが、足りない意味をモデル性能で埋めない。

## 保存と境界

原カレンダー/店舗確認: `artifacts/representative-store-sales-calendar-20261014-records` complete閉鎖、全stdout/stderr/exit0はcalendar-launch-records。過去月日記述: calendar-prefix-records complete閉鎖、同prefix-launch-records全stdout/stderr/exit0。文書はcalendar-doc-records、Git後calendar-git-records post-save優先。新fit/forward/旧評価/試験/CI反復0、閉鎖root追記0、原失敗保全。

既存automation PAUSED、直接研究ACTIVE。CARE手動完了報告待ち・自動確認0。実行/記録上限不変、追加agent0、formal_permission=false/credit0/native reader禁止/登録holdout未読/正式受入未完了。原本・観測本文・fit/生予測はGit送信しない。
