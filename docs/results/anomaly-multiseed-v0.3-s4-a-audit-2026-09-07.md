# anomaly multi-seed v0.3 S4-A engineering inspection audit

状態: **audit-result / S4-A ready / acceptance not completed / no formal permission**
日付: 2026-09-07
対象main: `e61d14c4b31ed3c4711157e4a94446513e390422`
親commit: `8befc5bb6cf1c7c424b6024c90b94fb149a9e4f9`

## 結論

S4-Aのengineering inspection/resource guardを、実装commit `8befc5bb`と監査修正commit
`e61d14c4`の2段階で本流へ統合した。初回独立監査はP2=1、P3=1だった。P2は、receiptの
`python.executable`とloaded native inventoryに含まれる実行Python imageの一意な参照、raw SHA-256、
byte countのpure validator内照合が不足していた点である。P3は、CLIの`argparse`失敗時に未知optionや
入力値がstderrへ反射される点である。

`e61d14c4`でstable receiptに`executable_native_path`を追加し、schema、builder、collector、pure
validator、Linux/Windows fixtureを同期した。validatorはsafe native path、一意な存在、実行Python
imageとdescriptorのSHA/byte count一致を要求する。CLIは安全な`ArgumentParser.error`、parse処理の境界化、
strict full revision、abbreviation禁止を追加し、invalid/missing/unknown argumentと任意例外を固定JSONへ
redactする。

再監査は **P0=0 / P1=0 / P2=0 / P3=0**。`PREVIOUS_P2/P3_RESOLVED=yes`、
`S4_A_READY=yes`、`INTEGRATION_READY=yes`と判定する。ただしこれは本番試験の開始や受入完了ではない。
receiptの`acceptance_status`は常に`not_completed`、`S4_ACCEPTED=no`、`FORMAL_PERMISSION=no`である。

平易に言えば、これは本番試験前の車検機能が完成した状態であり、正式試験はまだ開始していない。

## 検証記録

| 範囲 | 結果 | 実測 |
| --- | --- | --- |
| S4-A acceptance targeted | pass | 27/27、1.221秒 |
| S4-A統合後独立再実行 | pass | 27/27、1.441秒 |
| D2 compatibility/fixed-pin regressions | pass | 6/6、34.077秒 |
| S3 specialized regression | pass | 73/73、438.462秒 |
| Python in-memory compile | pass | 116 files |
| repository safety / diff-check | pass | pass |
| 修正候補のfull local suite | 未実施 | 旧候補714件の結果は転用しない |
| CI | pass | [run 34057314195](https://github.com/tyaro/banto-ai/actions/runs/34057314195) |

CIはmain `e61d14c4`上でPython 3.12が15m10s、Python 3.14が15m43sだった。compile、unittest、
manifest/smoke、synthetic data、benchmark、repository safetyは全て成功した。

## 境界と未完了事項

- Windows exact runtime基本pinは一致する。ただし現checkoutの`.github/workflows/ci.yml`はworking treeがCRLF、Git blobがLFで、raw bytesが一致しない。collectorはこれを正しくfail-closedした。byte-identical管理checkoutでS4前に再確認する必要がある。
- artifact棚卸しは617 entries / 461 files / 36,352,494 bytesで、before/after差は0だった。想定外residueはない。
- formal v0.3の5 rootは前後とも未作成である。
- 科学5 config、9 schema、historical 88、D2 current-only 31は保全した。
- MemoryErrorはglobal stop、future slotの`not_started`、stop後IO禁止へ強化したが、実OOM根因やcommit limitの解明は主張しない。
- S4-Bのtemp-only native publisher/DACL/restricted-token/race harness、S4全体、dev 8、smoke 2、formal acceptance、S5 holdoutは未実施である。

## 次のsavepoint

次はS4-Bとして、temporary領域だけを対象にnative publisher、protected DACL、restricted token、
競合race harnessを検証する。S4-Aのinspection receiptだけではnative acceptance、consumer freeze、
runtime closure、image identity、campaign permissionを発行しない。正式dev/smoke/holdoutのoutput rootは
S4全体の受入が完了するまで閉鎖する。
