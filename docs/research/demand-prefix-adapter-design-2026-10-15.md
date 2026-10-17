# 許可prefixの具体的受渡しと固定2特徴の支持監査

2026-10-15 JST。人の「続けてください」により前入力境界の次工程を実施。2015新内容参照/再評価は停止、旧変更/closed roots/失敗保持。本工程はadapter/特徴支持監査だけ、新fit/予測/scoreなし。これを通った後にも別の単一診断契約が必要で、自動的な探索を許可しない。

Astra方法担当と評価監査担当（既存gpt-6-astra2名/read-only）の回答を反映。accepted keysだけを渡して全体から探させず、確定した過去row・必要変換・ラベルだけを新payloadへコピーする。consumerには全470入力、全label reader/index/sourcepathを渡さない。Python sandboxや実着荷時点の証明ではない。

特徴を成績前に固定する。直前2週14日が全て真観測かつ各日が休業相当01-01/12-25以外の場合だけ有効。真0は有効。未来ラベルの欠測は適格性に使わない。Bは既存同mask mean28総量、uは2013尺度。T7は最新7日の曜日対応値を未来14日のassumed_open_maskへ反復した総量。x=(1,(T7−B)/(14u),2*(latest7−previous7)/(14u))。特徴2は過去週差を14日相当に換算した説明変数で、future mask適用の期待総量ではない。両特徴は同じ履歴を共有し独立証拠ではない。B<=0はB固定の入力fallback。年情報・成功gate・店舗/季節偏差・新期間/閾値は追加しない。

Q開始cutoffの許可label prefixから、各rowのpast14原値・日付、固定mask/B、2013uと変換usable_from、観測完全raw target/target末日/available_at、key/feature値・理由をコピーする。child schemaは余剰field/未来日付/未来label/利用不可変換/改ざん/特徴不一致を拒否。consumerへfreshデータだけを渡し、元全体・reader・pathへの参照を渡さない。

支持監査はinput適格/完全label/店・発行日・Q分布/理由/特徴変動・共通履歴を報告するだけ。ラベル値や予測誤差で候補を選ばない。支持が少なくても特徴やλを変更せず、仕様矛盾ならfit前に閉じる。カナリアで許可外rowを変更しても受渡payloadが不変、childが全体ファイルを開かないことを確認する。

後の単一仕様案（本工程では未fit）: 共通3係数、正規化残差(Y−B)/(14u)のQ等重み・店等重み・店Q内窓等重み（和1）の二乗誤差＋λ=1*全係数二乗。切片も罰則。未支持Q/店がある場合は構造的支持不足としてB、再配分して救済しない。endpoint R=max(B+14u*xβ,0)を先に作り、D=R−BへP=B+alpha_q D。過去の同QだけでalphaをMSE/under/over非悪化区間へclip。βと同じfitラベルによる内部最適化で独立校正ではない。Q開始後のlabelで同Qalphaを更新しない。B=0/未支持はB、解の非有限等は失敗保存し停止。B比例配分は各日平均の独立推定とは言わない。

四季平均under/over非増加・総量MSE非悪化、同休業mean28、観測only/欠測0別、outer事後B差替え禁止は維持。本工程は三条件の性能検証ではない。既読2014は独立性回復なし。親900/子870秒/footprint-RSS各2GiB、既存Files/EvidenceStore上限、全stdio/exit/source/state/closureを新rootへ保存。Windows固有/native/OS依存包括suite、新取得/外部送信/push/採用なし、PAUSED維持。
