# 監査済み集計入力と公開記録の結合

2026-09-25追記：[engineering consumer入口](anomaly-v03-engineering-consumer.md)へ接続済み。結合receiptと同じ入力の記述結果を選択し、数値を再計算せず専用directoryへ保存・読み戻しする。以下は結合API自体の仕様。

`anomaly_v03_consumer_analysis_binding.authenticate_analysis_binding` は、[公開・終了記録reader](anomaly-v03-consumer-publication.md)の保存済み結果と、独立監査から作成済みの集計入力を照合する。数値や区間評価を再計算せず、導出元と採用attemptの対応を固定する。[確認結果](results/anomaly-multiseed-v0.3-consumer-analysis-binding-2026-09-25.md)。

```python
from banto_ai.anomaly_v03_consumer_analysis_binding import authenticate_analysis_binding

receipt = authenticate_analysis_binding(
    {
        "publication": publication_savepoint_path,
        "analysis": analysis_savepoint_path,
        "adapter": checkpoint_adapter_savepoint_path,
        "seeds": seed_counts_savepoint_path,
        "completed": completed_campaign_savepoint_path,
    },
    expected_mode="engineering-dev-smoke",
    expected_publication_pin=retained_publication_raw_pin,
    expected_analysis_pin=retained_analysis_raw_pin,
)
```

2つの外部pinは `{bytes, sha256}` で、呼出し側が既に保持した保存点のraw pinを渡す。publication/analysisのどちらかが一致しない場合は進めない。formal/未知modeはpathを調べる前に拒否。5役割の保存点pathは明示指定し、重複を拒否する。

## 認証するつながり

固定名の小型artifactを計10件、各1回読み取る。5保存点に加え、all-publication-checks.json、adapted-metadata.json、analysis-inputs.json、verified/authenticated-counts.json、evidence.jsonを読む。各ファイルに既存のサイズ上限付き固定hash readerを使い、上限合計は24MiB。古い報告内に保存されたpathは比較用にのみ使用し、観測rootやpayloadへはアクセスしない。

1. publication保存点とanalysis保存点のclosed pinが同一campaignを指すことを確認。
2. publication保存点からcheckpoint adapter・全120区間の読取結果へ、analysis保存点から集計入力・seed集計・完走保存点・旧evidenceへhashをたどる。
3. plan hash、journal count/head、全区間のidentity、全attempt履歴、最終attemptと過去失敗を照合。集計が初回の失敗結果へ戻っていないか確認。
4. 公開readerの8file/区間、計960参照を旧campaign evidenceのraw pinと照合。公開metadataの確認を全payload認証へ格上げした報告は拒否。
5. 全720評価について6種input hash（4,320照合）とevaluation hash（720照合）を同じ旧evidenceへ結合。これらはhash参照の比較であり、参照先のpayloadを開かない。
6. 10seed cluster、90seed表、18role表のIDと元集計欄の値を一致させる。診断欄を追加した集計入力でも、元のcount・null・CI未実施・profile status等を変更できない。判定不能指標数を維持する。

以前のslice算術・比率・bootstrapを再実行しない。集計入力の診断結合は、その生成時に検証・保存したartifactのraw hashを信頼の起点として再利用する。今回再読取りしたbytesと、旧監査から引き継いだ導出証拠を区別する。

## 戻り値と制限

戻り値は `anomaly-v03-consumer-analysis-binding-v1 / historical_analysis_inputs_bound`。元analysis-inputs.jsonへのpathとraw pin、読んだ10artifactのpin、閉包に使った外部anchor、attempt対応、照合数を持つ小さなreceipt。大きな集計入力を複製しない。

`publication_metadata_binding_verified` と `analysis_input_bytes_verified` はtrue。`historical_aggregate_authentication_reused` / `historical_diagnostic_join_reused` もtrueと明示する。元の判定不能値を成功へ変換しない。

source payload読取、score/集計再計算、新評価は0。`full_payload_bytes_verified`、controllerプロセス終了、source/runtime正式受入、trust、analysis/execution/formal/promotion/S6はfalse。bootstrapなし、performance未実施、selected_candidate=null。旧分析入力を再利用できる参照対応が確認された段階で、正式運用の契約案はdraftのまま。

次はこのreceiptを使って、engineering consumerの入力選択から記述結果までの入口をつなぐ。既存の独立監査と集計を再利用し、観測やscoreの再計算・正式gate/holdoutの起動は行わない。
