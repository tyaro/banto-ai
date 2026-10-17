# 保存済み720評価の検出遅延・条件別集計（2026-09-25）

全120区間・720評価の保存済み判定を読み、検出遅延と条件別の件数を独立に集計した。10,368,000 score行と14,400異常事例の予定母数・重複・欠落を確認し、seed別90表・用途別18表すべてが前工程の検出件数・警報件数・利用可能率と一致した。関連32試験通過。新しい観測・検出器評価・score再計算・実データCIは0。

## 集計の意味と対象

ここでいう条件別集計（slice）は、同じ保存結果を「設備別」「運転段階別」「欠損の有無別」等に分けて見るもの。試験区間を追加した意味ではない。開発用dev 8 seed/576評価と動作確認用smoke 2 seed/144評価を分け、各seedの12 layouts・2条件・3候補を保持する。coreとquality-stressを足したoverallは同じ結果の合算であり、新しい評価ではない。

入力は外部SHAを持つ前回保存点から認証済みcounts・独立score/ledger監査報告をたどり、その監査に記録された720評価JSONの全bytesをhash照合して読んだ。読取対象12,855,219,166 bytes。全payloadを読む理由は、既存の要約には今回必要な各時刻の品質・発生前後の位置がないため。観測からscoreを再計算せず、過去に検算済みのscore・matchingを利用して分類・加算する。区間119はverified attempt2だけを使い、失敗attempt1を保全した。

## 分類と母数

| 対象 | 分類 | 数え方 |
| --- | --- | --- |
| 異常事例 | class、equipment、mode、class×equipment×mode、test-cycle、event-start-phaseの6軸 | 各軸は1評価の予定20事例を完全に分割。予定0のセルも保持し、検出件数・recall・遅延分布を保存 |
| score | full-target、signal×mode、phase、context、当該targetの現在/前時刻quality、fault-quality-overlap、profile-status | 各軸は1評価の予定14,400時刻・信号を完全に分割。利用不能・低scoreも母数に含む |
| 発生前後 | event-offset −2、−1、0〜5秒（scoreの9軸目） | 40計画eventの指定targetへの参照。重複する参照を許し、上記scoreの排他的分割とはしない |
| 設備警報 | raw-event / grace / clean | 設備単位の予定秒数、全episode、未対応episodeを保存 |

scoreの比率は`observed`（その条件に属する予定済みの試験内score行）を母数とする。`threshold_exceeded`は閾値超過の時刻数、`signal_onsets`は連続条件が成立した信号警報の開始数で、別の量として保存する。設備警報の正解率を異常class別へ割り振らない（class precisionはnot_applicable）。

- event-offsetは毎offset40参照のうち、10件のignored eventが指定するload_proxyを`unscored_target`として保持する。load_proxyは8つのscore対象に含まれない。開始前の負offsetは`outside_test`に記録し、常にplanned = observed + unscored_target + outside_testを確認する。除外分を「利用不能なscore」と混同しない。
- contextは設備全体の計画event区間を使い、raw-eventをgraceより優先する。coreで無効なquality eventも凍結済みclean除外計画に含め、clean露出は1評価3,365設備秒と一致する。
- quality-current/previousは各target自身の依存観測品質。C2のpeer全体の品質を代表する分類ではない。peer除外の影響は保存済みavailability等に残る。
- fault-quality-overlapは、同じtargetの有効quality区間と交差する正例の判定窓全体。瞬間的な欠損だけ、または設備の全信号を数える分類ではない。coreの無効qualityはoverlapに含めない。

これらは記述用の診断表であり、正式analysis文書のslice schema全体に接続済みと宣言するものではない。

## 検出遅延

因果条件を満たして検出した事例に限り、警報開始時刻−異常開始時刻を確認する。対応するequipment/source episodeと2つのsupport scoreが同じ判定窓内にあることも照合した。今回の固定1Hzデータでは遅延は1〜5秒の整数なので、5つの正確な度数で全検出値を保持できる。seed・用途・overallの中央値はこの度数を合算して求め、区間中央値の平均を使わない。未検出の遅延はnullのまま。検出0件なら中央値等もnull。

