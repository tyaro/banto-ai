# R2P工程2: Rustの学習部品

2026-10-17 JST。[R2P固定条件](../research/rust-r2p-synthetic-training-contract-2026-10-16.md)の工程2として、人工データだけで検証する学習部品を[`training.rs`](../../crates/banto-ai/src/training.rs)に実装し、[Cloud参照](rust-r2p-cloud-reference-2026-10-17.md)とR0.1の許容差（変更なし）で照合した。

## 実装

| 部品 | 内容 |
| --- | --- |
| normalized pinball loss | r=(actual−center)/scale−prediction、全B×C×H×3の平均。(τ−½)r+½\|r\|と書き、Burnのautodiffで厳密なtieの勾配が(½−τ)/Nになる（Torchのmaximumと同じ） |
| 入力検証 | 形状不一致・非有限のprediction/target・0以下のscaleを拒否（I0〜I3） |
| 名前付き勾配 | 重複・未知の名前は対応付けの前に拒否、欠落は0で補わず拒否（I4・I5） |
| global clip | Torchと同じく要素ごとのnormのnormを取り、係数min(1,1/(norm+1e−6))を全勾配に一律に掛ける |
| AdamW | Torchのsingle-tensor更新（foreach/fused=false）の順序：decoupled decay、lerpの1次moment、addcmulの2次moment、整数stepからのbias補正、addcdiv。勾配0でもstepを進め、既存momentを消さない |

`training-tests` featureと試験target `r2p_synthetic`は契約どおり。CIのRust jobで毎回実行する。

## 結果

| 照合 | 件数 | 結果 |
| --- | --- | --- |
| lossと予測勾配 | 7case | 全件R0.1内（全tieのL1も勾配非ゼロで一致） |
| global clip（norm・係数・clip後勾配） | 4case | 全件R0.1内 |
| AdamW 1更新（clip後勾配・parameter・1次/2次moment・step） | 6case | 全件R0.1内、stepは整数で+1 |
| 不正入力の拒否 | 6case | 全件拒否 |

試験が実装の誤りを検出できるか、意図的な改変で確かめた。tieの係数、eps、clipの分母を変えると失敗した。weight decayの除去は1更新では3e−6〜6e−6の変化でR0.1の1更新許容差の内側に入るため検出できなかった。そこで勾配・moment0のO0に、fixtureの解析条件「全parameterが(1−lr·decay)倍」をbit単位で確かめる検査を足し、検出できることを確認した。許容差自体は変えていない。

## 変えていないもの・次工程

R0.1許容差、固定fixture/protocol、R1の残1点未達、正式R2実データ学習の停止。SmallForecaster全体の学習は未実装。次は工程3（人工affineの連続8更新、checkpoint writer/reader、4更新→別process復元→4更新、checkpoint拒否8・writer途中停止3）。
