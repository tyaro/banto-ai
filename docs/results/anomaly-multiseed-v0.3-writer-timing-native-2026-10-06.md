# v0.3 保存済み入力によるwriter限定時間計測（2026-10-06）

## 結論と範囲

clean `a8df8656643798ece1311924ebaed1ae00ca5afa` のWindows実機で、writerだけを既存 **60秒 / private 512 MiB / stdout・stderr合計64 KiB** の上限で実行した。supervisor全体56.561秒、writer内55.842秒、PID35288・exit0・元handleで終了確認と回収、5 payloadのローカル公開が完了した。上限までの余裕は3.439秒で、反復性能や全工程の安定成功はまだ示さない。

[e03の全工程試行](anomaly-multiseed-v0.3-generation-publication-retry-native-2026-10-06.md)の入力と数値結果をそのまま再利用した。数値由来は `8cac6fae93242747675fa67853a30a5e17ccef06`、今回workerは `a8df865` と別欄に保存し、旧revisionを変更していない。11ファイル / 8,076,367 Bを旧期待pinで読取り、新rootへ排他的にコピーした。生成、観測の再導出、50,000 draw計算・算術監査、owned fresh reader、全工程の外側予算測定は実行していない。

正式gateは `s4_acceptance_not_frozen`、正式許可false・credit0、登録holdout40 seedは未読。e03のfailed、fresh reader未起動、公開後の最終control等の未実施は維持する。

## 実装と試験

- 初版code `9b34b0e280e1de7b7ffd25665d7c460c48a25c09`。[通常publication処理](../../src/banto_ai/anomaly_v03_saved_row_document_publication.py)を共通の `_perform` へ整理し、[限定profile](../../src/banto_ai/anomaly_v03_saved_writer_profile.py)から同じ処理を呼ぶ。通常経路の検証内容と順序は維持した。
- 初回source検証・retained検証、stagingと公開、2回のmarker前境界と公開後の最終境界を計測する。各retained検証の読取り、入力・claims検証、主mapping、slice mapping、独立count監査を区分する。**retained／count監査は合計4回**で、公開前callbackはpayload renameの前後に各1回呼ばれる。
- 専用journalは工程開始前と終了時に排他的ファイルを保存する。1ファイル4 KiB・128 event・journal合計64 KiBで停止し、hard stop時は開始済みの未完工程が残る。記録・I/Oの時間も計測値に含む。
- 初版の焦点試験は固有22件（新9件／既存13件）がpass。最初の実行ではimportしたTestCaseが6件重複収集され、28実行 / 146.211秒だった。commit前にmodule importへ整理し、重複収集を防いだ。
- 初回実機でruntime adapterの引数漏れを発見。`a8df865`でrepository rootを渡すよう修正し、autospec付きのadapter／起動前失敗保存試験を追加した。追加・関連2件は別runでpass（14.957秒）。試験追記の初回配置ミスによるNameErrorも修正し、失敗概要を保存した。上記実行数を単一runの受入件数に加算しない。

## 2つの保存root

| 試行 | revision | 状態 | 起動したworker |
| --- | --- | --- | --- |
| `trial-20261006-profile01` | `9b34b0e` | runtime probeのTypeErrorで起動前failed。supervisor 0.063秒。公開rootなし | 0 |
| `trial-20261006-profile02` | `a8df865` | writer限定verified。supervisor 56.561秒 | 1、exit0・回収 |

rootはすべて `artifacts/anomaly-v03-preformal-saved-row-document-budget/` 直下。helper／期待値／checkerは `artifacts/anomaly-v03-writer-profile-20261006-p1/` と `...-p2/`。旧rootを上書きしていない。両試行の準備と終了後Git照合はwriter時計外で、p2のhelper全体は84.861秒だった。

runtimeはWindows11 Pro 26H2 / build26300 / UBR9457、CPython3.14.0 / AMD64 / MSC v.1944、local NTFS。supervisorの前後runtime一致、observation errorなし。peak worker private 68,452,352 B、stdout7,977 B、stderr0 B。終了後の空きRAM9,783,222,272 B・disk401,524,404,224 Bは観測値で、正式同形容量2倍の証拠ではない。OS契約採択、stdlib／拡張／DLL等の全在庫は完了していない。

## 保存された時間内訳

各retained検証内の**重ならない工程**の合計。sourceは初回と3境界を合計した。時間は秒。

