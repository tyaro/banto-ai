# v0.3 S4 運用改訂案: 26H2・単一writer保証 A

2026-10-04。状態: **review draft / 未採択**。この案は[凍結計画 §8–9](anomaly-multiseed-evaluation-plan-v0.3.md#v03-runtime-acceptance)の科学仕様、S1 registry、旧formal入口を変更しない。採択対象の差分と不足証拠を、[運用契約案 v2](anomaly-v03-formal-operations-contract-proposal-v2.md)からレビューできる形に固定する。S4受入・正式実行許可はまだない。

## 採択候補の差分

| 項目 | 凍結計画の現行条件 | この案の採択候補 | 採択までの扱い |
| --- | --- | --- | --- |
| 正式Windows runtime | Windows 11 Pro 25H2、`10.0.26200.9168`、local NTFS、AMD64、通常GIL CPython 3.14.0 | Windows 11 Pro 26H2、`10.0.26300.9457`。Pythonのversion/compiler/source tagとexe/DLL raw SHAは[v2案](anomaly-v03-formal-operations-contract-proposal-v2.md)のexact値。各役割の開始・終了、公開前に再照合 | 旧pinは旧版の履歴として保持。現runtimeを旧正式入口で許可しない。UBRの範囲指定・自動追認はしない |
| 公開保証 | protected DACL、独立read-only tokenでのwrite/delete等のAccessCheck、競合試験 | **保証 A**: 専用新rootの単一writerを所有し、終了・回収後に別readerを起動。公開前後の全payload、marker、receiptをfresh readし、非上書き・失敗保全を照合 | DACLによる別主体の書換え防止は保証しない。旧native試験をpassに読み替えない |
| 成功条件 | 完了markerと独立検証を含む | markerだけでは成功にしない。外側のverified receipt、writer/reader両者のexit・reap、保存rawのfresh readと意味照合がそろった場合のみ成功 | 親postflight失敗でmarkerが残る場合もfailedとして保全 |
| 版・root | 旧registry、旧formal root、旧schema | 正式ID候補 `anomaly-v03-single-writer-research-v2`、新しい版付きwrapperと専用root。attemptごとにclean full revision・source/runtime pin・失敗と再登録規則を固定 | 旧artifactや旧rootを移動・上書き・再利用しない。新入口はS4独立受入まで閉鎖 |
| Linux CI同定 | Ubuntu 24.04 x86_64 / Python 3.12・3.14、runner image digest等 | 両jobと共有fixture比較を最終revisionで実行。digestが取得不能なら、image version・run log・release manifest等の**代替同定**を別に定義し、計画に版付きで明記 | `runner_image_digest=null`を取得済みと表現しない。代替の妥当性も独立監査対象 |

科学条件の40登録seed、480区間、2,880評価、50,000 bootstrap draw、分母・gate・選択規則は変更しない。S5の実登録観測はS4採択後だけに扱う。S4用の架空入力試験に480区間の全完走を追加の必須条件とはしない。

## 保証 A の受入項目と現在の証拠

| ID | 最終revisionで必要な結果 | 現在の限定証拠・残件 |
| --- | --- | --- |
| A1 | 26H2 exact tuple、Python raw bytes、local NTFSと専用新rootを実機で照合。途中変化は公開成功前に停止 | [platform-v2 fixture](anomaly-v03-formal-operations-contract-proposal-v2.md)の純粋契約試験はpass。全役割runtime閉包と最終revisionでの再実行は未了 |
| A2 | writerの実process handle、PID/start token、exit/reapを保持し、その後に別readerを起動 | 2026-10-04 17:23–17:25 JST、`9aab9e01f06f2ac5750993a360c42a8e54394560` のnative試験がpass。下記の成功receipt参照。正式5役割には未接続 |
| A3 | 同一attempt/rootの再利用を拒否し、保存全payload・marker・receiptのraw/意味を別readerで再照合 | 同じnative試験でpass。登録2,880枠と正式全文書の固定経路は未受入 |
| A4 | writer監督証拠3種類・公開payloadの改変を失敗として保全。markerが残ってもverifiedにしない | 下記4失敗receiptで確認。別主体による並行改変の防止は対象保証外 |
| A5 | producer→登録保存reader→40架空cluster/50,000 draw→完全S6同形audit→writer→別readerを単一外側予算で停止・回収 | 工程別の試行はあるが、単一外側予算、子孫停止、容量2倍の実測は未了 |
| A6 | 最終clean revisionでLinux両job、Windows native、正式dev 8 seed・smoke 2 seed、独立監査を一つの受入記録へ結ぶ | 最終revision・runner同定・最終回帰・独立受入は未了 |

今回のnative実行は `BANTO_PLATFORM_FIXTURE_NATIVE=1` による `tests.test_anomaly_v03_platform_fixture.NativePlatformFixtureTests` の3/3 pass（51.637秒）。通常の関連4 test moduleは26件中23 pass、native明示起動待ち3 skip（8.900秒）。両実行は現在のbranchの上記clean revisionで行った。`artifacts/` はGit管理外なので、次のraw pinはこの作業場所の保存証拠に限定される。

| native attempt / `platform-result.json` | bytes | SHA-256 | 期待された結果 |
| --- | ---: | --- | --- |
| [native-6346241d2a87ada9](../artifacts/anomaly-v03-engineering-platform-v2/native-6346241d2a87ada9/platform-result.json) | 1,916 | `ebda6ced54d5bd27ac6bd6afe8cc8bbb6417c64fd182bad82978b2028bab6440` | verified。writer回収後の別reader、非上書き |
| [native-0d274d8530aca52d-supervision-json](../artifacts/anomaly-v03-engineering-platform-v2/native-0d274d8530aca52d-supervision-json/platform-result.json) | 1,538 | `2220eec8c8a050437ae2799223433b37f4a2e688e17ead7f731ec1334800113d` | failed。writer監督証拠の改変 |
| [native-0d274d8530aca52d-worker-report-json](../artifacts/anomaly-v03-engineering-platform-v2/native-0d274d8530aca52d-worker-report-json/platform-result.json) | 1,540 | `a4991f16654aa0829bd6f2c7f61cedce5a2fdd496070e0ca181f31707c9b2b8c` | failed。writer stdoutの改変 |
| [native-0d274d8530aca52d-dependencies-json](../artifacts/anomaly-v03-engineering-platform-v2/native-0d274d8530aca52d-dependencies-json/platform-result.json) | 1,539 | `0757344e914ed06f9db53c6421c67af1eddb458648e4f27a6b52e9015f7000b5` | failed。依存証拠の改変 |
| [native-08a80951f67fc470](../artifacts/anomaly-v03-engineering-platform-v2/native-08a80951f67fc470/platform-result.json) | 1,525 | `5a68c93e5d77aa92d5c543191e37a87e85d6fe6cd84d80818792d175d89b925c` | failed。公開payloadの改変をreaderが拒否 |

この試験のscopeは未採択の26H2 platform fixtureであり、登録実観測・全source/runtime閉包・正式同形の全工程予算・S4採択を示さない。上表の失敗rootは残し、成功rootと合算しない。

## 採択前に閉じる事項

1. 本案の保証 A と旧§8との差を版付き計画・運用契約・正式wrapperに反映し、最終clean revisionを指定する。案 B のDACL/独立token試験を実施済みと表示しない。
2. 登録形式の架空固定入力から全予定identity、保存raw、最新attempt、profile/score/ledger、全slice/sidecar、40 cluster/50,000 draw、完全S6同形audit、全文書・公開までの由来を固定する。実登録holdoutの成功receiptはS4の前提にしない。
3. producer、analysis、audit、writer、readerの各起動前/中/後の全source/runtimeと動的依存、外部program、子孫停止・回収を独立に照合する。現campaignのselected source pinや親の子申告を全閉包へ昇格しない。
4. A1–A6を最終revisionで再実行し、Linux runnerの同定方式、Windowsのexact tuple、容量2倍・全工程予算、最終dev/smoke、独立監査を同じ受入記録へ結ぶ。

これらがそろい独立判定を受けるまで、`S4_ACCEPTED=no`、`formal_permission=false`、`resume_authorized=false`、正式credit 0、旧gate `s4_acceptance_not_frozen`を維持する。
