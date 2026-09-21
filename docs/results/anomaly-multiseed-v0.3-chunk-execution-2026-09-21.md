# 新しい6評価の生成から別process監査・journal確定まで

2026-09-21 JST。接続実装 **8b343873e052103fb78fd304551eba09c8015bfc**、path長の事前検査 **25d1084ecf8f24f17fe6f8f5b253c317bc80daa7**。
[実行方法](../anomaly-v03-independent-audit-and-checkpoints.md#新しい6評価を別processの監査まで通す) / [短い引継ぎ](../current-handoff.md)。

## 実装と選抜検証

ユーザーから「このPCで他の作業をしていないので大きめの作業OK」と連絡を受け、同時作業への制限を緩和した。資源監視と途中保存を継続し、native接続と新規の実6評価を対象に進める。全campaignの自動起動、旧正式gate、専用principal試験の扱いは変更しない。

`NativeCallbacks` と `run_anomaly_v03_chunk.py trial` を追加した。固定sourceのproducer workerが新しい結果を生成・公開・writer終了後再検算し、別processの独立ledger auditorが保存score以降を検査する。controllerがさらに実証拠を照合してjournalを確定する。各監視を専用format/対象/argv/runtimeへ結び付け、外部receiptをrunning/saved/verifiedごとに保存する。

CLIは新しい親と最初のdev chunk/attempt 1だけを確保し、開始前に `request.json` へ対象・source revision・plan hash・上限・実runtimeを記録する。producer900秒/2GiB・payload1GiB・ログ1MiB、audit600秒/1GiB・ログ8MiB。旧試行はコピー・再ラベル化しない。controller内fresh検算は既存readerの開始/終了資源検査で、controller全体の強制停止上限や全campaign予算は残件。

新規11＋controller12＋producer6＋監視13＝**42件pass/77.920秒/failure・error・skip0**、safety/diff-check pass。小規模実ファイルIOでsource/runtime/schema/数値/processのmockを明示し、既存監視テストのprintのみの実Windows子processも含む。初回新10件は1 error/1 failure、fixture PIDとResourceStopの継承に起因する誤分類を修正して10件pass。レビュー指摘の診断出力失敗時の所有権保持、監視保存失敗時の一次停止保持を修正し、追加回帰を含む最終42件へ進めた。独立再レビュー残存0/進捗poll0、担当の試験・編集なし。

選抜試験PID6388/exit0、peak private **67751936 bytes（64.61MiB）**。UTC2026-09-21T12:03:34.561204+00:00、空きRAM13259005952/C174399447040/D119513935872 bytes。Windows26200.9457/CPython3.14.0、exe/DLL hashと試験前後runtime一致。Windows Update engineering緩和・旧正式pin不変。

## 実データ接続試行

最初は8b34387のclean worktree `C:/Users/TKent/.codex/worktrees/engineering-chunk-20260921/banto-ai` の `artifacts/anomaly-v03-chunk-trials/trial-01` で実行した。数値/sourceのmockなし。5件を保存した後、6件目quality-stress/C2の保存pathが261文字となりFileNotFoundErrorで停止した。worker PID17252/exit2/終了確認済み、258.007秒/peak private249008128 bytes。controllerはrunning→failedを記録し、markerを公開しなかった。54 files/107889570 bytes（約102.89MiB）を失敗証拠として保持した。

stage/payload双方の登録保存先をUTF-16単位で248文字未満とする事前検査を追加した。trialの出力確保前、workerのsource収集前、callbackのprocess起動前に拒否する。Windows設定やIO共通APIは変更しない。path境界・出力未確保・Unicode長を含む新13件pass/22.771秒、限定独立レビュー指摘0、safety/diff-check pass。

修正revision25d1084の短いclean worktree `C:/Users/TKent/.codex/worktrees/v03/banto-ai` で新しいtrial-01を実行し、**connection_trial_verified / exit0 / 6 success・0 failed・0 inconclusive・0 not_started** となった。旧失敗出力を再使用せず、同じ登録6枠を最初から生成した。source390 filesを固定し、payload41 filesを公開した。journalは **running→saved_pending_verification→verified_complete**、外部receipt3件と最終descriptor hash `3aa4f1a0511f3671afa093145c34f01c17435781771ede4963d53e8a76b5b8ca` を保持する。次の未検証chunkは1だが、このtrialを全campaignへ加算・自動継続しない。

| 実測範囲 | 時間 | peak private bytes |
| --- | ---: | ---: |
| producer（公開前・writer終了後の両再計算と終了まで） | 666.089秒 | 341819392（326.0MiB） |
| 別processの独立ledger audit | 91.316秒 | 189100032（180.34MiB） |
| controller（初期source照合から全体終了まで） | 1008.679秒（16分49秒） | 221065216（210.82MiB） |

producer PID15676とaudit PID23244は両方exit0、終了確認true、stop_reasonなし、観測エラー空。private bytesは各Python processの値で、読取り用Git subprocessを含むtree合計ではない。実行後に誤解を避けるdocstringの修正だけを行い、実行したsourceは25d1084として固定する。

成功試行全体は **68 files/133323148 bytes（約127.15MiB）**。失敗分との合計は241212718 bytes（約230.04MiB）。marker二名の論理量を含み、worktree/sourceや候補内の小さな記録を除く。UTC **2026-09-21T12:32:07.339235+00:00** の終了観測で、空きRAM **13116989440** / C **174142107648** / D **119513669632 bytes（D約111.3GiB）**。実行前後のOS26200.9457/CPython3.14.0とexe/DLL hashは一致。長期リーク不在の評価ではないが、所有workerは両方終了し、controllerの終了時privateは68861952 bytesだった。

ローカルの選抜ログ・実試行driver/log・結果pinは候補内 `artifacts/chunk-execution-2026-09-21` に保存する。本流889cfc3/cleanと既存dirtyの親policy文書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621は保持・commit除外。前回attempt-controller証拠も保持する。

## 次に広げる範囲

この試行は新接続の実行確認であり、全120区切り/720評価の成績へ加算しない。次は実測を使って全dev/smokeのsource・consumer・完全runtime inventory・時間/メモリ/保存容量を確定し、複数区切りの継続入口へ進む。初期callback setup後の935.916秒を120倍すると **約31.2時間**、今回の全出力を120倍すると **15998777760 bytes（約14.9GiB）**。初期source照合まで毎回行う場合の単純換算は約33.6時間。profile/score導出等の独立検算、bootstrap、holdout、性能評価は未完了。

旧6評価のproducer単体実測からの19.1時間/約14.8GiBは、独立auditとcontrollerのfresh照合を含まない。新しい試行の総時間と保存量を用いた推定は、seed/layout差・再試行・余裕を含む保証ではなく、予算検討用の単純外挿として区別する。元の科学的条件や候補選択は変更しない。
