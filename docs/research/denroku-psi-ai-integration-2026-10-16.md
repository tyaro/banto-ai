# 既存の需要予測とPSI実装から引き継ぐ内容

状態: sourceの読取り確認と実装計画への追補。2026-10-16 JST。アプリ変更、学習、推論、モデル移行は行っていない。

[denroku-psi-demo](https://github.com/tyaro/denroku-psi-demo) のmain commit `816fbdaec722008193b3945db7f4599d1a8a64b7` を固定して確認した。13 source/仕様ファイルの取得内容がGit blob SHAと一致した。[AIクレート実装計画](banto-ai-rust-implementation-plan-2026-10-16.md)へ、需要・PSIの既存利用例として反映する。

## 現在実装されている範囲

| 場所 | 確認した処理 | 現在の境界 |
| --- | --- | --- |
| trainingのPython script | LightGBM学習、特徴量・モデル・照合用出力の保存 | 学習はPython CLI |
| inference-probeのRust | 保存済み木JSONの推論、特徴量再生成、再帰予測、Python出力との照合 | 学習器ではなく推論/変換用プログラム |
| Rustからの出力 | 検証用/将来用を別に照合し、一致後に画面用JSONを生成 | 既存静的デモ資産の生成経路 |
| 画面の予測選択 | AIと担当者の参考計画のどちらを採用するか選択 | 予測エンジンそのものから分離できる |
| PSI処理 | 採用した予測または確定受注を需要とし、在庫・ロットから必要生産候補を計算 | 需要予測とPSIの判断を分離する |

根拠は[Python学習](https://github.com/tyaro/denroku-psi-demo/blob/816fbdaec722008193b3945db7f4599d1a8a64b7/training/train_synthetic.py)、[Rust推論](https://github.com/tyaro/denroku-psi-demo/blob/816fbdaec722008193b3945db7f4599d1a8a64b7/inference-probe/src/main.rs)、[予測採用](https://github.com/tyaro/denroku-psi-demo/blob/816fbdaec722008193b3945db7f4599d1a8a64b7/app/apps/admin-template/src/lib/demo/forecastChoice.ts)、[PSI](https://github.com/tyaro/denroku-psi-demo/blob/816fbdaec722008193b3945db7f4599d1a8a64b7/app/apps/admin-template/src/lib/demo/psi.ts)。実行して性能を再確認した結果ではなく、固定source上で確認した処理である。

特徴量定義は旧公開データ版の12列と現行合成データ版の18列がある。列名・順序・lag・calendar・品目対応をモデルと照合する。将来の再帰予測では非負化・偶数丸め後の予測を履歴へ追加し、検証期間の実績を次のラグへ入れない。Python/Rustのraw値・特徴量・丸め後数量を比較し、不一致なら画面用JSONを書き出さない構成は共通化の参考になる。

デモの合成実績や補完値に対する成績は実運用の精度として引き継がない。公開データ・合成データ・新たな業務実績の評価は分ける。デモが予測数量をPSIへ渡せることと、在庫・生産の業務判断が妥当なことも別に検証する。

## Pythonを使わない再学習の既存計画

[再学習計画](https://github.com/tyaro/denroku-psi-demo/blob/816fbdaec722008193b3945db7f4599d1a8a64b7/docs/design/python-free-lightgbm-retraining-plan.md)と[実装設計](https://github.com/tyaro/denroku-psi-demo/blob/816fbdaec722008193b3945db7f4599d1a8a64b7/docs/design/python-free-lightgbm-training-design.md)がある。LightGBM 4.6.0を起点とし、Rustの隔離workerから公式C APIで学習する案で、状態行は実装・依存追加・native library導入未着手となっている。

この案はPythonを運用時に不要にする方向であり、LightGBM学習計算まで純Rustで書き直す案ではない。自作SmallForecasterのBurn経路とは別engineとして扱う。既存計画のジョブ/モデル版/評価/採用と定期実行の考え方を参照し、未実装の機能を現在動作しているものとして扱わない。

## banto-aiに共通化する境界

共通AIの配置は引き続きbanto-aiで、利用側は産業のbanto-industrialと需要・PSI側のアプリになる。

| 共通化の対象 | 用途またはengine側に残す部分 |
| --- | --- |
| model ID/version、engine種別、学習範囲、source・特徴量schema・来歴hash | LightGBMの木と18列特徴量、SmallForecasterのtensor/quantile構造 |
| 予測起点・対象期間・粒度・単位・対象IDの意味 | 品目/週と設備/センサー/10分の対応や集約 |
| raw出力と後処理済み数量、後処理policyの版 | 需要数量の非負化/丸め・再帰、産業分位点の順序と残差警報 |
| 学習進捗・取消確認・保存再開・型付き失敗の基本契約 | native workerの監督、定期実行、認可/監査/DB/UI/モデル採用 |
| 入力/正解の分離、固定参照、数値照合と不一致時の停止 | 用途別loss/指標/評価窓/実用性の合格条件 |

将来出荷数量の点予測・期待値・中央値・分位点を区別する。LightGBMの出力やSmallForecasterのq50を、一律に同じmean APIへ詰めない。rawの小数数量を残し、PSI向けの丸めと表示丸めを混同しない。需要の26週再帰予測と産業の32step出力も同じhorizon数へ合わせない。

業務の受注/出荷/在庫/生産予定や販促試算は利用側の意味を保つ。AI crateへPSIの在庫計算や「確定受注と予測のどちらを採用するか」の判断を埋め込まない。モデル評価では、担当者が選択・修正した後の値と、修正前のAI出力を別に保持する。

## 計画に加える有限工程

1. **需要側の現状確認は今回で区切る。** 既存実装/未実装と移行対象を整理したため、R1着手前の大規模な再棚卸しは不要。
2. **R1/R2は自作モデルを先に進める。** 共通manifest/error/input-outputの意味がLightGBMを不必要に排除しないことを確認し、最初のcrateへLightGBMのnative依存やPSI固有処理を追加しない。
3. **需要側の接続仕様を別に固定する。** 既存の特徴量/木JSON/予測schemaと互換にすべき境界を定め、取得済みの小さな照合fixtureか合成fixtureで確認する。顧客・非公開のsource/data/modelを共通crateの公開配布物へコピーしない。
4. **LightGBM移行は別engineの工程にする。** 既存計画を再利用し、共通化する推論の範囲、native C API学習の担当、配布/利用条件を実装前に決める。Burn版の学習完了をLightGBM学習完了としない。
5. **共通crateを使った需要・PSI接続を確認する。** まず現行出力との互換を確かめ、その後に自作の需要平均モデルを候補として比較する。モデルを自動的に置換せず、予測精度とPSI結果の比較条件を先に固定する。

需要側の工程は新しいデータ取得/学習/評価の開始許可ではない。以前からの需要2015再評価停止、2014以前だけの調整、同休業mean28比較、四季平均の過小量・過大量非増加、観測のみ/欠測0仮定の分離を維持する。今回のrepo source確認を、同repoのモデル/実績データの利用範囲へ拡張しない。

## 保存範囲

非公開source原文・tree・内容hashはローカルのgitignore対象artifact `artifacts/denroku-psi-ai-intake2-20261016` に保存し、tracked文書には技術的な境界とsource参照を残す。Excel/CSV、学習済みモデル、予測値データは取得していない。相手repositoryの変更、アプリ起動、学習/推論、依存導入、Git pushは0。Windows native/OS依存試験も今回のsource確認では実行していない。


保存処理の初回はsource許可拡張子にTypeScriptを含め忘れて停止した。失敗root/stdio/exit/sourceを保持し、source種別だけを修正してfresh rootへ保存した。相手のsourceや実行条件は変更していない。
