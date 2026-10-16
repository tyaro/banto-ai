# v2人工checkerの期待値誤りを保持

2026-10-15 JST。数値仕様・encoder v2は変更しない。v2の行変換試験はold_features=Noneでも履歴重みr>0を計算する仕様を正しく実行したが、checkerが全行の非ゼロr数を旧適格かつ非ゼロr数と混同して1と期待し、assertで停止した。Astraも同じ問題を指摘した。

v2のsource/全stdio/exit1/resources/failed closureを保持する。v3では全raw非ゼロr=2、old_Eかつ非ゼロr=1を別に照合する。旧不支持行のrを0に書換えず、features=Noneとrisk行保持を維持する。これは人工試験の期待値訂正であり、定数・式・実データによる選択は変更しない。

v3は同じ有限人工集合/既存ラベル処理/独立readerを使う。2015参照・再評価、実r/fit/予測/2014採点は引き続き0。旧E/I、同休業mean28、観測/休業欠測0仮定の分離と2014以前だけの調整条件を維持する。
