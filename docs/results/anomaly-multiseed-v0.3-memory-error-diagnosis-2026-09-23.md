# v0.3 MemoryError停止の調査

2026-09-23 JST。停止の保存点は **3bba1bd5a6ff7e36653b10dedce33283ebabd63e**。対象は区間81〜104のcontrol000006で、新規区間開始前に発生したMemoryError。保存ログ・Windowsイベント・現在の資源・固定実装c01d1c9を確認した。数値評価や完了済み81区間の再照合は実行していない。

## 結論

**原因は未確定。Banto controllerの持続的なメモリ増大は観測していない。** OS全体のコミット余力不足やページファイルの拡張遅延は候補だが、停止時のコミット量・上限と例外のtracebackが記録されておらず、今回の原因とは断定できない。一時的な大きい割当要求やその他の割当失敗も排除できない。

新規確定0、累計81区間/486評価、残り39区間/234評価を維持。失敗した呼出しやheartbeatは再起動せず、OS設定・Python・固定実装を変更していない。

## 停止前後の記録

停止はUTC2026-09-23T02:57:30.180163（JST11:57）、exit2/MemoryError、messageは空文字。今回の実行時間は約3時間7分。保存された60秒間隔の185標本を集計した。

| 観測 | 結果 | 読み取れる範囲 |
| --- | --- | --- |
| controller lifetime peak private | 232960000 bytes、約222.17MiB | 2時間目までに到達し、その後の記録で増大なし |
| 各時間帯の標本private最大 | 約184.22 / 184.09 / 185.49 / 178.45MiB | 4区分目は最後の約7分。数GiB規模の蓄積は観測なし |
| 終了時controller private | 159330304 bytes、約151.95MiB | 設定2GiBを超えたという記録ではない |
| 終了時空き物理RAM | 7879757824 bytes、約7.34GiB | OS全体のコミット余力は分からない |
| 最終標本から終了までのC空き容量 | 161239666688 → 131049820160 bytes | 約26秒で約28.12GiB減少。原因ファイル・因果関係は未確認 |
| journal / 新規receipt | 全標本で243 / 0 | 完了済み区間の再照合中とみられ、新規producer開始記録なし |

直前の成功呼出しのcontroller peakは約225.6MiBで、今回も同程度だった。小さなリークの有無、失敗した割当の要求サイズ、標本間の変動まで否定するものではない。

Windows System/ApplicationのUTC02:40〜03:15を確認し、Systemは稼働時間の情報イベント1件、Applicationはライセンスサービスの情報イベント4件だった。Resource-Exhaustion-DetectorもUTC前日22:40〜当日07:15で該当なし。エラーが記録されなかったことは、一時的なコミット不足がなかった証明ではない。起動時刻は9月19日03:46 JSTのままで、今回の停止時に再起動した証拠はない。

## 約7時間後の状態

UTC10:03:22（JST19:03）の観測は、空き物理RAM約14.16GiB、システムのコミット約28.98GiB / 上限約44.42GiB（約65%）。C空き約144.83GiB、D空き約49.35GiBだった。Dは停止時の約108.96GiBから減少しているが、別時点の観測であり、停止原因との関係は未確認。

ページファイルは自動管理、Cの確保量13022MiB、現在使用4071MiB、報告されたpeak使用9499MiB。ファイルの最終更新UTC08:11:23は停止後であり、これらの値から11:57時点のサイズや利用状況を復元できない。現在の上位process一覧も診断証拠へ保存したが、停止時の負荷主体とは扱わない。

Windowsでは物理RAMの空きと、OSが追加割当を保証できるコミット余力は別の指標である。Microsoftは自動ページファイルの拡張遅延による割当失敗も説明している。ただし今回のイベント・保存ログだけでは、それが発生したか判別できない。参考: [ページファイルとコミット上限](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/how-to-determine-the-appropriate-page-file-size-for-64-bit-versions-of-windows)、[自動ページファイルの拡張と割当エラー](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/slow-page-file-growth-memory-allocation-errors)。

## 実装を確認して分かった記録の不足

- `anomaly_v03_attempt_controller.py` の `_revalidate_completed` は既存区間を順番に監査し、保持する確認済み集合はdigest文字列。全81区間のpayloadをまとめて保持する設計ではない。
- `_anomaly_v03_io.py` の `PayloadView` は要求されたファイルを読み、`anomaly_v03_saved_audit.py` は各評価の検証後に `value, raw` を解放する。単一JSONの読込み・解析には一時領域が必要。旧inventoryの最大payloadは25286581 bytes（約24.12MiB）、監査上限は単一32MiB。総出力約10.02GiBをそのまま一括読込みしているわけではない。
- `_anomaly_v03_engineering_runtime.py` の資源記録はprocess private/peak、物理RAM空き、disk空き。**システム全体のコミット量・上限とページファイル量は保存していない。**
- `anomaly_v03_campaign_launcher.py` の例外処理は型・message・closed stateのみ出力し、**tracebackや再照合中のchunk番号は保存しない。** 今回の正確な発生箇所を遡って決めることはできない。
- controllerの資源検査は境界で協調的に実施する。過去verified区間を確認するループ内にwrapper予算検査はなく、今回のMemoryErrorは設定2GiB超過による `memory_limit` 停止ではない。

## 次の対応

次に準備するのは、再照合の区間・処理段階、例外のtraceback、OS全体のコミット量・上限・ページファイル量を時刻付きで残す最小限の診断。保存元の固定実装・成果物を上書きせず、変更が必要なら別の保存点と実行条件を明示する。原因未確定のままページファイル固定化やPython変更を行わない。

長い再試行より先に、独立した出力先と明示上限を使う短い確認で診断の取得・資源・終了を検証する。今回の全81区間を原因調査だけのために自動で再照合しない。再開する場合も最新failed closed000006（SHA-256 `18af12a119e3acc0600594d8eaf6263607f5f7c85d68ff3acbda31931d4b9e4c`）と累積活動97603.864249秒、残り候補活動75196.135751秒を引き継ぎ、旧closed000005へ戻さない。

## 証拠と保全

今回の証拠は候補worktreeの `artifacts/memory-error-diagnosis-2026-09-23/` に分離した。`windows-events.json`、`current-resources.json`、`pagefile-file.json`、`pagefile-management.json`、`saved-progress-analysis.json` と、文書commit・各hashを記録する `savepoint-evidence.json`。以前の失敗証拠folderは変更しない。既存dirty親policy文書は保全・commit除外。本流・実計算source・累計件数は不変、追加agent・評価再計算・OS設定変更・push/mergeはない。コード変更がないため数値試験は繰り返さず、文書差分・pin・保全対象を検証する。
