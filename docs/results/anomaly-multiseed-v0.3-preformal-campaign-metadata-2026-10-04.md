# 架空campaignの凍結計画・journal構文境界（2026-10-04）

## 保存した実装

[架空専用metadata契約](../../src/banto_ai/anomaly_v03_preformal_campaign_metadata.py)を追加した。S1で凍結済みのholdout **identityだけ**を再構成し、480区間・2,880評価の順序付き計画を検査する。identity全体のcanonical SHA256は `8cbda70c8749bebb2bab92f3113870093027589bc73b5e4676cb74fbca39e921`、各区間６identity hashを並べたcanonical SHA256は `50308531170c26fb4ecf6782afee3f76d0f4c26c5805677d724a7b769b460448`。実観測の生成・読取りは行わない。凍結registryのraw pinは10,679 B / SHA256 `61af9100f8daa96d8200a0d2ab23aa7209cab52f0dd5543f9e35797de7332a70`に限定する。

計画はcampaign ID、別のmetadata root、短いpath code、架空recipe `hand-normal-v1`、登録seed非消費、選定sourceのraw pin集合、版付きruntime候補、未採択の予算候補をcanonical JSON+LFへ固定する。区間/attempt rootは`artifacts/`直下で４文字suffixを使う。例: `h001`は区間0・attempt1、`h011`は区間1・attempt1、`hdb1`は区間479・attempt1。現workspaceで既存生成子の最深相対出力を当てると４文字suffixの最長pathは244文字で、現probe上限245文字以下。ただし本純粋契約は実際のworkspace所属、path長、root不存在をI/Oで検査しない。

journal reducerは**外部に保持した計画raw pin、record count、head SHA256**を受け、canonical JSON+LFの追記recordを連鎖検査する。`started→completed/failed`、区間順、attempt番号、別root、同じanchor/manifest/source/runtime、22保存論理名のpin集合を検査する。`completed`宣言には初回生成子・readerに加え、別のfresh保存raw再読取りresult/監督/stdout/予算/６行pinを必須とし、行pinの一致を要求する。実g02 manifestの22論理名との一致も独立の固定値で確認した。途中失敗と再試行の履歴は残し、欠番・逆順・重複、別anchor、改変・切詰め、最新失敗からの次区間を拒否する。

この計画・journalは**呼出者の宣言を検査するだけ**である。raw保存file、外部pinset、元process handle、PID/start token/exit/reapは開かない。`completed`を480回宣言しても、`producer_campaign_anchor=null`、`campaign_coherence_authenticated=false`、`producer_execution_authenticated=false`、cluster/診断/slice sourceは`null`、`launch_authorized=false`、`resume_authorized=false`、正式credit 0を固定する。g02の既存pin値を新rootの宣言へ転記するだけでは由来を証明できず、g02を後付けで新campaignへ所属させない。

[焦点試験](../../tests/test_anomaly_v03_preformal_campaign_metadata.py)12件は、観測materializerを呼ばない計画生成、凍結順序、0・1区間の宣言だけでも未認証を保つこと、外部head/count、canonical LF、欠番/逆順/古いattempt/失敗後skip、必須証拠pinを確認した。repository safetyもPASSした。**今回、所有controllerや架空２区間のnative実走、新しい保存rawの再読取り、全工程予算測定は行っていない。**

## 次の受入境界

[次のcontroller契約案](../anomaly-v03-preformal-campaign-controller-next-v1.md)に従い、最初の`prepare`より前のanchor外部固定、起動前intentionの外部固定、CLIと内側子の所有・終了回収、22 fileと再読取り６行の実raw照合、head/countの別場所保管、失敗保全を実装する。現metadata schemaではmanifestがまだない`prepare`失敗を表せず、失敗recordの存在だけで子が回収済みか判定できない。どちらもnative再試行を許す前に解決する。inner子のinvocationにはまだanchor pin欄がないため、次の小試行でもechoを追加・検証するまで共通producer由来認証をtrueにしない。

これはS4の正式採択や、架空480区間完走を新たなS4必須条件にする記録ではない。26H2運用契約、５役source/runtime閉包、Linux両jobとrunner同定、Windows native、最終dev８・smoke２、容量２倍条件、50,000 drawを含む単一外側予算は残る。S4採択後にだけ未使用holdout40 seedをS5で一回実行し、S6で実結果の全件独立再監査を行う。旧gate `s4_acceptance_not_frozen`、実登録観測読取り０、正式評価credit０を維持する。
