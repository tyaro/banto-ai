# Macでの需要入力・profile・模型の新規生成

2026-10-15 JST。[固定契約](../research/demand-macos-rebuild-design-2026-10-15.md)に従い、公式Store Sales ZIPからWindowsの旧artifactをコピーせず新生成した。
生成・学習・保存は完了したが、mean28を上回る暫定開発条件は未達。この一回で区切り、製品採用・追加学習は行わない。

## 作成したもの

原本参照manifest、内部/開発snapshot、前期尺度、splitと暦支持、内部480/開発150のprofile・統計8入力、initial/sampler、更新journalと選択曲線、finalと二つの選択state、150件のlabelなし予測と別経路で付与したlabel、指標、source/契約pin、child全stdout/stderr/exit0、closureを保存した。

Git基準6690531fd6ef081e3605c3801e610e466e1be0ea。CPython3.14.8 / Torch2.14.0 Mac arm64 / CPUfloat32 / 2threads / interop1 / deterministic。
StatisticalFeatureMean30369parameterを新initialから一軌跡だけ学習。10店fit300窓、同店時間validation120窓、別5店移行validation60窓。
3840更新で移行validationのearly stop。時間最良3328、移行最良3072。異なる二stateを固定後、開発6店へ各一回適用した。

## 固定開発の結果

主指標はpositive5店を等重みとした、日次MSE/u²と完全14日総量MSE/(14u)²の.5平均。

|方法|日次|総量|joint|
|---|---:|---:|---:|
|mean28|0.048888499952|0.011307497606|0.030097998779|
|時間選択3328|0.049489167360|0.012121862958|0.030805515159|
|移行選択3072|0.048922594485|0.011633074187|0.030277834336|

移行選択はmean28比**0.597500%悪化**。日次/総量も悪化し、2%以上改善・副条件の暫定判断は未達。生成の成功と性能改善を分ける。
150要求、NN125、zero-scale店20のbaseline25、完全label144を保持。positive5各25入力/24完全labelで支持不変。Christmas欠測はnullのまま、13日和を14日総量として採点しない。

既読開発データの一seed/一splitによるMac新規実行であり、未知性能・メーカーPSI・TimesFM同等性能・統計的有意性・本番適合を示さない。
Windows報告と終了/選択stepは一致したが、旧weightsを受領していないためbinary stateや旧実行証拠との同一性は未検証。新snapshot/profileのhashを旧hashへ置き換えない。

## 保存先と確認

- 模型と入力: `artifacts/macos-demand-rebuild-20261015/`（closure含め22files、約4.9MiB）
- 実行記録: `artifacts/macos-demand-rebuild-20261015-execution-records/`
- 保存stateと予測の読戻し: `artifacts/macos-demand-rebuild-20261015-readback-records/`

模型rootのexact file set/bytes/SHAと両EvidenceStore closureがpass。二つの実stateを`weights_only=True, map_location='cpu'`でstrict loadし、30369parameterの型へ接続できた。
読戻しではforward/学習を行わず、150件のlabelなし予測がlabel付与後も同じこと、閉鎖root不変を確認した。新境界fixture5件がpass。旧確認・旧評価・全CIの再実行結果ではない。

child elapsed24.558739秒。sampled physical footprint最大310838160B、peak RSS304824320BでMac各2GiB上限内。Mac指標はWindows private bytesと同じ定義ではなく、sample checkpointはOS hard capや全runtime/native容量証明ではない。
TorchのNumPy未導入警告は全stderrに記録、tensor専用経路の実行はexit0。MPS・公式TimesFM weightsは使用しない。

## 現在の引継ぎ

今回のMac研究はこの新rootの入力/profile/stateから継続できる。Windowsの旧26rootのコピーは今回の新生成の必須条件ではなくなった。ただし旧失敗・旧実行履歴・削除済み証拠を復元したわけではない。
一回保存で研究を停止、automation再開0。新仮説・seed/split/LR/grid・追加年度へ自動で進めない。2016/2017・予約31–54の数量・販促実績・正式holdoutは数値解釈していない。
CARE手動待ち、formal_permission=false、製品採用0、原data/profile/ledger/予測/weightsのGit送信0を維持する。
