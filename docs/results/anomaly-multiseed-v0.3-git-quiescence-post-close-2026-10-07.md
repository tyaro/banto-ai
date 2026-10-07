# v0.3 Git receipt・post-close quiescence接続（2026-10-07）

code保存点 `301644854a9e4db7d6915ffda6c9bf8278be54dd`。正式gate `s4_acceptance_not_frozen`、formal_permission=false、正式credit0、登録holdout観測未読。先行channel/stop fenceの再試験と新nativeは0。

## この小さい単位で結んだ範囲

- `_close_owned` はCloseHandle/診断より前に元thread/process/jobを `UnclosedHandles` へ保持する。CloseHandleのFalseでは未close分だけ保持し、例外/割込みでは失敗・未確認handleと後続未attempt handleを保持して、それ以上closeを進めない。元close_errorと診断のdiagnostic_errorを分け、reportへのIO/割込み例外でも元ownerを捨てない。
- 3 handleのcloseが成功した実位置からだけclose eventを返す。`capture_quiescence=True` の明示private Job opt-inで、実 `_execute` のpost-close eventをreceipt pin・元native creation identity・exit・empty Job accountingへ結ぶ。既定のresult/tuple/receipt JSON fieldは維持し、既存保存receiptを新schemaへ読み替えない。
- 公開 `verify_quiescence` は外部policy・root・receipt raw pin・stdout/stderrを既存 `verify_raw` へ渡して完全なretained照合を行い、さらにpost-close witnessを照合する。native original pid/creation/token、3 distinct handle value、exit type、accounting typeと値、formal false、未知field拒否を固定。失敗callでもexit/reap/closeとrawが確認できたものはquiescentとして照合でき、call成功や正式creditとは区別する。
- direct-handle policyのcaptureはspawn/root前に拒否。private Jobのcaptureは既定False、通常worker invocation/actorからはまだ呼ばない。close未確認・unstarted/identity未確認のcallには回収済みTrueを与えない。

## 試験・保存

新 `GitQuiescenceTests` 16件 / 0.727151秒、fail0/error0/skip0。実owner/Job executor/retained verifierの関数をfake Kernel・fake executable observation/policy・fake creation identityで通した。close順、default互換、reaped failed call、close割込み、extra handle付き元UnreapedJobの無fallback、False/例外/診断失敗時の原handle保全、raw/output/policy/creation/accounting/handle/permission改変拒否を確認した。実exe/実Kernel/native/容量合格の証明ではない。

選択13 source/test/science pinは前後不変、変更4file `scan_repository(paths=...)` pass。code-saveはHEAD=origin/cleanと13 working/Git pinを照合。全repository safetyは先行e4cbの30秒TimeoutExpired未確認を維持し、再試行/上限緩和なし。全helper終了、critical ownerなし、新native0・追加agent0。

raw root `artifacts/preformal-git-quiescence-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 4475 | `c8e89086a33a696ce82cb4c792d9a8bf2d5b67232bfc2945f9f25c8814b19309` |
| focused.log | 3189 | `b8ae9ca184e67f844aa12a7e6c8140711a94fc5baba2250b39a770c5b6d920f2` |
| code-save-checkpoint.json | 566 | `92f8653145a29f4263e84ad446c27f8ae5cff3c000d1cf7a81851d0108e9643b` |

新CI37585092575（HEAD3016448、各minor3207件予定）は進行中。先行未保存37581339092（HEADaaca57c/3178）・37583002436（HEADe5ff975/3191）もrun未終端。完成CI/旧nativeは反復しない。

## 次の原owner keeper／compact proof単位

channelのactive lease・共有stop/clock・compact32 KiB proofへは未接続。child keeperと実worker invocation/initial-reader actorも未接続。receipt-linked witnessは保存観測の整合性であり、loaded-code/execution認証や業務異常子孫回収の証明にはしない。

次はreap失敗を検出した時点で、追加Terminate/診断より前に元UnreapedJobを保持し、stop/診断例外をそのownerへ付ける。現Git executorのreap fallbackは元例外への診断属性付与を含むため、この範囲を先に保全する。child keeperは元Job/process/thread/extra handleと失敗inflight/partial archiveを保持し、marker/IO/sleep割込みがPython終了へ落ちない経路を結ぶ。close成否が不明のhandleはblindに再closeせず、確認不能を保全する。shared stopをprobeへ渡して新Jobを拒否し、確認できた回収/close/raw保存の後だけleaseを完了し、compact proofを親の外部pin付きverifierへ渡す。

その後Parent.create/on_started bind/stop_fenceとChild wait/Job leaseを実invocationへ結び、実importを含むsource inventory/runtime profileと専用未使用rootを新revisionで準備する。旧14/14・旧parent111/111・旧runtime/native保存点を読み替えない。pending＋完成frame＋compact proof・原inflight/失敗rawを既存outer/root reserve内へ計上し、接続/拒否/停止保全ができる前には新nativeを開始しない。
