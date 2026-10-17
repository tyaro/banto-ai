# 独自小型モデルの需要用途への適用（2026-10-14）

## 判断

需要用の入力・分割・総量と配分・不確実性・学習予算を先に固定し、独立初期化から一回の学習と選択、回顧予測まで完了した。需要モデルを作って動かすことは成立したが、今回の結果は既存の単純基準を置き換える根拠にならない。

研究基準は **過去28日の同曜日平均による総量＋限定的な暦配分**を維持する。今回のモデル・学習区間は採択しない。TimesFM3の重み・教師出力・公式学習を使わず、公式モデル同等性・汎用zero-shot・実メーカー精度・PSI採択は示さない。

## 実装と一回の条件

保存済み公開Store Sales snapshot、5/11/12 BREAD/BAKERY。C56/H14/P7/V3/D64/L2、110,916 parameters。過去数量の観測maskと過去/未来の暦5要素。未来販促実績、oil、transactions、Transfer/Event、営業日予定を入力にしていない。

既存独自Blockを再利用し、旧MetroPT固定モデルを変更・再実行していない。総量Q10/Q50/Q90を非負・順序付きで直接出力し、日次pointを総量Q50×softmax配分とした。日次分位点の合計を総量分位点にしていない。日次pointは整合配分値で、日次各値が周辺中央値とは主張しない。

trainは2013–15 label、991共通origin。validationは2016固定26起点のうちChristmasを含む1起点を除外し25。testは既存2017固定16起点、3店舗で48窓・672日。欠測と観測ゼロを区別し、店舗12の60日連続ゼロを保持した。contextの欠測はmaskで扱い、label欠測は除外した。

init seed20261014、独立sampler seed20261015、256×8 batch、AdamW lr3e-4/grad norm1。validation選択は固定尺度による総量pinballと日次MAEの等重みloss。学習完了後に選択stateをSHA確認し、test forwardを16回だけ行った。3店舗の相互attentionの追加価値を分離する対照学習は今回していない。

| checkpoint step | validation loss |
| --- | ---: |
| 64（選択） | 0.0693295431 |
| 128 | 0.0703946297 |
| 192 | 0.0699850389 |
| 256 | 0.0702897543 |

後続checkpointでvalidation改善は得られなかった。今回のtestを見た学習延長、seed変更、loss/幅の探索はしていない。予算が限定された実験なので、学習能力の上限や他の設計が無効とは判断しない。

## 点予測

既存基準の予測・実績は保存ledgerから再利用し、店舗・日付・数量を新float32 labelと照合した。集計は基準側の保存精度の実績で行った。数量は公開salesの原単位で、メーカーの箱数ではない。

| 方式 | 日次WAPE % | 14日総量WAPE % | 総量Bias % |
| --- | ---: | ---: | ---: |
| mean28 | 14.770136 | 7.307154 | -0.839908 |
| mean28総量＋暦配分 | 14.424314 | 7.307154 | -0.839908 |
| 小型モデル | 14.729793 | 7.295235 | -1.214088 |

モデルの総量差は0.012 percentage points程度、日次は暦配分基準より悪く、過小偏りも増えた。微差を有意な改善としない。

| 店舗 | 日次 mean28 / 暦配分 / モデル WAPE % | 総量 mean28 / モデル WAPE % | モデル総量区間coverage |
| --- | ---: | ---: | ---: |
| 5 | 12.524499 / 12.193467 / 12.447354 | 5.304585 / 5.290620 | 16/16 |
| 11 | 14.010734 / 13.660233 / 13.996522 | 6.847978 / 6.816155 | 14/16 |
| 12 | 21.720269 / 21.363324 / 21.655742 | 12.724551 / 12.787738 | 11/16 |

## 総量80%区間

| 方式 | covered / 48 | coverage % | 平均幅 | 平均interval score（小さいほど良い） |
| --- | ---: | ---: | ---: | ---: |
| mean28・固定校正 | 32 | 66.67 | 917.801727 | 2092.694240 |
| mean28・最新25完了窓校正 | 34 | 70.83 | 1147.818659 | 2080.379115 |
| モデル直接分位点 | 41 | 85.42 | 1819.699715 | 2301.566831 |

