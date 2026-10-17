# 次の機構：需要入力の支持情報を予測と分けて示す

2026-10-14。[保存補正と入力範囲の診断](../results/store-sales-weekly-correction-diagnosis-2026-10-14.md)を受けた未実装の設計。8週回帰の不採用を覆すための新gate評価ではない。

## 目的とfield

予測時点の入力だけから、固定fit profileに対する状態を返す。状態は、`unsupported_zero_fit_scale`、`missing_weekly_input`、`outside_common_fit_range`、`inside_common_fit_range`。店舗自身の範囲外は独立した補助fieldで示し、共通範囲外と同一視しない。範囲内は精度保証/適用承認/通常運転認定ではない。

profileはfit cutoff/対象store役割/8列min-max/std/source pinを固定したもの。旧rootへ追記せず、保存fit-only-boundsを新profileの参照元とする。値の変更・対象店不一致・future fit行・不正幅は、別の適用失敗として拒否。ゼロ尺度群の値に別店尺度を借りない。

target/actual/forecast/residual/2015結果は入力引数に持たない。未来labelを触ると失敗する少数例で確認する。missingの週を範囲内の0へ変えず、featureがない場合は範囲判定・距離ともnull/理由付き。境界と等しい値は範囲内。定数列の差はstdで除算せず別理由を持つ。

## 次unitの範囲

新pure functionを独立namespaceで作り、profile/store/cutoff、欠測と実0/zero-scale、範囲端の内外、共通と店舗内の差、定数列、未来label payloadへ非アクセスを少数確認する。旧確認・fit・forecast・range監査を再実行しない。保存profileを読み込む接続はmetadata pinとfield対応だけ、新予測を作らない。

profileを作る時期と利用起点を比較し、起点より後の学習profileを通常のオンライン支持証拠にしない。profileのfit cutoff以前の窓への利用はfixture/学習記述として明示する。本番の公開遅延・改訂は別の利用可能時刻契約が必要。

## 予測変更・研究の境界

この仕組みは通知だけで、点予測・quantile・係数・選択・停止閾値を変更しない。範囲外をBへ戻す方式や補正の縮小が良いかは、別の出力前契約と評価で確かめる必要がある。今回の既知2015に戻って良い閾値/店だけを選ばない。距離を失敗確率へ変換しない。

次の需要モデル研究では、追加情報の役割、情報が分かる起点、支持不足時の扱いをこのfieldと同じように明示する。営業/新商品導入/供給予定を実績から推定して既知入力へ補わない。入力支持の確認と追加価値の確認を分ける。

直接研究ACTIVE/automation PAUSED、旧8週モデル不採用/mean28総量＋限定暦配分維持。追加agent0/CARE手動待ち、原失敗/閉鎖root不変、全実行・記録・prep上限据置き。formal_permission=false/credit0/native reader禁止/登録holdout未読、メーカーPSI/TimesFM同等/正式受入を補わない。Gitは独自codeと集約docsのみ。
