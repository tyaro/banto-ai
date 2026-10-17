# 声かけまで継続するMac研究

2026-10-15 JST。人の最新指示「進めてください／こちらから声かけるまで自走して進めてください」が継続の委任。直前の有限campaignの終了だけを理由にroutineな再開承認を求めない。

## 継続の方法

このチャットにheartbeat `banto-ai-mac`（banto-ai Mac研究の自走）をACTIVEで設定し、15分間隔で未完了工程を継続する。旧Windowsのautomationを再開したものではない。
設定はCodex app toolで作成し、ローカルautomation.tomlを読取り照合した。手書きscheduler/cron/外部メッセージは使わない。最初のtool callはdestination不足のvalidation errorで作成されず、destination=threadで一件だけ作成。target_thread_id=01a13aae-d41f-7013-ba78-ecba0ace0944。
[公式OpenAIのheartbeatによる実装ループ](https://developers.openai.com/cookbook/examples/agents_sdk/agent_improvement_loop)をOpenAI Docsスキルで確認した。実際の実行はアプリの稼働・権限・利用制限に依存する。

人の新しい直接メッセージが来たら、新規実験より先にheartbeatをPAUSEDにし、その発言へ応答する。自動起動promptは人の声かけと扱わない。再開を明示された場合はその指示に従う。
各回は最新handoffを読み、未完了の一件を完了させるか、根拠のある次の一件を契約から実施する。無変化や同じ失敗を反復せず、結果と次の工程をhandoffへ蓄積する。仮説が尽き、意味のある作業を進められないときは理由を残してheartbeatをPAUSEDにする。

## 固定する境界

主目的は既存10店の将来販売数量の平均予測。CPython3.14.8、Mac arm64 CPU、原許可済み2013–2015だけ。mean28を対照に、原10店/250窓/3490日/240完全総量と欠測を保持する。2015は既読の探索的開発で、未知性能とは呼ばない。
毎実験の親900秒/子870秒、Mac sampled footprint/peakRSS各2GiB、通常artifact24files768MiB/全32files1GiB/single32MiB/失敗8files256MiB、EvidenceStore16MiB512file/part256KiB/reserve2MiB16fileを維持。全stdio/exit/source/state/失敗prefix/closureを保存する。
旧sourceやclosed rootsを修復・上書き・削除しない。Git push/外部送信/課金API/新データ取得/追加agent/本番採用なし。2016/2017/予約31–54/販促数量/正式holdout/Windows native/CAREを扱わない。formal_permission=false、製品採用0、CARE待ち。

## 今回の工程と次の候補

最初の工程は[発行日前の誤差だけを使う更新](demand-prequential-bias-design-2026-10-15.md)。固定模型/基準の過去56日以内に確定した自己予測誤差から店舗別のbiasを更新する。2014内部だけで更新量を校正・方式選択し、その後2015を順次評価する。
完了後は保存結果から、期間変化に対応できたかとMAE/過小過大の向きを判断する。性能悪化なら係数を2015で合わせ直さない。次の仮説は内部時間検証を複数期間に分けた安定性や、発行日時点での過去labelだけによる学習更新。具体的な契約・過去境界・支持を保存してから行う。
暫定2%改善/日次総量悪化なし/支持不変を通過しても、PSIの在庫/入荷/lead time/損失条件は未設定なので製品採用を認定しない。改善がなくても負の結果を残し、同一gridの無限探索へ移行しない。
