# 主用途 — 既存店舗の将来需要予測・PSI

2026-10-15 JST。人の選択「既存店舗の将来需要予測・PSI」を主問とする。未学習店舗への転用は副問。現段階は自作StatisticalFeatureMeanの需要予測研究であり、公式TimesFM weightsは使わない。

## 固定する用途

既存店舗・商品系列について、予測発行前に完了した56日を入力し、次14日の日次販売数量と14日総量の期待値を出す。検証の発行間隔は14日、origin当日は入力外。ベースラインは過去28日から作る曜日別平均を14日に展開する既存mean28。
現在の公開benchmarkはStore Sales/BREAD/BAKERYで、製菓メーカーの実データへの適合確認とは区別する。salesは販売実績の代理targetであり、在庫切れで観測されない需要は識別できない。
PSIへの接続には将来、在庫・入荷・生産lead time・欠品/過剰の損失・必要service levelが必要。現在は平均数量の予測精度までを検証し、発注/生産判断や需要分位点の精度は認定しない。

入力に使う量はorigin前の観測だけ、欠測は0に置き換えない。尺度uは既存の各店2013-01-01〜2014-06-30観測平均に固定。暦支持はfit300で固定済み。販促実績・将来oil・他店同時売上を新たな既知入力としない。

## 次の一件の具体設計（未実行）

- 既存fit10店6/7/10/13/15/17/19/23/26/27を全店固定。fit窓は元契約どおり2013–2014前半、時間validationは同店2014後半。
- 主模型は閉鎖Mac rootの `time_selected.pt`（3328step、SHA256 `166171df43537141ea6174b0180f21e5044ddc54d4ea35c4ea7af5018d05aaf6`）。時間validationだけで選んだ保存点を使い、2015結果でcheckpointを選び直さない。
- `transfer_selected.pt`（3072step）は副比較。主用途と異なるC店舗移行validationでの選択であることを表示し、評価後に主模型へ入れ替えない。
- 2015-01-13+14*k（k=0..24）×10店の250要求を保持。予測用context/label範囲2014-11-18〜2015-12-28をstore/family/date filter後にだけ原本から数値化。2016/2017、予約31–54は対象外。既存店の2015は今回の診断では未抽出であり、盲検holdoutとは呼ばない。
- 原本pinと旧closure/state hashを確認してから一回適用。過去56日だけの新profileを生成、予測を全件labelなし保存してからlabel付与。新fit、倍率最適化、seed/LR/gridなし。
- 日次MSE/u²と完全14日総量MSE/(14u)²の半々jointを10店等重みで主指標とする。日次/総量、全店舗・origin全4四半期、MAE/WAPE/bias、支持を併記。欠測総量は部分和で代替しない。全店positive尺度を要求し、違えば停止して報告する。
- 開発上の暫定目安は元のaggregate2%以上改善・日次/総量悪化なし・支持不変を維持。改善店舗数は記述し、結果後に店を除かない。業務損失が未設定なのでPSI採用条件は未確定。
- fresh model/evidence roots、通常24files768MiB/全32files1GiB/single32MiB、失敗reserve8files256MiB。EvidenceStore16MiB/512files/part256KiB/reserve2MiB16files。親900秒/子870秒、Mac footprint/peakRSS各2GiB。全stdio・source pin・前後原root不変を保存。失敗rootへ追記/再試行しない。

これは次unitの設計であり、既存店舗2015の性能結果はまだない。本unit終了時は研究停止/automation PAUSED、formal_permission=false、製品採用0、追加agent0。原data/profile/予測/weightsをGit送信しない。
