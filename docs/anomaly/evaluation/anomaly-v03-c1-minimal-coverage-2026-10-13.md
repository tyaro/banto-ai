# C1代表ケースの既存確認範囲と不足
更新: 2026-10-13。既存テストsourceと保存済み原結果の対応整理。今回の新モデル・テスト実行は0。

## 確認範囲

|代表ケース|既存テストの範囲|保存済み接続証拠|残る範囲|
|---|---|---|---|
|同一運転内の段差・持続偏差|test_hand_C0_C1_residual_and_no_profile_or_score_quantizationは水準残差・正規化を確認。test_no_episode_from_singleton_and_long_run_has_unique_onsetは入力済みscoreからepisodeを確認|layout11 core C1のmatched-targetsに原event・対象source・equipment・2support scoreの対応がある|任意の小さい段差入力をscorerからepisodeまで通し、期待する数値とonsetを手計算で固定する単独ケース|
|正常運転切替|test_first_observation_unknown_then_observed_entryは観測された入口でphase0、次点phase1を確認。test_profile_change_gap_unavailable_and_low_score_reset_runsはprofile変更時のresetを人工scoreで確認|layout11 core motor_currentの7259–7262はstartup→low_speed。入口phase0でnull/streak0、次2点は利用可能・閾値未満・streak0、source_episode_idなし|切替直前の単発超過を切替後へつながないことを、同じ小入力のscorer→episodeで明示するケース|
|欠測を挟む超過|test_current_and_previous_self_quality_all_candidatesは自分のcurrent/previous品質除外。episode resetテストは人工scoreのunavailableを確認|layout11 quality cycle09 C1の対象窓でphase不能、current品質不能3点、previous品質不能1点、残り2点は閾値未満。原candidate0/delaynullで欠測をまたいだepisodeなし|利用可超過→欠測→previous不能→再び超過という小入力で、前後を連続2点に数えないことを明示するケース|
|閾値と等しい点・単発逸脱|test_M8_equality_does_not_exceed、test_C0_strict_four_and_C1_strict_six_no_threshold_tolerance、singletonテスト|今回は保存証拠の追加計算なし|scorer接続の少数ケースへ等号と単発を含め、同じepisode単体テストを再実行しない|

既存テストの関数が存在することと、今回そのテストを実行して成功したことは別である。
今回のテストsource読取りは、保存済みCIの再実行・再取得や新しい実行successの主張ではない。
保存済み合成devの接続は、その入力で観測した動作の証拠であり、手計算した任意段差や実設備の誤警報率を証明しない。

## 原証拠

最新の保存rootは artifacts/representative-c1-minimal-coverage-20261013-continuation。原対応証拠は閉鎖済み artifacts/representative-c1-minimal-coverage-20261013-records の保存prefixを参照。文書準備時の対象文字列不一致によるfailedを保持する。
coverage-source-mapは選択した既存関数の名前・位置・source pin、saved-C1-connection-evidenceは原result pinと抜粋の対応を保存する。
sourceの本文抜粋はローカル検証記録だけに保存する。

- layout11 core: 既存C1原結果とmatched-targetsを読取り。モデル再computeなし。
- 正常切替: motor-01.motor_currentの7259–7262。切替前profileと切替後profileが異なり、phase0のscore/residualはnull、streak0。phase1/2のscoreは約0.373で固定閾値6を超えない。全4行のsource_episode_idはnull。
- layout11 quality: 既存cycle09 C1原event/incident/対象7scoreを読取り。不能を0補完しない。
- 過去layout11 qualityの3cellは保存済み144cellに含む。方針変更でその原結果を削除したり、未実行に戻したりしない。大量比較の拡張はここで終了する。

## 次の最小確認

次unitは上表の不足3組合せに限ったC1の小さい接続ケースの設計・実行。
正常profileを明示したfixtureと手計算の期待値を使い、scorerの原出力をepisodeへ直接渡す。
段差、切替、欠測の期待値・利用不能理由・streak・support・onsetを保存する。
既存テスト関数の再実行、dataset/layout sweep、追加C0/C2評価は開始しない。
実装不具合を観測した場合だけ修正し、影響する失敗ケースだけ再確認する。

これはC1の正式採択ではない。C2はC1で拾えない具体的な検知対象が定義されてから検討する。
実行側900秒/2GiB/output1GiB/single32MiB/files32、Git30秒/16entry/512KiBを維持。
EvidenceStore16MiB/512files/part256KiB/失敗予備2MiB16files・閉鎖予備を維持。閉鎖root追記0。
formal gate=s4_acceptance_not_frozen / formal_permission=false / credit=0 / holdout未読。
正式受入未完了、native reader禁止、追加agent0、automation設定変更0。

[最新の引継ぎ](../../current-handoff.md) · [方式の理論検討と最小の実装確認](anomaly-v03-minimal-validation-policy-2026-10-13.md)
