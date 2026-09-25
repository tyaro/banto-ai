# 実際の別process readerと証拠validatorの接続

2026-09-25、実装 `0ee336e72ca52849e6725415a3d7f8e4ff75aeeb`。[検証結果](results/anomaly-multiseed-v0.3-reader-observed-evidence-2026-09-25.md)、[純粋validator](anomaly-v03-consumer-evidence.md)、[通常reader](anomaly-v03-consumer-reader.md)。通常権限・writer終了後の追加API。既存check_in_subprocessの既定動作は変更しない。

```python
from banto_ai.anomaly_v03_reader_evidence import check_with_evidence

checked = check_with_evidence(
    retained_reader_request,
    expected_revision=full_current_commit,
    receipt_parent=existing_parent,
    receipt_name="new-observed-check",
)
```

requestは既存readerの10欄（format、engineering-dev-smoke mode、公開root、外部marker SHA256、binding/report保存点と各pin、analysis input）。formalをpath/Git操作前に拒否。結果の書込み先は元publicationやinput/sourceと重ならない新directoryだけ。同じ確認directoryを再利用しない。

## 外側が保持する期待値

親は指定した現在のfull Git revisionから固定10sourceを取得し、working raw bytesと照合する。全tracked cleanの受入ではなく、他の既存文書変更は保全する。10sourceの一覧はSOURCE_FILES。全project依存closureではない。

GitはPATHで一度選んだ絶対実行pathを固定し、実際のhardlink数とbytes/SHA256を記録する。呼出しの前後で変化を拒否。今回のGit実体はhardlink2で、sourceのsingle-link条件を外部programへ一律適用しない。Git helper/DLLの閉包は未確認。

親は外部anchorで公開結果と元入力を検査し、子に期待するreportを独立に準備する。元入力7file、公開payload4file、marker2file、reader request、invocationの計15入力のraw bytes/pinを保持する。payloadの数値計算は行わない。1file16MiB/合計32MiBの接続用読取上限があり、既存の評価実行予算は変更しない。

親のruntime値は子の観測として代用しない。親で読んだhost/Python/CPUの実値と、明示した-I -S -B/search path方針を起動前の期待profileにする。子は後述の実観測を別途生成する。

supervisorの追加on_started hookはPopenが返した元のhandleからGetProcessId/GetProcessTimesを読む。PIDと生成FILETIMEのhashをstart_tokenにし、親PID/command/cwdとともに保持する。expectationと生成記録はメモリに保持した値を基準にし、終了後に保存expected.json/launch.jsonの変化も拒否。ファイルから期待値を再採用しない。

## 子の実観測と照合

子は自分のhandleから生成時刻を読み、os.getpid/getppid、sys.orig_argv、cwd、sys.flags/sys.path、site/hook状態、実OS build/UBR、CPU名、Python executableと**実際にloadしたPython DLLのpath**を記録する。Python2fileとselected sourceのraw hashを、既存verify_saved_publicationの前後で採取する。入力にも前後一致検査を行う。

子が出したcompletion値だけで終了扱いにはしない。親の監視がexit0・終了確定・観測errorなしを確認してからstdoutを外部pinで読む。子の生成時刻/token/PIDを元handleの観測と照合し、report bytesを親の期待reportと比較する。stdoutに結合されたevidenceを純粋validatorへ渡す際も、role/process/source/runtime/入出力の期待値は親の保持値を使う。

監視は既存30秒/private512MiB/stdout+stderr64KiB。これは子の監視枠で、親のGit/source preflight全体の正式予算ではない。Git各呼出しは10秒timeout、源泉と入力のサイズは上限検査する。新CLIや自動実行は追加していない。

## 保存と失敗

確認directoryにはsource-tool.json、reader-request.json、invocation.json、launch.json、expected.json、supervision.json、workerのstdout/stderrを保存する。成功時のみreader-report.json、evidence.json、binding.jsonを追加し、result.jsonのstatus=verifiedとする。不一致時はfailedで、元公開物へ書き込まない。

UnreapedWorkerは元ownerをそのまま再送出し、保存記録の書込み失敗があってもownerを失わない。呼出し側は既存retain_until_exit等で終了を回収する。確認できていないworkerのログは読まない。on_started失敗もsupervisorの停止/reap経路に入る。

既定APIが外部期待値へ結合する範囲はselected source10本/Python2file/保持した入出力。formal/promotion/S6/trust/execution_authenticated/full closure=false。追加の依存観測は以下のopt-inを使う。

## 依存fileの追加観測

`observe_dependencies=True` を指定すると、子の実import origin・既存cache候補・EnumProcessModulesExで得たloaded imageを検査前後で採取する。collectorをimportしrequestを解読した後が前観測の境界。builtin/frozen/no-file moduleも分類する。既存file/moduleの消失・変化は拒否し、新たなimportは差分として記録する。

親は終了確定とstdout pinの確認後、sourceは指定Git revision、runtime等は現在のdisk bytes/identityと照合する。Python/Windows System32外のnative fileは、親のloaded image一覧にもある同一pathに限定。1MiB buffer、512file、1file64MiB、合計256MiB。opt-in時のみ監視output枠は1MiB、30秒/512MiBは既定と同じ。

成功例ではsource28、stdlib79、既存cache候補77、extension8、その他native40の232fileを記録した。dependencies.jsonとdependency-crosscheck.jsonを追加保存する。従来evidence/bindingの10source/Python2fileとは別の補助記録で、子由来の一覧を独立した事前期待値とは扱わない。cacheの実使用やmemory内code、完全依存閉包は未証明。正式freeze/受入ではない。

既知のCRLF差を保全するため、今回の接続試験は指定commitから作る候補checkoutで実施した。[詳細結果](results/anomaly-multiseed-v0.3-reader-dependency-observation-2026-09-25.md)。次は役割別の独立した期待profileとimport準備境界を具体化する。

## 事前保持profileとの照合

別に完了したreaderから候補を作り、`dependency_profile`と`expected_dependency_profile_pin`を指定できるようになった。候補は起動前に検査してメモリに保持し、子と親の両方で前後の依存一覧へ比較する。追加/欠落module、候補や保存copyの差し替えを拒否。profileを入力へ結び付け、この場合は16入力になる。[作成APIと制限](anomaly-v03-reader-profile.md)、[検証結果](results/anomaly-multiseed-v0.3-reader-dependency-profile-2026-09-25.md)。

これはengineering候補の事前照合で、独立に定義・承認された完全な依存集合や正式freezeではない。既定動作・正式受入の境界は維持する。
