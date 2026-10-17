# 架空２区間のnative限定技術試行（2026-10-04）

状態: **区間別の技術結果 / 共通campaign由来未認証 / S4未採択**。ユーザーの範囲変更により、共通anchor/journal・子孫異常時回収保証・可変coverage集約を小試行の開始条件から外した。これらは共通campaign由来、resume許可、集約coverageを主張する前の条件として残す。未使用の実登録holdoutは生成・読取りせず、`hand-normal-v1`の固定手作り系列だけを使用した。

## 実行範囲と保存pin

clean HEAD `7c9be9dc328480985dd6c6721af1db8071a93544`、Windows 11 Pro 26H2/build26300/UBR9457、CPython 3.14.0の新規rootで、区間0 (`c001`) と区間1 (`c011`) を**直列に** `prepare → run-budget → fresh保存raw再読取り`した。各`prepare`前に生成root・pinset・再読取りrootが不存在、pinsetと生成rootの４文字suffixが一致することを確認した。`prepare`のmanifest rawとSHA sidecarを再照合してから次CLIを起動した。失敗した場合は後続を起動しない手順とし、両区間のCLIはexit 0だった。

| 区間 | 起動前manifest pin | 生成２役result pin | fresh再読取りresult pin | ６行pin |
| --- | --- | --- | --- | --- |
| 0 `c001` | [72,150 B / `06249355…806042b`](../../artifacts/anomaly-v03-preformal-generated-pinsets-c001/pins.json) | [1,656 B / `6a21deb…e5d4cc`](../../artifacts/anomaly-v03-preformal-registered-attempt-c001/budgeted-result.json) | [8,453 B / `647ad28…612d42`](../../artifacts/anomaly-v03-preformal-saved-row-reread-c001/result.json) | [116,085 B / `ef21e7d…45d0e92`](../../artifacts/anomaly-v03-preformal-saved-row-reread-c001/rows.json) |
| 1 `c011` | [72,150 B / `3991638…862aea6`](../../artifacts/anomaly-v03-preformal-generated-pinsets-c011/pins.json) | [1,656 B / `e4f9ca8…8e49e8`](../../artifacts/anomaly-v03-preformal-registered-attempt-c011/budgeted-result.json) | [8,453 B / `9d4b0a0…1d42`](../../artifacts/anomaly-v03-preformal-saved-row-reread-c011/result.json) | [116,085 B / `f183197…71dcd`](../../artifacts/anomaly-v03-preformal-saved-row-reread-c011/rows.json) |

主要rawの完全SHA256は次のとおり。生成２役resultに結ぶ[区間0の所有生成result](../../artifacts/anomaly-v03-preformal-registered-attempt-c001/owned-generator/result.json)は10,528 B / `6ad3ad604d4737af6ec100aec6dd11c5952e8d45b6d7b6175d5347865521f06e`、[区間1](../../artifacts/anomaly-v03-preformal-registered-attempt-c011/owned-generator/result.json)は10,528 B / `e2c6fe1876c0626653fb9da0a6a14fe6554833404a7a6fb965bbfb743db71afe`。再読取りCLIの`--outer-result-pin`にはこのpinを渡し、`budgeted-result.json`のpinは渡していない。

```text
c001 manifest        06249355b995d65f40a03039e643b577e6604c12daf233d02ab492716806042b
c001 budgeted-result 6a21deb21733bbbe5710092dbf12f41e53b4ed082af1bb1c811af32920e5d4cc
c001 generated-budget a1f430a74310f7e44336dd70d92e22a422bad422c982f0d35bc892e0ecb097c0
c001 fresh-result    647ad2886661ca872eae67874b4f2d709a2a64fe879b50af795f703fe4612d42
c001 rows            ef21e7dbe49dccb4c386d0e44d557243ea14788ff9e39491ebd9c308c45d0e92
c001 fresh-budget    69e2cb58c2ac3ee32d8994cd40b12e1dc611787d0ce0cc56def69c86b55a7068
c011 manifest        3991638e567f40f0d0de6917e26eb6fc1f92c27e40aeb5d3644346244862aea6
c011 budgeted-result e4f9ca84eccad7e368c2b4951c57ea131abe14feae5a5edf8f220ce2918e49e8
c011 generated-budget 3fd6c3929d360e9c94b86f1fbfdfb70c92be8e71ea36fdc7250f05d16b12a545
c011 fresh-result    9d4b0a0915693e69ef28504f9ee0d741fb1be35630043b68ecf9ab559c21080c
c011 rows            f183197f9be8f599329cd5e1cf72beb398ee7dc99d92b641c87a9fb6f4471dcd
c011 fresh-budget    9984103a149ecab8975b013785d2f3743e5f655b347a0d5fe3a7e8c75cb185a1
```

各manifestは22保存出力を先行固定した。区間0は131,144,120 B、区間1は131,144,440 Bの保存payloadを生成し、別のreaderで再読取りした。既存の厳格なraw照合入口で各区間22出力・生成側13証拠pin・fresh側６証拠pinを再確認した。さらに標準Pythonの`hashlib`/`json`による別のread-only照合で、両区間ともmanifest sidecar、各22保存rawのbytes/SHA、結果/予算・３つのsupervisionの参照pinに差異０を確認した。各`rows.json`の実配列は６行で、区間0は登録seed index0/layout0、区間1は同seed index0/layout1、どちらも最新attempt 1である。これは**６＋６件の区間別確認**であり、同一campaign由来の12/2,880集約coverageを認証しない。

## 区間別予算と限界

| 区間 | 生成→初回readerの共有予算 | fresh再読取り予算 |
| --- | --- | --- |
| 0 | [190.103秒 / 737標本 / PASS](../../artifacts/anomaly-v03-preformal-registered-attempt-c001/resource-budget.json) | [42.036秒 / 169標本 / PASS](../../artifacts/anomaly-v03-preformal-saved-row-reread-c001/resource-budget.json) |
| 1 | [195.158秒 / 756標本 / PASS](../../artifacts/anomaly-v03-preformal-registered-attempt-c011/resource-budget.json) | [42.821秒 / 172標本 / PASS](../../artifacts/anomaly-v03-preformal-saved-row-reread-c011/resource-budget.json) |

`prepare`の計算時間・別rootのpinsetは生成２役予算外である。fresh再読取り予算は外部に保存済みの約131 MB/区間を入力として読み、その入力容量を新しい再読取りrootの32 MiB制限に含めない。４予算は別々の測定であり、時間を足して単一全工程予算passとはしない。今回の起動は既存CLIを直接実行したもので、[未接続のcontroller API](anomaly-multiseed-v0.3-preformal-two-slot-owner-boundary-2026-10-04.md)が外側CLIを所有して保存したcampaign receiptではない。異常終了時の全子孫停止・回収も検証していない。

両区間の保存結果は`invented_only=true`、`registered_seed_consumed=false`、`actual_registered_observations_read=false`、`formal_permission=false`、`campaign_evaluations_credited=0`を維持する。共通campaign anchor、外部に時点固定したjournal/head/count、可変coverage集約、40 cluster/診断/slice source、50,000 draw以降の単一全工程予算、完全独立S6は未成立。26H2運用契約・公開保証A/B、５役source/runtime閉包、Linux両jobとrunner同定、最終dev８・smoke２等のS4残件は変更しない。旧gate `s4_acceptance_not_frozen`を維持し、実登録holdoutのS5はS4採択後に限る。
