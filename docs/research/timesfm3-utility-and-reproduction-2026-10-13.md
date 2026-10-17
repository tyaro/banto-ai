# TimesFM 3の実用性と公開情報からの独自モデル構築
策定日: 2026-10-13 JST
状態: 調査・研究計画。新しいモデル実行・学習・性能評価は未実施。

## 1. 研究の主問

人の最新方針に従い、主問を次の二つへ戻す。

1. TimesFM 3はBantoが想定する産業時系列用途で実用的な価値を持つか。
2. その価値を、公開情報を基に独自のモデル・学習でどこまで実現できるか。

C0/C1/C2は対象・検知目的によって使い分ける監視方式として扱う。特定の段差と持続条件での結果から方式全体を否定しない。固定合成patternの追加比較を研究の主目的にしない。試運転支援・異常検知・Hub連携は応用先として残すが、すべての完成をTimesFM研究の前提にはしない。

「同じ構造を実装」「公式の学習を再現」「同等性能を得る」は別の成果である。自前mini-Transformerという名前だけではTimesFM 3再現を意味しない。

## 2. 既存評価で答えたことと未回答

下表は既存報告の読取りによる整理。原artifactの再計算・再評価はしていない。

| 保存済み根拠 | 分かったこと | 未回答 |
| --- | --- | --- |
| [統計baselineとの小規模比較](../results/timesfm3-baselines-comparison-2026-09-04.md) | past-onlyでは温度が最良、電流はmoving-average等に劣った。known-load追加も点予測の一貫した改善ではなかった | 共変量が役立つ条件、長さ・遅延・入力品質への依存 |
| [合成8cell matrix](../results/timesfm3-matrix-2026-09-04.md) | 温度4条件でMAE最良、電流4条件で6方式中4位。長いcontextで改善した限定例 | generator外の一般性、独立した運転・日・設備への移行 |
| [MetroPT-3の限定評価](../results/timesfm3-metropt3-evaluation-2026-09-04.md) | 1日・1設備・3target・16 test origins。最良統計baselineへのMAE改善は約45～48%。3targetのMAE/RMSE/WISが最良 | 実設備一般、別期間の安定性、故障検知、試運転効果、本番適合 |
| 同MetroPT-3のruntime | 保存値はCPU p95約3.91秒、whole-process peak約2.77GiB | model単独のpeak、target hardware、必要周期との適合、許可上限内の構成 |

研究上の判断: TimesFM 3には限定条件で有望な予測結果がある。ただし、用途横断で使える・採用可能・自作でも同じ性能になるとは結論できない。目標は「全条件でbaselineに勝つ」ではなく、必要な用途で価値と負担を確かめること。

### 未回答を絞る順序

- 対象信号と予測時間幅、先読みで変わる判断を一つ定める。現在未確定なので、ここで数値合格基準を作らない。
- 既存結果で答えられる部分を使い、別運転での予測誤差、区間校正、共変量の効果、計算負担のうち判断を変える不足だけを選ぶ。
- 比較には同じ情報時点・target・horizon・splitを使う。単位を混ぜない。重なるoriginを独立試行数とみなさない。
- 既知将来共変量は予測時点で確定していた計画値だけ。将来の実績値や事後の故障情報を入力にしない。
- 公開データと製品対象の違い、事前学習との重複の確認範囲を明記する。

C0/C1/C2の保存済み144cellは監視挙動の資料であり、TimesFM 3の予測・自作モデルの性能評価数へ加算しない。登録holdoutは未読を維持する。

## 3. 一次資料と公開範囲

2026-10-13に次の一次資料を読んだ。外部master/mainは変わり得る。今回のweb読取りは閲覧時点の観測であり、外部source全体のraw-byte snapshotやrevision固定を完了した証拠ではない。

