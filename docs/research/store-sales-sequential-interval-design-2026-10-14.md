# 次の固定案：完了した過去誤差だけで更新する総量区間

自身の過去区間は全体scoreを改善したが、店24coverage64%、店20calibration21窓、年・四半期の変化が残った。次は新しいモデル構造を増やさず、**時点が進むと既に完了した誤差を加える**一つの手順を設計する。本案は未実装・未実行。

## 役割と保存結果

pointは保存mean28のまま。自身の2013–15の69起点ledgerと、保存2016の150区間/point/actual/local scaleを再利用する。元過去基準、point forecast、固定自身Q、旧区間restore/scoreを反復しない。予測の時点依存のcalibrationだけを新しく計算する。メーカー運用/TimesFM同等/zero-shot/正式採択ではない。

2016は既知の回顧期間だが、計算では各originで利用できる誤差を厳密に区切る。対象store固定4/8/16/20/24/28、固定25origin/storeを維持、2017・予約群・新archiveを読まない。

## 新手順を固定

ある予測origin dのcalibration候補は同storeの過去窓だけ。target終端(origin+13日)がdより前の窓だけを使用する。raw targetや誤差の値を見る前にstore・日付で選別する。過去窓のcontext/label支持、過去56日正値ありの条件は固定自身設計と同じ。未知/欠測を0誤差にしない。

利用可能になった完了窓のうち最新26窓（14日刻みで約1年に対応する工程上の選択）を使う。26は一案として固定し、個数や重みを2016結果で探索しない。n20未満は原保存shared-local分位点へfallbackし、own Qはnull/理由付きで保持。自身のrow重み1、Q10/Q90とCDF定義/scale max(B,.01*14*u)不変。

すでに保存した固定自身calibrationと使用日付・残差・重みが完全に同じ場合は、その原分位点を再利用してpinを保存する。特に初期の少数支持storeで同じQを再計算しない。他の新窓集合だけで一回計算する。元labelの公開遅延・訂正履歴はdatasetにないため、target完了後の前日締めで利用できるという研究仮定を明記し、本番as-of証拠としない。

## 出力と確認

各store/originの使用calibration日付、target終端、支持、reuse/fallback理由、Q、保存point、newintervalを保存する。current/future labelがcalibrationへ入らないことを独立した少数例で確認。未来窓の数値payloadを触ると失敗する例、最新26/支持20境界、原Qの同日付再利用、store混入拒否を確認する。旧確認は反復しない。

保存actualとの新coverage/上下外れ/幅/interval score(alpha.2)を一回記述し、原固定自身区間の保存値と全体/店舗/四半期で対応させる。個別storeで良い方式を選び直さない。時系列依存/context重複が残るためcoverage保証/CIを補わない。全体改善と各店舗の不足を分け、採択せず研究上の追加情報を判断する。

新script/source/設計/元ledger/Q pin/時点別日付・支持・区間/原stdio/失敗をfresh rootに保全。実行/記録上限、正式gate、CARE手動待ち、追加agent禁止、automation PAUSED、原失敗・旧closedroot不変を維持。Gitは独自codeと集約docsのみ、原量/ledger/fit/予測を送信しない。
