# Astra：固定数値仕様・人工統合の確認

2026-10-15 JST。ユーザー指定によりgpt-6-astraへ数値契約、コード、人工checker/独立readerと結果をread-onlyで依頼した。追加agentへの再委任なし、実データ/fit/2015へのアクセスなし。

τ=Fraction(1,20)は全店共通の工学的規約として固定できると確認した。μ単位の変化尺度であり、前block比5%成長/最適値/確率とはしない。p32は絶対格子、μ/曜日平均は一般にFraction、negative tieは整数divmodで処理する。z誤差と最後r誤差の対象を分離する。

raw非負・N≤56の範囲証明をAstraが確認した。M=112+2^-32、s−r_raw≥(1/14)(1/400)/(2M²+1/400)>61·2^-33なので最終nearest-evenでもr≤s。raw域以外に拡張せず、保存前assertで異常停止しclampしない。8192bitは結果だけでなく約分前の中間積/和も検査する。

初版の手計算ラベル例は全Noneを0にしており既存休業相当規則を試験していなかったこと、任意baseline複製や手書きledgerだけでは弱いことを指摘した。親が既存label_scenarios/project_input/project_label/atomsへ人工日付と固定maskを通す試験、実encode_featuresの行変換、J1..14、途中bit超過、フィールド参照canary、fallback全数値stateの独立照合を追加した。

v2のunsupported行はr>0でfeatures=Noneとなるため、全r正と旧適格かつr正の二計数が必要と指摘した。親の試験も期待値で停止しfailed rootを保持した。v3のexact欄へstr(float)を渡したfixtureエラーも保持し、v4でstr(F(...))へ訂正した。定数/式/実装v2はこの試験訂正で変えていない。

v4差分に追加blockingなし、unsupportedのr>0/features=Noneの独立確認とexact欄の修正は妥当と確認した。Astraは保存結果のcomplete閉鎖・両工程exit0、人工37packet/107assert/期待拒否30・人工ラベル4例・独立5159比較一致、最大2136bitと資源上限内もread-onlyで確認し、人工encoder確認完了に異論なしとした。これはraw encoderの人工確認であり、実需要有効性・実prefix統合・係数fitの承認ではない。r0行保持は情報量/独立発行日数を増やさず、再fit後の幅や未来の両側非増加を保証しない。2015停止・fit_ready=falseを維持する。次は別契約のprefix統合と支持監査までとし、fit/2015へ自動接続しない進め方を支持した。