モデルは下限未満2/上限超過5。幅は固定基準の約1.98倍で、外れへのpenaltyを含むinterval scoreは悪化。全体coverageが80%を超えていても、店舗12は68.75%、店舗5は100%と一様でない。実務校正済み・将来80%保証・安全在庫へ利用可能とはしない。固定・直近基準の元区間を再利用し、再校正はしていない。

## 保存予測からの配分診断

新forward/fitなし。総量中央値と基準総量の比は0.991626–0.999062、平均0.996254。今回の補正は基準の近傍に留まった。

元日3窓の日次WAPEは暦配分18.713429%、モデル24.013416%。残り45窓では暦配分14.155551%、モデル14.148067%と微差だった。モデルが名目の元日flagを受け取っていても、少ない年の例から今回十分な配分を獲得したとはいえない。flagの因果効果、実際の休業、必ず閉店するという判定ではない。

保存model配分に基準総量を掛けた代数診断は日次WAPE14.759084%。逆に保存model総量に既存暦配分を掛けた値は14.386368%。これはtestを見た後の記述的な分解で、独立した候補評価・因果的ablation・混合方式採択ではない。後者の微差を理由に2017へ合う方式を選ばない。

## 資源・記録・限界

実CPython3.14.0/Torch2.14.0+cpu/Windows。elapsed14.2470007秒、OS peak private/pagefile1,033,379,840B。model rootは閉鎖18files/2,766,445B。日次和と総量中央値の最大float32丸め差0.001953125原単位。

計算時checkoutはd3bbd10a58e24a0bd70896fbc65c7d9d853bb392に今回の未commit独自sourceを加えたもの。clean commit計算とはしない。実際のsource全bytesとSHA、設計、input pin、batch日付列、初期state、4checkpoint、validation prefix、選択、予測・対応、journalをlocalに保存し、Git保存後のsource照合は別metadataで記録する。

今回の需要機構6件は一回all passed。欠測/実ゼロと過去境界、label split、非負順序と配分整合、未来暦経路とmasked payload、直接総量loss、zero contextでの有限gradient。完成旧確認・MetroPT学習・CI・既存基準予測の反復0。初期の探索読取りにはpath/wildcard指定の誤りと既存restricted directoryの列挙警告があり、選択toolエラーとして保存した。モデルや確認の失敗として数えていない。

主要保存先（全閉鎖・追記/再実行禁止）：

- `artifacts/representative-store-sales-small-model-pilot-20261014`：原model出力、summaryはcandidate-complete、root closureがcomplete。
- `artifacts/representative-store-sales-small-model-checks-20261014-records`：6新確認の全stdout/stderr/exit、source pins、初期foreground読取りエラーの区別。
- `artifacts/representative-store-sales-small-model-pilot-20261014-records`：学習の全stdout/stderr/exit0。
- `artifacts/representative-store-sales-small-model-analysis-20261014-records` と対応launch-records：保存予測診断のみ。
- `artifacts/representative-store-sales-small-model-doc-20261014-records`、Git後は `...-git-20261014-records` のpost-saveを優先。

900秒/2GiB/output1GiB/single32MiB/files32、診断16MiB512files/256KiBparts/失敗reserve2MiB16filesを維持。checkpointはblocking中断・全writer/native容量認証ではない。生データ・予測・fit・重みのGit送信0。正式gate/credit0/native禁止/登録holdout未読は不変。automationはPAUSED、直接研究はACTIVE。

## 次に研究すべきこと

現在の3店舗・固定期間ではニューラル化の追加価値は確認できない。次は2013–15 train側だけで、基準の残差と暦配分の支持例数、連続ゼロが学習目的へ与える影響を診断する。学習量・対象系列の拡大が必要なのか、既存統計で十分なのかを判断してから次の設計を固定する。2017を使った再学習や幅探索はしない。大規模比較へ戻らず、販促予定履歴がないことを研究全体の停止条件にもしない。
