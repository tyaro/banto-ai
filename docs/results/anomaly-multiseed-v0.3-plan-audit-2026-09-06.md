# event-aware anomaly multi-seed evaluation v0.3 計画監査結果

- 監査日: 2026-09-06
- 監査対象: `4b02201f95e8ffa3a243be716872d95815a554bd`
- 監査対象のparent: `e92c83df03b2f798d60246e14411d249a0b76202`
- main基準: `026aa77fe96afd954957acb2fc7d0df9ee3cc938`
- S0初稿: `41decf9b6f8d6c876715729516354bf6da49422c`
- 対象文書: [v0.3実装前preregistration](../anomaly-multiseed-evaluation-plan-v0.3.md)

## 結論

監査対象`4b02201f95e8ffa3a243be716872d95815a554bd`を独立にread-only監査し、指摘は
`P0=0`、`P1=0`、`P2=0`、`P3=0`だった。S0計画は採択・凍結可能であり、判定は
`SCIENCE_READY=yes`、`FREEZE_READY=yes`、`DOCS_READY=yes`、
`IMPLEMENTATION_READY=yes`、`STACK_READY=yes`である。

この判定は、v0.3の実装前科学計画が再現可能な仕様として整ったことだけを示す。
Linux／Windows native acceptance、S1〜S7、config/schema/code/test/CIの実装、formal run、
性能評価、候補選択、promotionは未実施で、今回の監査対象外である。mainへの統合も未実施である。

## 指摘件数とreadiness

| 判定 | 結果 |
| --- | ---: |
| P0 | 0 |
| P1 | 0 |
| P2 | 0 |
| P3 | 0 |
| SCIENCE_READY | yes |
| FREEZE_READY | yes |
| DOCS_READY | yes |
| IMPLEMENTATION_READY | yes |
| STACK_READY | yes |

## P2修正の解消根拠

### P2-1: incident matching

計画は`first-equipment-onset-no-retry-v1`として、候補をequipment onsetとepisode IDで完全に
列挙・整列し、最初の候補をclaimした後にだけtarget sourceと因果的supportを検証する。
最初の候補がsupport不適格でも後続episode／sourceへ再探索せずmissにし、入力構造違反は
metric上のmissへ埋めずengineering failureにする。M1〜M9の手計算fixtureは、pre-event support、
窓外episode、別source先行、merge後onset、half-open右端、mode-entry、閾値等号、偽造supportを含み、
列挙、選択、claim、support判定、miss／failureの各境界を再検証できる。

### P2-2: observation quantization

normal stateは未丸めbinary64のまま次sampleへ渡し、machine、sensor、ignored、quality overlayを
適用した後、保存直前に有限な5信号へPython組込み`round(float(value), 6)`を1回だけ適用する。
nullは保持し、ties-to-evenとsigned zeroを含む保存済みcanonical JSONLだけを
fit／calibration／test／auditが読む。Q1〜Q5はoverlay前丸めとの差、latent state、dropout、
binary64 tie、`-0.0` tokenを固定し、順序違反や未丸め内部配列の利用を検出できる。

### P2-3: runtime/platform acceptance

計画はUbuntu 24.04 x86_64上のCPython 3.12／3.14共通試験と、Windows nativeの実publisher、
protected DACL、別process／tokenでのAccessCheckを分離した。formal runtimeはWindows 11 Pro 25H2
AMD64、OS build `10.0.26200.9168`、local NTFS、通常GILのCPython `3.14.0`
（source tag `v3.14.0:ebf955d`）に一意固定され、非対応環境は生成・staging・claim・ACL操作前に
`unsupported_runtime`で拒否する。Linuxは互換性検証、Windows 3.12はpublisher互換性試験に限り、
formal fallbackにはしない。

監査時のread-only実機照合では、OS build `10.0.26200.9168`、AMD64、C:のNTFS、
CPython `3.14.0`、`Py_GIL_DISABLED=0`を確認した。実体hashは次の計画値と一致した。

| 実体 | SHA-256 |
| --- | --- |
| `C:\Python314\python.exe` | `467014615a5255aca450ae88100dd2caf887da87657f00e3c2171ec44a685aec` |
| `C:\Python314\python314.dll` | `f1722bd369d79fecbc85f3ed2790c30c330b9413fd74332f95b086e60dfacc2a` |

この照合はformal Windows native acceptanceの実施を意味しない。実publisher、DACL、AccessCheck、
Linux 3.12／3.14およびWindows 3.12／3.14の受入はS1〜S4で別途実施する。

## 固定値の再検証

seed生成手続きからdev 8、smoke 2、holdout 40の全50新seedを再計算し、旧10 seedとの非重複、
retry 0、canonical seed-list SHA-256
`fa072f5299132fc22cce471c94ca189ddfc0f3acd27c2c5201bc31a2a9287505`を確認した。
計画母数は960 datasets、2,880 evaluations、19,200 positives、41,472,000 score rowsで
相互に整合する。M1〜M9とQ1〜Q5も手計算期待値に照らして反例境界を再確認した。

## 監査境界

監査は計画文書、参照実装、commit差分、固定値、リンク、表、repository安全境界をread-onlyで
検査した。dataset、score、run、result artifact、ACL fixtureは生成・変更していない。
顧客データ、外部通信、PLC／control write、Banto Hub write、外部model weightsは使用していない。

この結果文書は監査対象科学仕様の改訂ではない。監査対象`4b02201...`をS0の科学仕様revisionとして
採択し、後続のstatus/result同期commitはprovenanceとしてS1 registryへ併記する。
現在状態の入口は[文書索引](../README.md)と[研究roadmap](../research-roadmap.md)を参照する。
