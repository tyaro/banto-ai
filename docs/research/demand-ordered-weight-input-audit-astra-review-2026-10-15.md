# Astra：固定重みの入力接続・支持/rank監査

2026-10-15 JST。ユーザー指定によりgpt-6-astra1名が設計/コード/保存結果をread-only確認。編集/追加agent/fit/予測/採点/旧ラベル数量・2015へのアクセスなし。

設計はinput-only診断として妥当とした。Iはtrusted accepted_keysから引き継ぎ、元E/I・per-store1n・r0を維持する。全r正と旧適格r正を分け、energy=w*r²*||x||²と各列を保存、zero-totalはundefined、質量相当数は独立標本数としない。3列rankは罰則なしで、new rank=old positive subset rankを確認するよう指摘した。2013旧特徴は2014での遡及前処理であると明記した。

コード確認ではstored-positiveをrawと呼ぶ命名を訂正し、全categoryの行/店/日数を補った。正規化Gram determinantと非中心化cos²を共線性の記述として認め、condition numberとは呼ばず、[0,1]とrank3/det正の一致を確認した。

起動前に独立readerの未検査Fraction演算/比較を指摘し、独立checked subclassと各order比較のcross product、監査sortのchecked比較を確認した。resource finally/timeoutのfailed閉鎖とjournal、実行前fresh root確認も補強し、最後の差分にblockingなしとした。人工fixture訂正は数学的に妥当で、式/定数や入力を実成績へ合わせた変更ではない。

Astraは保存3rootのcomplete閉鎖と整合性、470行/16群、独立81665比較/652rank証跡、算術109/454/453bitと資源上限内をread-onlyで確認し、保存結果にblockingなしとした。季節poolのrank3は薄い単一年の3/6/7/5発行日支持や、Q3/Q4のenergy集中を解消しない。学習候補Q4の1日70.71%、issue Q3/Q4の1日73.12%/68.61%を確認した。r0全行の店舗は元E/Iに残るが情報量を増やさず、元日のr正8/旧E0/Noneとzero-total nullも適切とした。2014issueの分布はラベルを読まず、正誤/予測改善を示さない。入力接続監査済み・fit_ready=false、学習/2015へ自動接続せずこの監査で終了する結論を支持した。
