# 判定差と保存済み観測値の対応表示

2026-09-16 JST。実装savepoint **a013ec2c4175725b091702ad9d6e0fa7804bac31**。
[使い方](../anomaly-v03-local-preview.md#判定差の詳細)。§116の通常権限・単一writer運用を継続した。

## 実装と検証

compareの各詳細に、同じ設備の直前1秒・当該・直後1秒の保存済み観測を追加した。
4つの計算対象信号の値・単位・品質とmode/recipeを表示し、C2が併用する他信号も照合できる。load_proxyは含めない。
時点の欠測はpresent=false/observation absentとし、null値や別設備の観測で補わない。直後の観測は計算終了後の閲覧専用。
検証済みsnapshot bytesは最初の1候補分だけ保持し、追加の展開済み観測は表示対象の時点に限定する。詳細0件では観測表示用の解析を省く。
自由文字列をMarkdownのセル内へescapeし、旧observationsなし詳細JSONも描画可能。計算式・保存API・CLI引数は変更していない。

**関連22件pass / failure・error・skip0 / 9.334秒**。4信号の値/単位/品質、C0入力差分、設備・時点の一致、欠測とnull、単位の特殊文字、保存後の元入力変更、表示省略、旧JSONを確認した。
初回22件は1 error（10.146秒）。テストがgapによるphaseリセット後にも判定差の行があると仮定していたため、通常phaseの統合試験と欠測表示の検証を分けて修正した。初回はpassに数えない。
独立レビューP0〜P3所見0・進捗poll0、repository safety/diff-check pass。広い評価moduleやprincipal試験は実施していない。

## 保存済み3候補の実CLI確認

通常Python 3.14.0のcompare PID26676、UTC01:32:17.597939〜01:32:30.144467、12.547秒、exit0。
既存C0/C1/C2を再利用し、入力・候補payloadの新規生成0。新observations欄を除けば、前回の比較・詳細の全項目が一致した。
表示した2組×3時点×4信号＝**24セル**の値・単位・品質が、保存済み観測と一致。重複を除く設備/時点は4組だった。

| Sample / Target | 直前値 | 当該値 | 差分とC0残差 |
| --- | ---: | ---: | ---: |
| 7202 / motor-01.vibration_feature | 130.03 | 130.28 | 0.25 |
| 7203 / motor-01.motor_current | 115.28 | 100.83 | -14.450000000000003 |

同時点の他信号も表示するため、sample7202の電流115.28と、vibration_feature側のC2判定を並べて確認できる。表示は入力と計算結果の照合であり、因果寄与の分解や性能順位の判定ではない。
表 `artifacts/local-observation-context-2026-09-16/comparison-observations.md` は7235 bytes/hash `998a218610d2f6a69e2c6d9674927097976e122df4fb705e79a71bce91110b83`。

## 保存・資源・次工程

選抜130 sourceのworkspace/Git blob一致（126不変・4変更）、前回公開artifact8件不変。選抜は完全な依存閉包ではない。
input-evidence22971 bytes/hash `3c627452322f07ad7b934bb7bb3242f0895e540b9e9bf46f6b5cbcf8fda348b1`。
最終manifest27542 bytes/hash `b0ee357476fc5ee380fd5c4f27b776fc45772954d1f91615f3c4d596171b6971`。自身を除く8 artifacts/49617 bytes、manifest込み77159 bytes（約75KiB）。
終了後UTC01:34:12、空きRAM16946081792/C153028853760/D171638452224 bytes（D約159.9GiB）。PC全体の容量変動原因や長期リーク不在は断定しない。
OS26200.9445/boot2026-09-16T08:46:30.5000000+09:00、Windows Update engineering緩和・正式pin不変。本流889cfc3/cleanを維持。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621は保全・commit除外。

ローカルの計算・保存・比較・観測照合の経路が一通り揃った。**次は、単一writer運用の評価実行経路と、現行計画§8/9・runtime gateの差分を整理し、次に必要な契約判断を具体化する。** 科学的な候補式・seed・閾値・評価条件を維持し、正式未実施をpassへ置換しない。
専用principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。§116の保留と旧root閉鎖・jの消費済みguardを継続。
local_comparison_computed=true、今回local publication0。formal_permissionと他のnative保証flagはfalse、acceptance_status=not_completed。正式campaign入口・科学的評価条件・受入gateは未変更。
