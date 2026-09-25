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

実際に観測した範囲はselected source10本/Python2file/保持した入出力。stdlib内部、extension、OS DLL/CRT、Git helper、全source依存、実行真正性の完全な証明は残る。formal/promotion/S6/trust/execution_authenticated/full closure=false。正式documentや性能判定は開かない。readerの依存sourceとstdlib/extension/loaded DLLの記録範囲を広げる。既知のCRLF差を現在の作業コピーで修正せず、必要なら指定revisionの一時的な候補checkoutでraw一致を確認する。正式freezeとしては扱わない。
