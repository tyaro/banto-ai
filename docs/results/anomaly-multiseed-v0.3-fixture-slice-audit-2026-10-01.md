# v0.3 架空slice・補助診断表の独立検算結果

2026-10-01、**保存済みの架空解析を再実行せず、主9表と条件別集計1,233行・補助4系列2,835行・詳細9表を別実装・別processで検算し、一致を確認した。** [APIと範囲](../anomaly-v03-fixture-slice-audit.md)。正式holdout、50,000反復、S6の実行ではない。

実装保存点は`b6d578e7c577470ecb2fbef228413d6b2abf85bf`、clean候補は`fs02/banto-ai`。検算本体を追加した`ced27e3895b00e6fadcbc21157b74d38112364de`/fs01も保全した。b6d578eとの差は1試験のデータ生成だけで、検算の実装は不変。

## 変更

- stdlibのみの`anomaly_v03_fixture_slice_audit`を追加。固定座標ごとの加算とdelay multisetの展開を使い、計算側のslice集計・mapping・validatorを呼ばない。
- 既存owned auditに`audit-invented-primary-and-slices-v1`を追加。slice入力の外部pinを元analysis記録へ結合し、主表とsliceの両検算が成功した場合だけ新scopeのreceiptを保存する。
- 元のprimary-only operation、5入力/6MiB、`primary-audit.json`の形式を維持。新operationはsliceを含む6入力/14MiB、`primary-and-slices-audit.json`を使う。時間・メモリ・directory等の資源予算は据置き。
- 新module/testの2本と既存worker/testの2本を変更。前保存点72codeのうち70本と18dataは不変。現在のcode pinは74本。

## 試験

対象はpure slice audit14、所有audit14、既存資源監視16の44項目。新しく追加した19項目（pure14＋worker5）と既存25項目を含む。

初回`tests-1`は44試験、43pass/1error、74.090秒。errorは試験が「異なる検出件数の2cell」を検索したが、対象の架空データが同じ件数だったためのStopIteration。検算処理へ到達する前の試験データ組立ての問題だった。classを跨いで検出1件と対応histogramを移し、合計を維持して周辺表との不整合を作る形へ修正した。

修正した1件だけを`tests-2`で再実施しpass、1.964秒。production source、通過済みtestの本文・setupが不変であることをGit差分・pin・ASTで確認し、旧43passを再利用した。**合計44項目の成功が揃っているが、最終revisionで44項目すべてを再実行したものではない。** 旧ログ・初回候補・旧harnessは保全する。

確認した改変は、本文のみ/補助系列のみ/詳細表のみの数値変更、重複/欠落/ラベル違い、合計を保ったjoint/marginalやtarget/modeの誤割当、histogram/profile/primary不整合、整数範囲・ゼロ分母・省略件数、入力差替え、operation降格・descriptor違い。新operationの実子でも、再封印した文書の不整合を検出してexit2、成功payloadなしとなることを確認した。

既存資源監視の16試験では、上限の締付け、模擬commit不足、directory超過、所有子の停止/reap、停止記録の保全を確認した。今回、正式規模の負荷試験やPC全体の長期リーク試験を行ったわけではない。

## 保存済み解析への適用

元は`fixture-resource-budget-2026-10-01/tests-2/shared-example/analysis`のverified解析、source revision=`cf4d9c42c11c202984aacdd71ac5efb0368f22d0`。元の数値入力・slice入力・文書・result・evidenceの5ファイルを前保存点のpinで確認し、新規rootへ保持してauditした。元analysis起動0、別audit1回、既存720評価再実行0、新評価0。

| 確認事項 | 結果 |
| --- | --- |
| 数値範囲 | 架空40cluster/4draw、主9表/117絶対推定/72対応差/180gate一致 |
| slice範囲 | 本文1,233行、補助4系列2,835行、詳細9表一致 |
| 所有子 | PID46224、exit0、終了/reap確認、observation error0 |
| 時間 | 全体10.469秒、子2.868秒 |
| 事前保持 | 選択source15本、Python2file、入力6file、output pin、親と子のprocess生成identity一致 |
| 依存観測 | project32/全236file、181module、native48、前後の追加0、終了後disk/Git照合成功 |
| 成功結果 | 全体/所有auditともstatus=verified、両resource_budget_passed=true |

出力`primary-and-slices-audit.json`は2,384bytes、SHA256=`be0a327a15db02a5881e51b682fefcdcfe05cae995a7443dc941647c51a863c4`。元文書は1,932,543bytes、SHA256=`2c20d80e63bf53e662ee722ba48f723285cf08182178036a2410a78d6033c6b1`のまま。原本5ファイルのpinを終了後も確認した。

## 資源

保持入力とauditを共通rootの予算に含め、41sampleで観測。directory最大7,063,820bytes（6.74MiB）/25entries、親harness peak100.68MiB、子peak66.58MiB。system commit余裕は最小12.24GiBで、停止条件への抵触や診断欠落はなかった。

保存例直後のRAM空き7.91GiB、commit余裕12.74GiB、C/D空き121.32/388.26GiB。OS25H2/build26200/UBR9457を記録した。正式runtime pin9168は変更しない。最終保存時の値は`save-checks.json`を参照する。

既定の共有120秒/親512MiB/dir32MiB/256entries/深さ8、commit/RAM余裕各2GiB/disk余裕5GiB、子60秒/256MiB/stdout+stderr1MiBを維持。sampling/協調停止でありhard quotaではない。今回の小例から正式2,880評価/50,000反復の予算を推定・採択しない。

## 範囲と次工程

T08/T12の**架空countからのslice/sidecar独立導出**とT09の追加入力・所有auditへの結合を完了側へ進めた。raw producer観測からcountが正しく作られたこと、登録coverage・正式推論、正式slice mapping採択、公開writer/readerとの結合、full source/runtime closureは未受入。formal/promotion/S6/execution_authenticated/closure=false、正式null4欄/ready=falseを維持する。

次は、既存wrapperが作る5payloadを通常公開・別readerへ接続し、このaudit scopeとwriterの実行記録を結ぶ。通常writer終了後に読み取り、公開receiptと科学payloadの自己参照を避け、失敗/応答喪失時の記録を保全する。元analysisの再計算や旧4payload公開の繰返しだけを目的にしない。正式gate・holdoutの起動や予算の拡大は含めない。

OUTは`artifacts/fixture-slice-audit-2026-10-01`。最終文書revision・74code/18data・各artifactのhashは`savepoint-evidence.json`。実計算c01d1c9、本流clean6f1285d、control000010 closed、既存dirty文書は不変。`banto-24`はPAUSED、旧候補/保存点/失敗記録を保持し、push/mergeなし。
