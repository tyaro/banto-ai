# 保存特徴projectionの対応確認

2026-10-15 JST、派生分析前。Astraの確認により、総行数だけでなく学習発行日3/6/7/5・2014発行日7/6/7/6、各日FIT10が1行ずつ、(store,origin)重複なし、元identity key、全21除外をconsumerで検査する。2013-02-26から14日ごとの21発行日、2014-01-01から14日ごとの26発行日という保存済みcalendarを照合する。

親はpin済みencoded-rowsとaudit-groupsの全key/metadata/保存x/z/r/w/vからprojectionを作り、分析前に保存する。consumerはその凍結bytesのpinも検査してからstrict schema/calendar/元1nと保存積を検査する。独立readerは元pin済み保存状態から全字段を再構築してprojectionと完全一致を照合する。これはtrusted parentからの具体payloadの対応確認であり、悪意あるparentに対するOS sandbox/認証ではない。childへpath/reader/ラベル/全履歴を渡さない。

人工22checkがpass。初版19checkのroot/sourceもcompleteのまま保持し、v2のconsumer検査だけ補強した。幾何式・元集合/重み・定数・将来の条件は変えない。今回は保存特徴だけの分析、学習/2015は停止のまま。
