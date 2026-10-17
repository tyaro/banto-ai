# Astra：有界区間集計の実装・保存2014結果レビュー

2026-10-15 JST。既存gpt-6-astra方法担当・進め方担当にread-only確認。agentの新fit/採点/編集なし。

## 起動前

[事前契約](demand-bounded-scoring-contract-2026-10-15.md)と[設計確認](demand-bounded-scoring-astra-review-2026-10-15.md)を保存した。方法担当は実装のchecked算術、負floor/ceil、重み後の囲い込み、direct paired差、upper0とstrict改善の分離、solver未import経路にblocking誤りを見つけなかった。

方法担当の指摘により、完了済observedの後でassumedが失敗してもpartial-evaluationへ残す処理と、最終resource失敗時のresource-failure/failed closureを補強した。root_failure_overrides_any_summary=trueであり、resource例外時に仮summaryを成功扱いしない。旧v1 source/準備を保持したv2新入口・prep-v2を凍結してから本採点を起動した。人工11件は新集計入口を直接importしたことを確認し、v1/v2準備で各pass。11件を22個の独立fixtureとは扱わない。

## 結果

方法担当は保存rootのclosure/resource/summary/必要groupを読み、採点complete、最大算術2134bit、時間・Macメモリ観測上限内と確認した。年間MSEは両modeで減少、Q2〜Q4はMSE・過小・過大も減少、元日は同値。一方Q1のall/normal両modeでMSEと過大量の区間下限が正で、丸め誤差や未判定ではない。mandatory_pass=false、契約上strict_total_improvement=falseが正しいと確認した。

進め方担当は提示結果を監査し、年間の低下は四季違反を相殺しない、8違反セルはQ1のall/normal・mode・指標の重複報告で独立8失敗ではない、と確認した。同担当は結果時点では成果物読出し/計算を行っていない。p192で全macro符号を解決できたことは数値判定の完了であり、統計的有意性や将来再現性の証明ではない。

親の別プロセス独立readerは、集計実装もsolverもimportせず、保存pred/labelから3,960 scalar・388,440 weighted項の支持/重み/上下限/direct paired判定を再構築して一致した。旧state/260予測/既存失敗/closed roots/source不変を確認した。Astraレビューの時点で進行中だったreadbackも、その後完了と共有した。

Q1だけを事後Bへ差し替えず、固定予測の評価として保存し終了する。21削除fitは未実施で、少数日の実測依存性は未評価。2015再評価の停止、同休業mean28、観測のみ/欠測0仮定分離、PSI採用なしを維持する。旧failed工程を成功へ書換えず、新たな保存予測採点工程のcompleteと区別する。
