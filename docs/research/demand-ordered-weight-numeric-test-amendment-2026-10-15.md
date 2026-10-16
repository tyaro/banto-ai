# 人工検証の補強：初版保持とv2の事前固定

2026-10-15 JST。定数τ=1/20・絶対p32最近接偶数丸め・D1の式は変更しない。[数値契約](demand-ordered-weight-numeric-contract-2026-10-15.md)を維持する。

初版23packet/53assert/26期待拒否・独立3130比較はpassし閉鎖した。ただしAstraが初版checkerのラベル手計算を指摘した。全Noneを0補完しquantity母数もdailyと同じだったため、既存の「休業相当欠測だけ0、営業相当欠測は残す」の試験になっていない。任意の固定baseline複製もmean28実装の検証ではない。手書きE/I ledgerだけでは行変換後の分母保持の証拠も弱い。初版のsource/結果/complete閉鎖状態をそのまま保持し、初版だけを統合確認完了とは扱わない。

v2を別名で保存する。raw recordのdate/available_atの型はtype is strで明示する。新checkerは既存project_input/project_label/label_scenariosとbounded atomsを人工calendarだけに適用し、01-01/12-25固定maskのうち12/25をtarget内に置く。past56=10から旧曜日mean28を検証し、closure予測0・観測のみ/休業欠測0仮定の各母数/損失を分ける。closureNone・openNone・実0・closure正値を区別する。

人工4行を実encode_featuresへ通し、positive/r0/全欠測/旧不支持の元E/I membership・元1/n重みを保存して照合する。これはモデル用prefix統合やQP fitの証明ではない。

J=1..14全支持、入力各値は8192bit内でも和/特徴積の中間bitが超過する2例、future/labelのフィールド参照自体を失敗させるAccessGuard、比較等価な非str日付の拒否、fallback全数値stateの独立照合を追加する。実データを一切使わず、この有限追加だけで終了する。

v2通過後も実r/新fit/2014評価/2015参照・再評価へ接続しない。fit_ready=false、四季平均under/over非増加・MSE条件・同休業mean28・観測/欠測0仮定分離・調整2014以前・heartbeat PAUSEDを維持する。最初の検証不足も結果に残す。