- [Google ResearchのTimesFM-3解説](https://research.google/blog/timesfm-3-a-zero-shot-foundation-model-for-multivariate-forecasting/)
- [公式モデルカード](https://huggingface.co/google/timesfm-3.0-pytorch)
- [公式repositoryのREADME](https://github.com/google-research/timesfm)
- [PyTorch model source](https://github.com/google-research/timesfm/blob/master/src/timesfm3/torch/model.py)
- [重みのlicense本文](https://huggingface.co/google/timesfm-3.0-pytorch/blob/main/LICENSE)

Astraの独立読取り検討も反映した。対象sourceと調査要約の範囲を区別し、repository全履歴・全issueの非公開性を証明したものとはしない。モデルのダウンロード・import・学習・評価は行っていない。

| 項目 | 確認できた公開情報 | 不足・次の確認 |
| --- | --- | --- |
| patchと規模 | model card/sourceに入力32、出力64、20層、幅1280、16heads、9分位点 | 縮小時の整合、学習時のcontext/horizon分布 |
| 多変量構造 | 時間方向のcausal attentionと系列間attention、入力blockと予測head | tensor shapeとmaskの厳密な対応、各要素の寄与 |
| 正規化・推論 | RevIN、CPM関連処理、forward/decodeがsourceにある | 学習時と推論時の違い、情報境界を保つ正規化 |
| trainer | 確認したPyTorch model sourceはinference onlyと明記。forwardはlogits等を返す | 公式trainer、loss、optimizer、schedule、samplingを今回確認できていない |
| 学習データ | model cardにGiftEvalPretrainの重複除外、Wikipedia、Google Trends、合成・augmentationの概略 | 完全なsnapshot、混合比、多変量group、augmentation recipeと利用条件 |
| 学習量 | blogに330M parameters、1兆超time pointsのcorpus規模 | 実際の学習step/epoch、precision、hardware、時間、FLOPsは確定できない |
| 旧資料との関係 | model cardの引用は旧TimesFM論文。READMEのLoRA案内は2.5の改善項目 | 旧論文・2.5の手順を3.0の公式学習仕様へ自動転用しない |

構造・推論の確認には上記source、規模とデータ概略にはmodel card/blogを使う。分位点を出すことだけから、公式lossがpinball lossだと断定しない。1兆点というcorpus規模からGPU時間や必要予算を逆算しない。

### 再現の三段階

| 成果 | 現時点の判断 | 完了の根拠 |
| --- | --- | --- |
| 構造の実装 | 検討可能。公開sourceが具体的な出発点 | 採用revision、仕様と実装の対応、shape/mask/正規化の小さな確認 |
| 独立データからの学習 | 独自recipeを設計する研究として検討可能 | 利用可能なデータ、独立初期化、独自loss・sampling、有限の学習予算、baseline/ablation |
| 公式学習・同等性能 | 今回の情報では実現可能と判断できない | 学習情報の補完、データ・資源、未使用評価での実証 |

小型版で成果が出ても、公式330M版の完全再現や汎用zero-shot能力の再現と呼ばない。産業用途に必要な一部の価値を得ることと、汎用foundation modelを再現することも別に判断する。

## 4. 利用条件と独自学習の経路

公式READMEはrepository source codeをApache-2.0、TimesFM 3の事前学習済み重みを別の非商用licenseとしている。許可されたGoogle Cloudサービスでの商用利用は別の経路として説明されている。[公式の区別](https://github.com/google-research/timesfm#license-notice-for-pretrained-weights)

重みlicenseのNon-Commercial Purposeにはcommercial decision-making/client deliverablesの制限があり、商用モデル向けtrain/fine-tune/distillも除外される。OutputsをDerivativeに含めない規定だけで、商用蒸留を許可されたとは扱わない。[license本文](https://huggingface.co/google/timesfm-3.0-pytorch/blob/main/LICENSE)

| 経路 | 研究での扱い |
| --- | --- |
| 既存重みの利用・fine-tuning | 元重みの条件を維持。商用適合への切替を自動承認しない |
| 元モデルの出力を教師にする蒸留 | 独立データ学習とは別経路。上記制限を確認せず商用向けに開始しない |
| 別licenseの公開コードを基に独立初期化・独立データで学習 | 候補経路。使用fileのlicense/notice、資料、データ、成果物の条件を個別確認する |

今回の記録は公開情報と既存研究結果の整理であり、商用採用の決定・利用許諾・権利適合の保証ではない。「自分で学習した」という一点だけで問題が解消したとは判定しない。新しい重み利用では用途と対象versionの条件を確認する。

## 5. 最初の独自モデル研究案

仮説案: 時間方向の予測に系列間attention・共変量を加えることが、選んだ産業用途で単純baselineより有効か。

最初は独立初期化の小型モデルで、公開構造のうち検証する要素を限定する。公式学習の再現と呼ばず、独自recipeとして設計する。入力patch、未来mask、正規化、系列間attention、分位点headの対応仕様を先に書く。loss候補としてpinball loss等を検討する場合は独自選択と明記する。

全要素の組合せgridは開始しない。基本構成と、仮説に対応する一つのablationから始める。公開TimesFM sourceを再利用する案と、関連公開情報から自作する案の差も記録する。ゼロから全fileを書くこと自体を成功条件にしない。

### 設計unitの保存（2026-10-13）

[小型独自モデルの設計](timesfm3-small-model-design-2026-10-13.md)へ保存した。次はoptional環境と最小forward/mask/lossの実装確認。下記は今回整理した設計範囲であり、新学習はまだ開始しない。

**独自小型モデルの構造・学習仕様を一枚にする。**

- 外部sourceの採用revisionと使用fileの条件を固定し、mask/shape/正規化/出力headの対応表を作る。
- データ候補の利用条件・学習/調整/確認splitを整理する。既存登録holdoutと分離する。まだ新データ本文を読み始めない。
- 対象用途・予測時間幅の暫定案と未決事項を明示する。外部データで確認できる範囲を区別する。
- 小型の層数・幅・系列数・window・batch・optimizerを候補として、parameter/activation/gradient/optimizer-state等の資源を見積もる。payload下限だけで容量合格としない。
- 有限の実行計画と終了判断を決める。精度の万能合格閾値や元モデル同等性能を先に約束しない。

このunitは設計まで。実際の学習はデータ・用途・利用条件・資源が具体化してから必要な範囲で進める。少量dev研究の開始条件にformal/nativeの全面完成を戻さない。

## 6. 維持する境界と終了判断

実行上限900秒/private 2GiB/output 1GiB/single 32MiB/files32、EvidenceStoreの分割・失敗予備、Git上限を維持する。既存MetroPT評価のwhole-process peak約2.77GiBは現上限内の再実行許可にならない。新たな大型学習の予算・上限は承認済みとみなさない。

完成モデル・試験・CI・replayは反復しない。閉鎖rootへ追記しない。既存の失敗と144cellの原証拠を保全する。今回追加agentは人が明示依頼したAstraの読取り調査のみ。automationへ詳細結果やPC内入力pathを転記しない。

formal gate=s4_acceptance_not_frozen、formal_permission=false、credit=0、登録holdout観測未読、native reader禁止、正式受入・方式採択未完了を維持する。

次の設計から「小型構造の実装へ進める」「足りない公開情報・データを先に調べる」「資源内では別構成が必要」「価値が見込めず保留」のいずれかを根拠付きで判断できればよい。比較数・監査数の増加を研究の成功条件にしない。

## 独立小型モデルの一回探索（2026-10-14）

[実装・学習・選択・予測の結果](timesfm3-small-model-pilot-2026-10-14.md)。独立学習経路は成立したが、TimesFM3同等性能や用途適合は未確認。上記の設計時点の次unit記述は履歴として保持し、次は実用性の対象/先読み時間/判断の具体化を待つ。追加gridを自動開始しない。
