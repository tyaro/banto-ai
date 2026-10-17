# 小型独自モデルの最小実装確認（2026-10-13）

## 結果と範囲

独立初期化のoptional Transformerを実装。登録parameter実測109024、3系列/C128/H32/P32/D64/L2/head4/FF128/Q3で設計と一致。
fullとdiagonal self-onlyは同じ登録parameter/初期stateを持つ。self-onlyのQ/Kは退化するため、同じ登録数を同じ有効容量とはしない。公式TimesFM3の構造・学習・zero-shot性能の再現ではない。

[実装](../../models/mini-transformer/small_model.py) /
[確認script](../../models/mini-transformer/check_model.py) /
[設計](timesfm3-small-model-design-2026-10-13.md)。

Astraの読取り批評を反映し、full networkの他系列接続と正規化training lossの独立手計算を初回前に追加。新10確認を一度実行し10passed/0failed。完了済み評価・試験・CIは反復していない。

| 新確認 | 結果 |
|---|---|
| shape/parameter/head | [2,3,32,3]、109024、有限値、分位点順序、逆正規化 |
| future label境界 | forwardはcontextだけ。loss側label変更で出力不変、context非変更 |
| self-only隔離 | 系列1の形を変えても系列0/2の出力不変 |
| full接続 | 同じ変更でfull系列0の出力は変化 |
| attention mask | 固定Q/K/Vで全系列平均、自己値、時間prefix平均を手計算 |
| series permutation | 共通floor条件で両構成が系列置換に対応 |
| selection loss | quantile pinballと固定train scaleの式に一致 |
| normalized training loss | 平均2/scale2/actual4の手計算7/30に一致 |
| backward | 勾配有限・非ゼロ、parameter更新なし |
| 入力拒否 | nonfinite/shape/dtype/batch上限拒否、一定contextのfloor動作 |

選択した入力での実装確認であり、全入力の証明・予測性能・実設備誤警報率の証拠ではない。未来実測、TimesFM weights、teacher出力、観測dataset本文を使っていない。optimizer step0。

## 実環境と資源

既存隔離環境 environments/timesfm3/.venv のCPython3.14.0/Windows AMD64、実import Torch2.14.0+cpu。TimesFM3 packageはimportしていない。通常Python環境へ依存追加0。
新optional requirementsはtorch==2.14.0を宣言。既存lock/pyvenv.cfg/2実装sourceのbytes/SHAを原保存へ固定。wheel digest/依存推移全体は未固定で、完全な供給経路再現性とはしない。

checks内部elapsed0.28266799997072667秒、親11.403536399942823秒（import等含む）。
OS private1021820928B / peak pagefile1021829120B / peak working set311668736B。
各check後のcurrent-process counterと900秒/private2GiB checkpointを確認。親timeout120秒。OS peak pagefileは全writer/global/nativeのcoupled peak・予約・blocking中断の証明ではない。実行上限不変。

## 原保存と失敗分類

- 環境metadata: artifacts/representative-small-model-environment-20261013-records（閉鎖）
- 実確認: artifacts/representative-small-model-focus-20261013-records（閉鎖）
- 文書: artifacts/representative-small-model-implementation-20261013-doc-records
- Git後: artifacts/representative-small-model-implementation-20261013-git-records の post-save/root-closed

EvidenceStoreはscript/source pins/返却stdout-stderr/exit/first error/分割/失敗予備を保存。foreground親process全stdio/fullcreationは未捕捉。誤ったrg path/V8 TextEncoder参照/文書functions isolateのSyntaxErrorは選択tool観測として保存し、モデル/CI/native失敗へしない。isolate SyntaxErrorはnested tool/process/tracked変更前。
親Python起動時「Failed to find real location」はexit0のtool警告で、モデル失敗へしない。閉鎖root追記・原check再実行0。

## 次の未完成unit

探索用MetroPT候補の観測pin/連続時刻/quality/splitを一度照合し、固定originのcontext/label・train-only scale・共通batch列を作るdataset adapterと単一の小さいtrainerを準備する。
人工tensorの境界確認は新ケースとして実施し、既存10確認は反復しない。まず学習前準備を保存。実データ学習はその準備と資源確認後判断する。登録holdoutは読まない。過去評価済み24h public testは探索用で新規holdoutへ改称しない。

人の「しばらく自走、進めなくなった場合止める」に従い、判断・入力・許可・実環境等が不足して進行不能になれば原証拠と未完成地点を保存しautomationをPAUSEDにする。heartbeatを不足する承認の代用にしない。
formal gate=s4_acceptance_not_frozen / formal_permission=false / credit0 / 方式採択・正式受入未完了 / native reader禁止。
