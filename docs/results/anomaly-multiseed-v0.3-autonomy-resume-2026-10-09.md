# 自走再開と現OS/runtime基本条件の実観測

2026-10-09T09:50:36Z、人の「ポーズ解除して走ってください」に従い自走heartbeat banto-10をPAUSEDからACTIVEへ更新した。15分間隔・対象thread・名前・保存済みprompt等の既存fieldsを保持し、過去の終了予約/PAUSED維持より今回の明示再開を優先する節を先頭へ追加。更新toolと保存automation metadataの両方でACTIVEを確認した。状態不変時は通知せず、意味のある完了・失敗・必要ユーザー操作だけ報告する。

## 開始時の保全

開始HEAD b4a0401680b0d938598c71ff890948f208eee2b5/origin一致・clean。先行元5helperのfull creation/start_tokenを保存live/executionへ照合し、CIM同original不在・repo helper/critical ownerなしを確認。旧CI失敗raw12file5360859B/metadata26file47469B/OS prep30file57845B/Python314 prep27file32705Bは閉鎖済みで追加・再実行しない。

再開metadataはartifacts/preformal-autonomy-resume-20261009-prep/へ新しく保存する。元capsは512KiB32entry/reserve128KiB/single128KiB、helperは30秒、Git batchは512KiB16entry/output1MiBのまま。元owner/unknown HANDLE/Python/streams/pending/partial保持と停止保全を維持する。

## 現環境の基本条件

改訂後のprobe_runtimeを現在のPCで一度だけ実行し、registry/volume/必要exportを読み取った。Job生成、ACL変更、process launcher、child transport、正式workerの実動作を呼んだ確認ではない。

- 実OS: Windows 11 Professional、26H2、AMD64、major/minor10.0、build26300、UBR9457、product_type1。
- 実storage: local NTFS、volume flags65482495、persistent ACL bitあり。
- 必要18 API exportの可用性を確認。behavior_verified=false。
- 通常GIL CPython3.14.0/MSC v.1944/source tag v3.14.0:ebf955d、元python.exe/DLL hashへ一致。
- runtime-basic-observation1214B/4792020c208422c33e60d5bbdf3c50d05825549ddbc51889d685ecf28d85422b。
- resume-observation1414B/90c65ecd1df3d29ab33fd0f34e5d92c8bef2f64fca6613d6ce678c231384b8d8。対象4sourceのworking前後/Git bytes一致を確認。

これは基本条件の実観測で、full loaded runtime/stdlib/CRT/DLL closure、原native owner、実API return tuple、実Job/DACL/token/publication/child endpoint-close-rename認証の受入ではない。runtime profile/private policy/native request/exclusive launcher/unused request rootはNone、capacity/auth/formal_permission=false。旧registryの25H2/26200.9168を今回の実観測へ読み替えず、旧117source/profile candidateも流用しない。

元observer33320/creation134360133339530308/start_token6d50a3caaa8bd7faf04ee1c1d4e3fd39d174518dc7ee80ee4b27644246839997はlive/execution full一致・passed。read-only CIMで同original不在、repo helper/critical ownerなしを確認した。native回収trueやlease/ackの証拠にはしない。

## 最新CIと次の範囲

CI37913386221/fullb4a0401680b0d938598c71ff890948f208eee2b5/attempt1/push/Phase 1 CI/.github/workflows/ci.ymlは一度の読取りでin_progress。原run JSON11696B/c9d10cc5b73b9890c060c9b028a0c6f1c0ba5f08f06e0a445b49f3acb97a9084とstderr bytesを保存した。jobs/終端/journal未固定、同状態の反復照会・待機・download/local全回帰/runner再実行0。原37907938074の3930件failure/verification skippedを新revision successへ書換えない。

次は未終端CIの変化と、same request-root/all-writer原owner/exclusiveからfresh latest-clean runtime-profile-private policy-request-unusedrootへ結ぶ未完成機能経路を扱う。全planned raw保存枠の32entry容量、原partialとnew growth/codec/native buffer/object overhead別量/global coupled peak、実callsite/stdio/child transport owner認証は未完成。準備前native入口/create_native早期拒否/全7役whole.run限定reader実起動禁止を維持し、完成focusは再実行しない。

formal gate=s4_acceptance_not_frozen、formal_permission=false、credit0、登録holdout観測未読、正式5残件と最終受入未完了を保持する。人の停止割込みやSol容量エラー時は新規実行を止め、原owner/安全な既存終端/証拠と短い引継ぎを保存してPAUSEDへ戻す。今回の再開文書はdoc-only skip ciへ集約する。