| 用途 | 候補 | 条件 | 検出件数 | 遅延中央値 秒 | 遅延平均 秒 | 最小–最大 秒 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| dev | c0-diff-control | core | 8 | 3.000 | 2.625 | 2.000–3.000 |
| dev | c0-diff-control | quality-stress | 7 | 3.000 | 2.571 | 2.000–3.000 |
| dev | c0-diff-control | overall | 15 | 3.000 | 2.600 | 2.000–3.000 |
| dev | c1-phase-level | core | 1840 | 1.000 | 1.261 | 1.000–2.000 |
| dev | c1-phase-level | quality-stress | 1744 | 1.000 | 1.261 | 1.000–2.000 |
| dev | c1-phase-level | overall | 3584 | 1.000 | 1.261 | 1.000–2.000 |
| dev | c2-phase-conditional | core | 1819 | 1.000 | 1.252 | 1.000–2.000 |
| dev | c2-phase-conditional | quality-stress | 1723 | 1.000 | 1.252 | 1.000–2.000 |
| dev | c2-phase-conditional | overall | 3542 | 1.000 | 1.252 | 1.000–2.000 |
| smoke | c0-diff-control | core | 0 | null | null | null–null |
| smoke | c0-diff-control | quality-stress | 0 | null | null | null–null |
| smoke | c0-diff-control | overall | 0 | null | null | null–null |
| smoke | c1-phase-level | core | 460 | 1.000 | 1.261 | 1.000–2.000 |
| smoke | c1-phase-level | quality-stress | 436 | 1.000 | 1.261 | 1.000–2.000 |
| smoke | c1-phase-level | overall | 896 | 1.000 | 1.261 | 1.000–2.000 |
| smoke | c2-phase-conditional | core | 460 | 1.000 | 1.261 | 1.000–2.000 |
| smoke | c2-phase-conditional | quality-stress | 436 | 1.000 | 1.261 | 1.000–2.000 |
| smoke | c2-phase-conditional | overall | 896 | 1.000 | 1.261 | 1.000–2.000 |

表の小数は表示時のみ3桁。JSONには計算値を保持する。検出できた事例だけの遅延なので、見逃しが多い候補の遅延が短くても高性能とは判断できない。信頼区間・正式性能判定・候補採択は未実施。

## 実装・試験・保存

実装保存点`782dcb7957e29dce481f0dea5c136df85a9152f3`。`anomaly_v03_slices.py`は独立の分類・整数集計・遅延度数を担当し、`anomaly_v03_slice_io.py`は呼出し側が認証したpin・identityと保存bytesを照合する。IO入口単独ではpinの信頼起点を確立しない。実行の信頼連結・登録順確認はOUTの`verify.py`で行う。

新規9試験と既存ledger/analysis adapterの関連試験、計32項目が通過。予定0のセル、phase0、発生前の参照、未検出null、品質重複、profile判定不能、重複/欠落/順序違反、遅延・support不整合、hash不一致を確認した。準備時にevent-offsetの手例の期待数を39から29へ訂正し、10件のscore対象外参照を明示的に数える回帰条件を追加した。実データの不一致ではない。

OUTは`artifacts/independent-slice-audit-2026-09-25`。最初の1区間と6区間ごとに保存し、120区間別report・21 checkpoint・`slices.json`・`input-pins.json`・資源記録・要約を残した。最終文書revisionとファイルhashは`savepoint-evidence.json`に保存する。元の大きなpayloadを複製せず、最終保存時も再読取りしない。

処理844.159秒、process peak private 145.32MiB、最小空きRAM 9.60GiB/commit余裕 16.49GiB。終了時C/D空き 127.05/298.62GiB。 1評価ずつ処理し、この実行の測定上は512MiBの上限内。長期のメモリリーク不在を証明する測定ではない。旧保存点・本流・実計算source・既存dirty guardを保全し、banto-24はPAUSEDを維持した。

次は、別々に検算したcounts・遅延・sliceを単一の認証済み解析入力へ統合し、正式schemaで不足するsource/runtime証拠等を整理する。現dev8/smoke2は記述集計に限定し、正式40holdoutの代用にしない。 formal/promotion/S6=false、performance=not_evaluated、selected_candidate=nullを維持する。正式holdout/CI/gate、単一writer/runtime受入、Phase 2/3全体は残る。
