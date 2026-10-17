# v0.3 5役Job前の選定source所有Git 7呼び出し v2入口

2026-10-05。状態: **採択前のpreformal実装とテスト**。この記録は最終clean revisionの実機受入や正式評価の証拠ではない。登録holdout観測は読まず、`formal_permission=false`、`source_closure_complete=false`、`runtime_closure_complete=false`、`execution_authenticated=false`、正式credit 0、gate `s4_acceptance_not_frozen` を維持する。

新しい opt-in [v2 wrapper](../../src/banto_ai/anomaly_v03_preformal_five_role_owned_source_anchor_v2.py)と[CLI](../../tools/preformal_five_role_owned_source_anchor_v2.py)は、外部pin付き所有Git policyから非上書きのphase rootを作り、既存の `owner._source(revision, git_reader=...)` を1回実行する。保存manifestには `HEAD`、clean `status`、5件の選定source blobという**正確な7呼び出し**の順序・直接receipt pinを要求する。7件が保存再照合を通った場合だけ、変更のないv1の5役Job ownerへ進む。外側receiptはpolicy pin、manifest pin、7件のsource pin、v1 owner receipt pinとstatusを結ぶ。Git preflightまたはJobが失敗した場合も、外側receiptは `failed` とし、取得できたmanifest/owner pinを保持する。未回収process/Jobの例外は同じhandleを再送出する。

この所有Gitの範囲は **Job前の7呼び出しのみ**。v1 owner自身のparent preflight、監督前後、子pre/post、内側chain pre/post、four-role/producer、保存verifierのbare Gitを所有したとは扱わない。`inner_v1_git_owned=false` と `integration_pending=true` をreceiptに固定した。完全な5役source/runtime閉包、Gitのloaded code/子孫process、登録readerを含む共通campaign入力、全工程単一予算は残る。保存verifierも成功したv1 ownerの検査でread-only bare Gitを再起動する。

実施した焦点確認は、新規[test](../../tests/test_anomaly_v03_preformal_five_role_owned_source_anchor_v2.py)10件（実Gitの7件順序、dirty status、誤blob、偽PATH、owner失敗、外側と内側の候補path不一致、owner verifierの範囲逸脱、未回収Git、保存物改変、root再利用）、既存owned Git/anchor関連18件、3新規ファイルのcompileall、CLI `--help`、repository safetyで、いずれもpass。テストの内側ownerは偽物であり、v2入口からのWindows native 5役Job実走・外部raw pin・独立再監査は未実施。実走時はclean full HEADと外部policyを固定して新rootを使い、失敗・成功のreceiptを別実装で再照合する必要がある。

後続のclean `a5deb31` Windows実機小試行と独立raw照合は[別の結果記録](anomaly-multiseed-v0.3-five-role-owned-source-native-trial-2026-10-05.md)に固定した。上の段落は実装直後のテスト範囲を記した履歴であり、試走をその時点の試験結果へ遡って加算しない。
