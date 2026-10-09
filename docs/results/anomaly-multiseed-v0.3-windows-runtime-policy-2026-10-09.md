# Windows OS条件の見直し

2026-10-09、人の「進めてください」に従い、OS完全一致条件を必要機能中心へ改訂した。開始08:28:35Z、HEAD6182cce4e00ea63e866cab3ffe48f852770a2b36/origin一致・clean。先行元5helperのlive/execution creation/start_token一致・CIM同original不在/repo helper・critical ownerなしを確認。自走heartbeat banto-10はPAUSEDを維持する。

## 現在の条件と証跡

- windows-runtime-policy.1はWindows 11 x64 workstation（major/minor10.0、build>=22000、product_type1）、local NTFSを要求する。release/build/UBR/editionの実値を保持し、特定番号への完全一致は外す。registryとsys.getwindowsversionのbuild不一致は拒否する。
- GetVolumeInformationWのFILE_PERSISTENT_ACLS flagと必要Job/process/HANDLE継承・ACL/publication API exportを確認する。exportを照会するだけでCreateJob/Assign/Close/ACL変更/Move等の実動作を呼ばない。behavior_verified=falseで、実native受入/owner認証を発行しない。
- 元expected_snapshotをAPI/IO前にcanonical bytesへ固定し、同run内では実観測全体の変化を拒否。別runのOS更新は新実証跡を記録する。collectorも開始/終了host全観測を照合する。
- 通常GIL CPython3.14.0/build/tag/exe・DLL hash固定は維持。S4受入未完了のcampaign拒否・create_native早期拒否を維持する。
- 新inspection s4-a.4/v3 schemaはproduct_type/native_capabilitiesを閉じた形で記録し、matches-python-basic-pinはPythonの一致を表す。旧s4-a.2/v1・s4-a.3/v2 schema bytesと旧Windows完全一致条件は履歴読取り用に保持する。
- 登録registryのruntimeと科学9schema/config/seedは変更しない。旧OS値は当初の参照環境として保持し、現在の実行許可や実runで観測したOS値へ読み替えない。runtime.jsonは実観測を保存する。

FILE_PERSISTENT_ACLSの意味は[Microsoft GetVolumeInformationW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getvolumeinformationw)、Windows11の初期build22000は[Microsoft platform version documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/gettingstarted/platforms-and-driver-versions)で確認した。

## 今回の検証

新10case＋変更が影響する既存5case＝15distinct。初回0.8843393999850377秒で14pass/1error（入力生成のdict.updateに重複keyword、3subcase）、fail0/skip0。原helper/log6887B/a0aa70dce033c1f60834e14856214853ba40bf46cf716c54ea2d0fa83eb3e162とfailed記録を保存し、成功へ書換えない。

入力生成だけを修正して失敗1だけ一回0.46676530002150685秒pass。v2 log306B/daf3be19a653eccfc548a9591931050b4e11d67af106397bf20880034c8afdfe。reviewで旧TestCaseをglobalへimportする重複discoveryを避け、module参照へ修正した新1だけ1.9168795000296086秒pass。v3 log256B/31959cd73462cc248ce9772be5fb117e9bfba3b69a151949e753fb70141fad15。

16distinct/body17、先の14は反復0、別source/runで最終source単一16successではない。更新build/UBR/edition、unsupported host、volume/ACL/API欠落、version整合、snapshot差分、新旧schema/旧OS条件、collector forwardingとclosed campaignを確認した。

実WinDLL/winreg/API-return/volume flagsは明示fake、小temp FileIOと純粋schemaのengineering確認である。実Win ABI/native Job/DACL/child transport/全経路wall/容量合格ではない。full suite/旧CI raw/完成focus/native/業務worker/追加agent/profile再観測0。

変更11pathの安全検査は違反0。科学config5＋科学schema9＋旧inspection schema2の計16pathはworking/Git原bytes一致。先行Python314 rootは27file32705Bのまま。元prepare・初回failed focus・v2・v3・componentsの5helperはlive/executionのcreation/start_token full一致、read-only CIM同original不在/repo helperなしを確認した。初回failed状態は変更しない。正式native入口のsourceは変更しない。

原raw artifacts/windows-runtime-policy-20261009-prep/は512KiB32entry/reserve128KiB/single128KiB。失敗を含む元helper identity/live/execution/log/source metadataを保持し、code/docを一つの保存単位へまとめた。post-saveで実fullHEAD/origin/working-Git両pinと新revision CIの一度の観測を保存する。新CI終端は未確認、正式受入未完了/formal_permission=false/credit0/登録holdout観測未読、PAUSEDと元caps/stop/owner保持を維持する。
