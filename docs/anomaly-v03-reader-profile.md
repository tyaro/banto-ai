# readerの事前保持候補profile

2026-09-25、実装 `0b2da336d90bcc60e97798d83d17d9f6f7421a34`。[結果](results/anomaly-multiseed-v0.3-reader-dependency-profile-2026-09-25.md)、[実観測reader](anomaly-v03-reader-evidence.md)、[source/runtime計画](anomaly-v03-consumer-source-runtime-plan.md)。通常権限・単一writer終了後のengineering候補。正式freeze/受入ではない。

## 作成と照合を別に行う

まず`observe_dependencies=True`の読取を完了させ、そのAPIが返したresult pinを別に保持する。次に`prepare_profile`で新しい候補fileを作り、そのpathとpinを後続readerへ明示する。後続reader自身の結果から期待値を再作成しない。profileの自動更新はしない。

```python
from banto_ai.anomaly_v03_reader_profile import prepare_profile
from banto_ai.anomaly_v03_reader_evidence import check_with_evidence

candidate = prepare_profile(
    completed_reference_directory,
    expected_result_pin=retained_reference_result_pin,
    expected_revision=full_candidate_commit,
    profile_parent=existing_separate_parent,
    profile_name="reader-candidate.json",
)
# candidate["profile_pin"]を保持してから、別の読取を起動する。
checked = check_with_evidence(
    retained_reader_request,
    expected_revision=full_candidate_commit,
    receipt_parent=existing_separate_parent,
    receipt_name="new-profiled-reader",
    observe_dependencies=True,
    dependency_profile=candidate["profile_path"],
    expected_dependency_profile_pin=candidate["profile_pin"],
)
```

作成元は、依存観測付き・未profile化・終了確認済みの成功したreader。外部result pinからevidence/binding/dependencies/stdoutを照合する。前後source/runtime/依存一覧は完全一致が必要。現在のGit/raw source、runtime、disk内容/identityにも比較する。profileは新規fileに排他的保存し、元reference・公開物・入力・sourceと重なる保存先を拒否する。

## 固定する範囲

format、engineering-dev-smoke mode、reader role、candidate-not-accepted状態、full source revision、checkout絶対root、起動runtime、依存snapshot、作成元pin、採取境界を保持する。採取境界はrequestの解読とcollector importの後、公開結果の検査前。既存cache候補は実使用したbytecodeとは区別する。

親は起動前に外部pinとprofileの役割・revision/root・runtime・依存fileを検査し、profile bytesをメモリに保持する。実行directoryへ保存したcopyは16番目の入力として入出力証拠にも結合する。子も保持profileへ前後の全一覧を比較し、余分なmodule/fileも拒否する。親は終了後、メモリに保持したprofileへ再比較し、元候補と保存copyの差し替えも拒否する。

成功時は既存のevidence/bindingに加え、dependency-profile.jsonとdependency-profile-binding.jsonを保存する。resultには候補pinと結合記録のpinを加える。新しい候補無しの既定APIは従来どおり。

## 制限と更新

候補上限512KiB。子の30秒/512MiB/output1MiB、依存採取512file/1file64MiB/合計256MiBを維持。親のGit/preflight全体の正式総予算ではない。

候補は同じcheckoutのpath/file identityにも結ぶため、別のcheckoutへの移動やOS/runtime/file更新では不一致になる。Windows更新は許容したengineering状態変更として記録し、必要なら別referenceと新規候補を作成する。旧候補を黙って更新せず、OS設定や旧formal OS pinを変更しない。

今回のprofileは**別に完了した観測を出発点とする候補**。後続実行から独立して保持しているが、信頼された完全な依存定義や正式な受入承認ではない。disk bytes/cache候補はmemory内codeや実使用bytecode、未実行branch、一時load/unload、Git helperの完全性を証明しない。profile作成process自身の完全な実行観測、analysis/auditのrole接続も残る。formal/promotion/S6/trust/execution_authenticated/full closure=false。
