# 検算済みfixtureの5ファイル公開と別プロセス読取り

`anomaly_v03_fixture_publication.publish_with_evidence` は、保存済みの架空解析・主集計とsliceの検算記録を受け取り、通常権限の所有writerで5ファイルを公開する。writerの終了と証跡を確認してから、別の所有readerで全公開物を読む。[実装](../src/banto_ai/anomaly_v03_fixture_publication.py)、[試験](../tests/test_anomaly_v03_fixture_publication.py)。

数値解析・検算は再実行しない。呼出し側が保持する過去のresult/evidence pinを信頼の起点にし、その保存済みbytesと公開内容の結合を確認する。過去processの実行真正性、正式な推論・S6・full closureをこの接続で認定するものではない。

## 入口と保持する入力

```python
result = publish_with_evidence(
    request,
    expected_revision=full_clean_candidate_revision,
    receipt_parent=ordinary_existing_parent,
    receipt_name="new-fixture-publication",
    budget_limits=None,
)
```

requestはformat=`anomaly-v03-fixture-publication-request-v1`、mode=`fixture`、inputs、analysis_reference、audit_referenceの5欄を持つ。formal/holdout/engineering-dev-smokeをこの入口へ流用しない。revisionは新しい公開実装の40桁revisionであり、過去解析・検算のrevisionとは別に保持する。

inputsは次の12ファイルを外部指定したpath/pin/linksへ対応させる。pathは絶対パス、pinはbytes/sha256、linksは1。記録内の任意パスは辿らない。

| 論理名 | 内容 |
| --- | --- |
| analysis/result.json | 過去解析のverified結果 |
| analysis/evidence.json | 過去解析の役割別証跡 |
| analysis/binding.json | 解析時の供給bytes照合記録 |
| analysis/document.json | 文書草稿・主表・slice・補助表 |
| audit/result.json | 主表＋slice検算のverified結果 |
| audit/evidence.json | 別実装検算の役割別証跡 |
| audit/verdict.json | primary_and_slice_numerics_matchedの範囲記録 |
| wrapper/analysis.json | 主表・文書草稿・小さいdraw |
| wrapper/coverage.json | 架空のcoverage宣言 |
| wrapper/diagnostics.json | 補助4系列と詳細表 |
| wrapper/execution.json | 解析時の入力・証跡・実施状態 |
| wrapper/verification.json | 当時の照合範囲と未充足 |

両referenceにはresult_pin/evidence_pin/source_revisionを指定する。入力を読み直して期待pinを作り直す運用はしない。入力総量12MiB、文書と各wrapper4MiB、それ以外各64KiB以内。既存の40cluster・最大8drawだけを受け付ける。

解析の文書・binding・wrapper pin、主表/sliceの入力pin、auditから元analysisへの参照と出力pinを結ぶ。旧primary-only auditは受け付けない。主9表/117絶対推定/72対応差/180gate、本文1,233行/補助2,835行/詳細9表の保存済み検算範囲を確認する。ここでこれらをもう一度計算するわけではない。

## 公開内容と自己参照の回避

保存済みwrapperは改行なしのcanonical JSON。通常公開はJSON末尾にLFを1つ要求するため、公開bytesは元bytesにLFを1つ加えたものになる。JSONの数値・内容は変更しない。`publication-binding.json` は元5ファイルのpinと公開5ファイルのpin、変換方式を両方保持する。

`published/payload/` の5ファイル、`marker-pending.json` と `.complete` を既存LocalPublicationで作る。markerは全payloadのinventoryを持つ。外部bindingが解析・auditの参照、marker、writer/reader evidenceを結ぶため、payloadやmarkerに自分自身のハッシュを埋め込まない。

元executionのwriter/reader/audit=`not_run`、published=falseは作成時点の記録として残す。後から行った公開・読取りは外部bindingと各役割receiptへ記録する。正式null4欄とready=falseも維持する。

## 実行記録と失敗状態

writer/readerはそれぞれ `-I -S -B` で起動する。親が選択source13本、Python2ファイル、12保存入力と専用invocationを保持し、元PopenのPID/生成時刻・argv・cwdと子の前後記録を結ぶ。両roleで終了後の依存file/Git照合も行う。依存inventoryは終了後照合であり、役割別の承認済み事前profileではない。

writerのexit0・終了確認・証跡検査が通るまでreaderを起動しない。writerの部分書込みや応答喪失はpublication_status=`unconfirmed`のまま保存し、完了markerだけで成功と推定しない。reader失敗時はpublication_status=`completed`とwriter receiptを保全し、全体statusはfailed。自動再試行・上書き・清掃はしない。未終了processは元ownerを持つ例外で返し、診断保存失敗でもownerを失わない。

## 資源予算と限界

新しい公開・両役割receiptを同じFixtureBudgetで監視する。共有120秒、親512MiB、directory32MiB/256entries/深さ8、commit/RAM余裕2GiB、disk5GiBを維持。各子60秒/256MiB/出力1MiBと従来の起動条件も維持する。[監視仕様](anomaly-v03-fixture-resource-budget.md)。

宣言した公開先の `.complete` と `marker-pending.json` だけ、同一実体・2リンクの組を許可し、両方の長さを容量へ足す。stage→payloadの通常renameと走査が重なった場合だけ、上限付き全走査を1回やり直す。任意hardlinkやreparse pointは引き続き拒否する。これは単一writerの協調監視であり、敵対的同時書換えやhard quotaを扱わない。

formal_permission/promotion/S6/trust/execution_authenticated/source_closure_complete/runtime_closure_completeはfalse。登録観測・coverageの真正性、正式運用契約、正式2,880評価/50,000反復の全体予算は別の残件である。旧4ファイル公開経路は変更しない。

[保存例と試験結果](results/anomaly-multiseed-v0.3-fixture-publication-2026-10-02.md)。
