# 水準・相対変動とイベント別入力を接続する一回設計（2026-10-14）

[入力の設計](store-sales-small-model-input-design-2026-10-14.md)に沿う新しい純粋入力関数の7確認とtrain側3起点の入力組立が成立した。次は別namespaceの小型候補へ接続し、一回だけ学習する。旧code/学習/確認/予測を反復しない。

## 新候補の接続

- C56/P7/H14/V3/D64/2block、CPU float32を維持。正規化された数量7＋mask7＋暦84の98要素をpatchへ投影する。
- futureは14日×暦12=168要素。店舗別context統計2要素を独立2→64 projectionで未来queryへ加える。maskやcalendarを介して統計が消えることを避ける。
- 日次配分headはhorizon state64＋当日暦12＋相対lead1=77要素。総量Q10/Q50/Q90と日次pointの整合方式、損失と非負順序は旧設計を維持。
- 原mean/stdのfloor、学習固定尺度、総量倍率/配分の初期化も維持。新parameter数は120740の予定。旧候補110916からの増加は入力接続分だけで、model幅/block数や学習予算は増やさない。
- train支持数は保存train診断ledgerのdistinct label日を使用し、featureには入れずmetadataへ付ける。支持例ゼロのChristmasは未検証・営業状態不明のまま。新forecastの保存にもそのmetadataを残す。

接続の新確認は3件：同じ標準化列で統計projectionと総量倍率への経路が変わること、event channelから配分への経路、実data wrapperが固定origin/尺度/基準と支持metadataを保つこと。有限gradientは新stats/暦の接続部分で確認する。初期zero-weight出力headでは入力差による出力差が出ないため、経路確認では明示した小さな非zero headを用い、性能の証明にはしない。

## 学習と比較を先に固定

保存旧inputのtrain991/validation25/test16 originと256×8 sampler日付列をそのまま使用する。train label2013–15、validation2016、testは既に読んだ2017回顧。新loaderでorigin/尺度/scheduleの完全一致を確認する。販促/oil/transactions/Transfer/Event/営業日の真値は使用しない。

新candidateを独立初期化seed20261014、AdamW lr3e-4/betas(.9,.999)/eps1e-8/weight_decay.01/grad norm1、CPU2threads/interop1/deterministicで256step。異なるparameter形状のため旧初期stateと同一とはしない。batch samplerは新生成せず保存列を読み、学習延長/別seed/gridは行わない。

lossは旧と同じ0.5*総量pinball/(14*固定train平均)+0.5*日次MAE/固定train平均。validation step64/128/192/256、最小score・同値は早いstep、選択を保存した後test16originだけforwardする。

旧小型候補とmean28/限定暦配分・固定/直近区間は原保存結果を再利用。店舗/日付/実績の対応を照合し、新候補の日次・総量WAPE/Bias/MAE、総量coverage/幅/pinball/interval scoreと店舗別内訳を保存する。元日と他originの内訳は保存予測から一度計算するが、それを用いた再fit・混合方式選択はしない。

水準統計と暦を同時追加した候補なので、改善してもどちらか一つの因果効果、系列attentionの追加価値、parameter数を揃えたablationとはしない。旧testの知見を踏まえた探索で、独立未見確認ではない。改善がない場合も小型モデルの一般的な能力上限を示すものではない。研究基準と正式不採択を保持する。

## 実行・失敗保存

通常output24file/768MiB、失敗reserve8file/256MiB、合計1GiB32file/single32MiB、OS private2GiB/900秒を維持。source全文・設計・input対応・固定support・初期state・4checkpoint/prefix・選択・新予測とevent metadata・旧比較・journal/summary/closureを新rootだけに保存。診断16MiB512files/256KiBparts/reserve2MiB16filesとprep128KiB16filesも維持。

元例外と完成prefixを保存し、未完成と閉鎖を区別する。失敗・Sol容量・人の停止では保全して停止、同root再実行/旧完成unit反復なし。既存Files/checkpointは局所制限であり、native回収やblocking中断の証明ではない。

独自codeと集約文書のGit継続承認内で保存。原数量/生予測/fit/重みは送信しない。正式gate不変、formal_permission=false/credit0/登録holdout未読/native reader禁止、automation PAUSED/直接研究ACTIVE、追加agent0/CARE手動待ち。
