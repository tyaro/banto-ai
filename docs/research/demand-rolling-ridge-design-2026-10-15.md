# 発行日前365日の完了窓だけによるローリング回帰

2026-10-15 JST。heartbeat banto-ai-macによる自走継続。[最新引継ぎ](../current-handoff.md)の過去pool更新を一件実施する。新しい人の停止指示はなく、この起動はschedulerである。

## 固定する仮説と方法

固定2013–14回帰は2015で過小方向のbiasを増やした。容量/λを探し直さず、同じ72列/lambda0.01回帰の学習期間を発行日時点に追従させる方法を検証する。平均販売数量をtarget、元mean28対照、元NN3328参考を維持する。

各originで、packetの店を許可10店に限定し、origin−365<=packet originかつpacket origin+13<originをmetadataで判定してから、完全観測14日labelだけを学習に使用する。最低140窓/全10店を要求し、不足ならmean28。実データの各店窓数均等を確認し、不一致は店舗除外や再重み付けをせず停止する。
過去残差統計8/context統計2/future暦60/lead1/intercept1の72列。各originの過去poolだけでmean/population stdとactive列を作り、日次/総量正規化MSE半々＋非intercept ridge罰則をfloat64で一回solveする。std<=1e-12はinactive、interceptは1。raw出力を非負clip。前期uと原暦有効42flagは変更しない。
同一originの10店を同じstateで予測後、その10packetを将来poolへ追加する。current行・同時刻他店・未完了窓のlabelは学習しない。profile/入力はそのpacket origin前56日だけ。

## 内部選択と2015

元fit300を初期pool、2014 time120をorigin順に追加して12回fit/120予測。期間境界でwarm poolを保持する。元NNの内部値はautonomous-mean rootの保存raw_nnを使い、新NN推論/学習はない。
内部time120だけでrolling rawとmean28のconvex blend alphaを、既存C/E joint最小・日次/総量MSE悪化なし・0<=alpha<=1で校正。mean28/元NN/rolling_calibratedのjoint最小を主方式とし、1e-12 tieはこの順。alpha/方式を保存後に2015に進む。
2015既存10店の250要求を25origin順に処理し、完了済みの内部/以前の2015packetだけを365日poolに追加する。学習更新自体は続けるが、λ・窓・features・u・alpha・方式は2015で選び直さない。
主方式の性能と、事前に固定したrolling_calibratedの副評価を両方保存する。副方式を結果後に主へ昇格しない。NN参考は保存予測を再利用する。labelなし予測を保存後に採点用実績を付与し、250/3490日/240完全総量/Christmas nullを保持。

全10店等重みの日次MSE/u²・完全総量MSE/(14u)²・joint、全店/全quarter/MAE/WAPE/bias/支持を保存。暫定2%改善・日次総量悪化なし・支持不変は主方式に適用し、副評価も同条件を参考表示。PSI採用はfalse。2015は既読で仮説の起点にもなっており、未知性能/盲検/有意性としない。

## 記録と境界

fresh root macos-demand-rolling-ridge-20261015 と同execution/readback/doc-records。各originの係数/標準化/pool keys/最大label末日/支持をjournalとして保存。新架空fixtureでfuture/current/同時刻他店label poisonとmetadata先行選択、365日端点、過去poolだけの標準化、cold fallbackを検査してから実行する。
模型通常24files768MiB/全32files1GiB/single32MiB/失敗8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16files、親900秒/子870秒/Mac sampled footprint/peakRSS各2GiB。全stdio/exit/source/state/失敗/closure、原root前後不変を保存。失敗を上書き/盲目的再試行しない。
CPython3.14.8/Torch2.14.0 Mac arm64 CPU/2threads/interop1/deterministic。元Windows private bytes受入ではない。原ZIP再抽出/新データ/2016–17/予約31–54/販促/正式holdout/Windows native/CARE/課金API/外部送信/Git push/削除/追加agent/本番採用なし。formal_permission=false、既存変更/closed roots保持。結果と次の有益な工程をhandoffへ残し、heartbeat継続方針に従う。