| 工程 | 初回 | 境界1 | 境界2 | 最終境界3 | 合計 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 入力読取り | 0.301 | 0.730 | 0.752 | 0.811 | 2.593 |
| 入力検証 | 0.079 | 0.264 | 0.242 | 0.200 | 0.785 |
| payload読取り | 0.257 | 0.759 | 0.503 | 0.931 | 2.451 |
| claims検証 | 0.003 | 0.017 | 0.009 | 0.057 | 0.087 |
| 主mapping | 0.081 | 0.169 | 0.383 | 0.376 | 1.009 |
| slice mapping | 3.353 | 8.104 | 7.887 | 9.164 | **28.509** |
| 独立count監査 | 2.831 | 2.818 | 3.533 | 2.784 | **11.966** |
| source再照合 | 0.030 | 0.141 | 0.087 | 0.157 | 0.415 |

4回のretained全体は48.529秒。staging／公開の34.033秒には境界1・2の計27.690秒を含むため、表へ重複加算しない。境界を差し引いたstaging／公開部分は6.343秒で、個々のwrite・inventory・rename・markerの細分時間ではない。parentのruntime probeは前0.096秒／後0.044秒、source／request境界は前0.031秒／後0.086秒。

slice mappingと独立count監査の合計40.475秒がwriter内55.842秒の約72.5%を占めた。これが今回の改善対象を示す。e03では工程記録がなく、負荷も同一ではないので、前回の60秒timeoutの原因を断定しない。

## 保存照合と主要pin

p2の別checkerは171 raw／43 selected Git source、コピー11入力の旧rootとの一致、数値／worker revisionの区別、request／reply／元handleのPIDとcreation token、exit0、runtime一致、worker82 event／14,444 B・parent12 event／1,887 Bの順序・nesting・全工程終了を照合してpass。5 payloadとmarkerの普通の保存読戻しもcheckerで照合したが、これはworker時計外の読みで、owned fresh reader実行ではない。4回のcount監査終了はjournalで確認し、checker自身は数値・mappingを再導出していない。

p1も別checkerで23 raw／43過去Git sourceと起動worker0・公開なしを照合してpass。修正後のworking sourceを過去sourceへ読み替えていない。科学計画／freeze registryの既存hash一致もp2 checkerで確認した。rawはignoredのローカル保存で、Git pushには含めない。

| p2のraw | bytes | SHA-256 |
| --- | ---: | --- |
| `result.json` | 47,070 | `fe2aef881665759af76c336ceac6869578076f2be54ae798430c64aeab65d419` |
| `writer/request.json` | 8,746 | `876133c38d05845421954f479d34c2164a99145885352d887eaa902ded6db77d` |
| `writer/supervision.json` | 2,192 | `7d5c0585a04bb58127b0bf01a61a1a4fa5d40772ba3acc726b546980c9348658` |
| `writer/launch.json` | 136 | `7fc3b0d4da2ecb9780aeff4e539f5441d2418133dd00e5871f00f4f26a422c69` |
| `writer/worker/report.json` | 7,977 | `e87aef7966065d5e94bfb025308db52b16055f013077a89a399b5fa91f376a57` |
| helper `execution.json` | 479 | `bddd2b7b49b876fd2e047306bb16b5171b7fb97df212bf6b52e34181eb00f285` |
| helper `check.json` | 38,259 | `0ef5b8d1625fe869ad176e20b321a3bee8b4fd519c0fdb3e3928ee7591806ce0` |

marker SHAは `7a9a5f675e85931197115f961e70de2c92bafde03398cf152cffa247f74a0b2b`。PID35288のcreation tokenは `dbc136f468af1bec206f2d2e3db83fd66a44b7146fee9ecda236231378e0ccd3`。

旧e03 writer requestは8,097 B / `dfcf5961785ff5b6b5d6ddba85610874387200eeefa1b5b87904d1742bf6f094`。p1のresultは10,461 B / `d467547a6bef0ebbeb5f5eb535fa6a0607f4dc2082f67e82f6ddf9b27b2d919f`、起動前failure checkerは10,926 B / `28675af4d34e695991388fcfe3925a87b262482cc2457546c86f4ca9cb247409`。

## 次の範囲と正式残件

次はslice mapping／count監査の重複走査を調べ、境界の入力pin照合と同じ導出結果の検証を維持して時間の余裕を増やす。実機再測定は保存済み入力によるwriter限定とする。上限の拡大や生成／50,000 drawを含む全工程の自動反復を追加しない。

修正codeと同じ `a8df865` の [CI37398623472](https://github.com/tyaro/banto-ai/actions/runs/37398623472) は記録時点で両minorのunittest実行中。最終CI成功や全journal照合はまだ主張しない。最新の保存検証済みCIは先行 `8cac6fa` のrun37340158371。

正式受入の残りは、共通全工程予算の成功証拠、正式同形容量2倍、26H2・保証A/B・runner同定を含む改訂契約採択、source/runtime全在庫、最終revisionでのCI/native・正式dev8/smoke2・独立受入、独立raw観測再導出。今回のwriter限定成功でこれらを完了へ変更しない。追加agentは起動していない。起動したwriterと保存checkerは終了している。
