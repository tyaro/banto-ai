# 架空２区間のpreflight・所有境界（2026-10-04）

状態: **実装済みの限定境界 / 保存当時はnative区間未実行 / S4未採択**。その後、ユーザーの範囲変更を受けて[区間別の架空native小試行](anomaly-multiseed-v0.3-preformal-two-slot-native-smoke-2026-10-04.md)を実行した。対象は登録形式を使う固定手作り系列の区間0・1だけ。凍結holdoutのidentityは計画slotの照合に用いるが、登録seedを消費せず、実登録観測を生成・読取りしない。

## 保存した境界

[prepare preflight](../../src/banto_ai/anomaly_v03_preformal_campaign_preflight.py)は、外部pin付きの架空campaign計画から区間・attempt root、対応するpinsetとSHA sidecar、Python/cwd/正確な`prepare` argvを導出する。manifest生成前の失敗も、manifest pinを要求せずにoutcomeとして記録できる。成功宣言ではmanifest rawとsidecar raw、22出力の論理名・サイズ上限・凍結registry pin、２つのsource snapshotとpin、選定sourceを検査する。実CLIのsource一覧順序は計画側へ正規化して比較する。[生成CLI](../../tools/preformal_owned_generated_trial.py)にもattempt rootとpinset directoryのsuffix完全一致を要求した。

[２区間controller](../../src/banto_ai/anomaly_v03_preformal_campaign_controller.py)は、外部pin付き計画とjournalの現在head/count、最新`started` record、保存manifestから、`run-budget`または新規保存raw再読取りの１CLI用requestを固定する。所有した直下CLIのPID/start token・終了code・supervisionを保存し、内側生成子/readerのreply親PIDと監督結果、22保存raw pin、fresh再読取り６行・予算/結果pinを照合してから完了record候補を返す。次の区間1は前区間0の完了recordを２つの所有receiptから再構成して一致させる。requestを検証して所有contextを確定した後の異常終了は、別の失敗receiptと失敗record候補を保全し、自動再試行・次区間を拒否する。欠損・改変された起動前requestなど、所有context確定前の拒否はreceiptを作らず停止する。

これらの関数は**callerが保存するrawを構築・照合するAPI**であり、計画anchor、起動前intention、journal record、外部head/countの永続書込みを一つの所有transactionとして実装していない。`prepare` preflightとcontrollerの開始recordもまだ接続していない。preflightのprocess pin・実行前時点は宣言で、所有handleによる事実認証ではない。controllerが所有できるのは直下CLIであり、異常終了時の内側子孫回収保証はない。よってこの実装だけで共通campaign由来、resume許可、２区間完了を主張しない。

## 検証と残る作業

焦点試験は計画/journal、preflight、controller、生成CLIのpinset pathを含む34件がPASS。repository safetyと差分形式もPASS。保存済み架空g02/r01をread-onlyで照合し、生成13証拠pin・22保存出力pin・fresh再読取り６証拠pinを確認した。生成側invocation pinの置換を模した照合も拒否した。新規の架空区間native実走、新区間の保存payload再読取り、新しいcoverage集約は行っていない。既存g02/r01の１区間を今回のcampaignへ後付けしない。

共通campaign由来や再開許可を**主張する前に**、同じownerが外部anchor・preflight intention/outcome・各CLI intention・journal/head/countを起動前に排他的かつ持続的に固定し、失敗時の不完全出力・未回収子孫を保全して後続を止める必要がある。保存行coverage CLIは現状g02/r01の１区間に固定されており、新２区間に対するpin付き可変入口と独立postcheckも必要。区間別の技術試行は、新規root・一致するpinset・clean revision・内蔵予算・区間ごとの終了/保存raw確認と、失敗時の後続停止を条件に先行できる。その成功を12/2,880の集約coverageや単一全工程予算passへ昇格させない。

26H2運用契約と公開保証A/B、５役source/runtime閉包、Linux両jobとrunner同定、Windows native受入、最終dev８・smoke２、容量２倍、50,000 drawを含む単一外側予算は残る。架空480区間完走を自動的にS4必須条件へ加えない。S4採択前の未使用実holdout40 seedは閉鎖を維持し、実S5/S6・正式creditは０。旧gate `s4_acceptance_not_frozen`、`formal_permission=false`を維持する。
