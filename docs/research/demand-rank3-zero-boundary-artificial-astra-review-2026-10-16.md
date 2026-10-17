# Astra：rank3・週係数非ゼロ解のrawP厳密ゼロ境界

2026-10-16 JST。既存gpt-6-astra担当を再利用、追加agentなし。実データ内容を読まないread-only確認。

## 起動前

2026-10-16 JST。既存gpt-6-astra担当 /root/astra_weight_support_audit、read-only解析/source監査、追加agentなし・実データ内容decodeなし。

固定A/D/W案は解析保証できる。large A/D/Wの旧特徴行列式1/32>0、r各>1/2。smallW平面への2×2縮約から全beta<0（週も非ゼロ）を示し、非制約解のsmallW raw<0と元非負半空間への正dual射影を保証する。smallWはP=0、全largeは0<P<B、under0/over減少で元問題の一意最適。issueはraw(c)=140*rW*beta0*(1-c/c0)、週項140*rW*(c/4)*beta2<0。旧履歴/重み/λ変更やfixture探索は不要。

起動前最終回答：
「check_rank3_zero_boundary.py:46 の大群条件をP<Bから0<P<Bにしてください。現状は大群のP=0を許し、契約のsolve前条件より弱くなっています。独立readerは既に厳密条件を検査しています。
その他、rank3、2×2縮約とCramer射影、保存rの再構築照合、週項を含む30境界ケース、90scenario、19拒否の集合、文書closerに新しいblockingは見つかりませんでした。
結論はQ2・全open・B=E・固定3点の人工接続に限定します。週項の日次線形分解は上側10件のみ。実学習・2015停止、fit_ready=falseを維持する記述は適切です。実験は実行していません。」

指摘は起動前に反映した。producerもchecked cmpでsmallW P==0/他行0<P<Bを厳密検査する。構文確認済み、source凍結前に修正し実験を再実行していない。

## 保存結果の最終確認

2026-10-16 JST。既存gpt-6-astra担当 /root/astra_weight_support_audit、保存結果read-only最終監査。

最終read-only監査で、新しいblockingはありません。起動前の大群条件もchecked比較による0<P<Bへ修正済みです。

保存3 rootの閉鎖・内容hash、今回13 source pin、保護対象205 root／335 sourceの一致を確認しました。保存証拠では、人工60行のrank3、Cramer射影と2×2縮約の一致、全beta負、元非負制約の正dual、Ju<Jc<J(0)、KKT gap 0が揃っています。

30予測を再集計し、下側10件は負raw・floor flag true、中央10件は厳密0・flag false、上側10件は正raw・比例配分と一致しました。週項30件の負値・中央相殺、上側10件の日次分解、phase freeze、90scenario／19拒否／悪化60セルも保存結果と一致しています。

文書closer／closure-readerの構文と記述にblockingはありません。結論はQ2・全open・B=E・固定3点の人工接続確認に限定してください。一般的な連続性、floor後の日次への線形寄与、実四季性能は認定しません。

rank3_zero_boundary_artificial_ready=trueのみとし、実学習・2015停止、fit_ready=false／can_launch_learning=false／採用なしを維持する結論は適切です。追加実験・solve・実データ内容decodeは行っていません。
