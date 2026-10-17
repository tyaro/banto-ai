# 既存10店の保存誤差診断 — 実行前契約

2026-10-15 JST。人の「進めていきましょう」により、既存10店2015の保存予測を一件診断する。主模型time_selected3328、副比較transfer_selected3072、対照mean28を変更しない。

入力は閉鎖root `artifacts/macos-demand-existing-stores-2015-20261015` の予測前後・尺度binding・summaryのみ。closure確認では全fileをhashするが、原本ZIP/入力snapshot/profile/weightsの数値解釈・deserialize・forward・fitはしない。250要求、各店349観測日/24完全14日label、全240完全labelを保持する。

既存pure分解器を使用。日次d=(P-B)/u,r=(Y-B)/u、総量は14u、MSE差=d²−2dr。原10店等重みと全4origin四半期を保持する。内部feature_off/on欄は時間/移行選択の列名対応に限り、特徴有無のablationとは呼ばない。

併せて同じ保存予測の絶対誤差差分を、改善/悪化/同値の件数・寄与、過小予測max(Y−P,0)と過大予測max(P−Y,0)に分ける。MAE差=過小量差+過大量差、bias差=過大量差−過小量差、WAPE差は店ごとの固定実績総量で正規化。これは予測誤差の方向であり、実際の欠品・過剰在庫・PSI損失を意味しない。
MSEの改善寄与/悪化寄与も分け、少数/多数と大きさの関係を記述する。全体/10店/4四半期/40店舗四半期×3比較×9指標の1485差を旧summaryと1e-10以内で照合。欠測総量は部分和で代用しない。原店を除外せず、倍率・年度・checkpointを選び直さない。

fresh記録root `artifacts/macos-demand-existing-stores-diagnosis-20261015-records`。契約/source/新架空fixture・全child stdout/stderr/exit・結果・元root前後一致をEvidenceStore16MiB512file/part256KiB/reserve2MiB16fileへ保存。親900秒/子870秒、Mac sampled footprint/peakRSS各2GiB。失敗を上書き/盲目的再試行しない。

一件保存後研究停止、automation PAUSED、formal_permission=false、製品採用0、追加agent0、CARE待ち。新学習・原本再抽出・profile生成・seed/LR/grid/年延長0、2016/2017/予約31–54/販促/正式holdout未解釈、Windows native/OS依存包括suite新実行0。既存変更・closed rootsを保持、原data/profile/予測/weightsのGit送信0。
