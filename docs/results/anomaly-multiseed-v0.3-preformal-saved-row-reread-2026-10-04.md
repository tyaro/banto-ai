# 架空保存rawの再読取りから６行投影までの共通予算（2026-10-04）

## 目的と境界

前の[部分行由来](anomaly-multiseed-v0.3-preformal-saved-row-lineage-2026-10-04.md)は、保存済みg02 reader resultとreportを新しいconsumerが再照合したが、今回のconsumer自身は131 MBのpayloadを再読取りしなかった。今回はg02の架空保存rootを外部pinで固定し、**新しい所有reader子が保存raw22件を再読取り・観測→profile/score→ledger→主/sliceを再導出してから、その結果を親の６行投影に結ぶ**。readerと投影は新rootの同じ外側予算・停止probeに置く。実登録holdout観測は扱わない。

対象は架空登録形式の１区間６評価だけである。g02の既存入力131,144,119 Bと起動前pinsetは**新rootの容量集計外**、読取りwall時間と子privateは今回の監督範囲に入る。前のg02生成子→reader２役184.919秒と今回の時間を合算して全工程予算とはしない。正式gate `s4_acceptance_not_frozen`、正式評価credit０を維持する。

## 保存試行

新しいclean code保存点とnative試行後に、result/予算receipt/所有子の終了・回収・pinと独立照合を記録する。

## 次の受入事項

この１区間が同じ予算で検証できても、残り479区間と40 clusterは成立しない。現g02のsavepointは区間番号と個別`run_root`を含むため、480件のsavepoint SHAを同一にする設計は誤りである。40 clusterへ進むには、区間別の外部pin・最新attempt・６行・凍結identityを検証する結合契約に加え、**区間間で共有するproducer/campaign由来anchor**が必要である。現在の登録registry pinや同じsource revisionだけでは、全区間が同一の実行から来たと証明できない。

S4前は架空の固定入力経路と最終dev8/smoke2で受入を行い、実holdout 480区間の成功を開始条件として要求しない。S4採択後のS5で未使用40 seedを実行し、S6で全件を独立再監査する。26H2運用契約、５役source/runtime完全閉包、Linux必須jobとrunner image、producerから公開後readerまでの単一外側予算も残る。
