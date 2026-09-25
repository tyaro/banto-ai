# readerの依存候補を事前保持して別実行と照合

2026-09-25 JST。実装 `0b2da336d90bcc60e97798d83d17d9f6f7421a34`。[API](../anomaly-v03-reader-profile.md)。OUT `artifacts/reader-dependency-profile-2026-09-25`、最終成功 `final/`。文書保存revision/pinは最上位savepoint-evidence.json。

## 結果

prepare_profileを追加し、別に完了した依存観測を外部result pinから認証して候補fileへ保存した。後続readerは起動前から保持した候補へ、source/runtime/全依存一覧を前後比較する。候補を16番目の入力として既存証拠へ結び、返された観測や保存copyから期待値を採り直さない。

保存例のreference PID40904 → 後続reader PID29764は別process。両方exit0/reaped、観測error0。232file/177modules/48loaded images（project source28）の前後一覧が保持候補と一致。観測bytes47,580,270。候補110,646bytes/SHA256 `a682eb680def9a61227696de7f76c6d6259d99705403cb150e41933ebb66a0ab`。reader監視1.846秒、stdout240,593bytes。

## 検証

最終新規16試験pass、failure/error/skip0、53.083秒。先行候補の全41試験もpass、81.129秒。その後の変更はprofile作成側の保存先保護と同testのみで、reader/依存採取の既存26種類は不変のため再利用（unique42、最終全42再実行ではない）。先行候補の成功記録も保存。

検出した条件は、候補pinの誤り、raw内容不一致、役割/mode/revision/root/採取境界違い、OS更新、module追加・欠落、file identity変更、再封印された子の一覧、終了後の保存候補差し替え、作成元pinの誤り、元publication内への書込み。module欠落候補は子の公開結果検査前に拒否され、子は終了回収済み。元publicationのbytesは不変。

最終試験harnessのpeak private 52.46MiB、保存例readerのpeak 36.85MiB。資料作成前は空きRAM 10.35GiB / commit余裕 18.89GiB、C/D空き 126.00/326.57GiB。 最終保存値はsave-checks.json。子30秒/512MiB/output1MiB、profile512KiB、依存512file/1file64MiB/合計256MiBは維持。親preflight/Gitを含む正式総予算は未確定。

候補checkout `C:/Users/TKent/.codex/worktrees/rp01/banto-ai` はclean 0b2da336d90bcc60e97798d83d17d9f6f7421a34、746tracked files/8,461,710bytesのGit/raw一致を検査。前工程rd01もcleanで保全。元70b0の既知CRLF差、既存dirty文書、実計算checkoutと本流、closed、旧保存点を保持した。架空入力原本はtemp cleanup済み。候補profile・reference/readerの観測・期待値・monitor/reportは残る。

## 未完了範囲

別referenceから作る候補を事前に保持して照合するengineering接続。profileそのものの正式な採択、完全依存閉包、memory codeの真正性、作成process自身・解析/auditの役割別証拠は未完了。Windows更新は記録したうえで新候補を準備でき、旧候補の自動上書きはしない。

解析側（engineering consumer）の実行観測と、別に保持した役割別期待値の接続を、小さな架空入力で具体化する。reader候補をanalysis/auditへ使い回さない。 正式consumer/最終auditと全体予算も残る。既存document_draft.analysis_consumer=null、formal/promotion/S6/trust/execution_authenticated/full closure=falseを維持。

旧54code/18dataの意図的変更はadapter/collector2本、profile API/test2本追加。新評価/登録データ/実bootstrap0。banto-24 PAUSED、正式gate/holdout/freeze・principal/UAC/ACL・push/mergeは開始せず、Phase2/3全体は未完了。
