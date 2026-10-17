# Astra：丸め差付き比例配分・floor到達の人工接続

2026-10-16 JST。ユーザー指定の既存gpt-6-astra担当を再利用。実データ内容を読まず、追加agentなし。

## 起動前

2026-10-16 JST。既存gpt-6-astra担当 /root/astra_weight_support_audit、追加agentなし、実データ内容decodeなし。

固定400件案は整合する。Rのmean28はfloat(.1)+weekday/1024、営業日数13/14でEとcanonical Bに残差があり、独立readerで生成baselineからexact確認する。Sの2^-20は二進の厳密縮小で、rはそのprofile自身の縮小前historyと比較すべきで、weekdayとuniform同一とは限らない。positive certのβ0<0と十分小さいBによりstrict negative rawが得られる。Jan1 80copy/R160比例/Spositive80floor/Snegative80比例、152scenarioの件数も一致。新compile/solve不要。

source起動前確認の最終回答：
「起動前 blocking はありません。保存8 state の完全再利用、r/state/係数の binding、400件の分岐条件、200件の scale 不変性、152 scenario、15拒否が整合しています。旧 floor 非到達を前提にした条件も残っていません。
未凍結のうちに次の小さな補強を推奨します。
- reader で raw制約差・週寄与の件数も独立集計し、summary と一致確認する。
- fixtures の到達不能な旧 label 生成 branch と未使用 project_label import を除去する。
floor後へ raw寄与の線形式を拡張せず、今回の compile/solve/fit=0、実学習・2015停止を維持する結論が妥当です。」

両補強を起動前に反映。Sのprofile別scale不変性200件、raw shift/weekly summaryの独立count照合、fit入口2関数のcanary count0を検証する。rawP=0境界は今回対象外。

## 保存結果の最終確認

2026-10-16 JST。既存gpt-6-astra担当 /root/astra_weight_support_audit、保存結果のread-only最終監査。

新たな blocking はありません。独立 readback も complete、model closure・195保護 closure／316 source・今回 source pins・reuse/予測 freeze の一致を確認しました。文書 closer にも起動を妨げる箇所は見つかりません。

保存結果は整合しています。
- 旧8 state は原本と bytes一致、新 compile/solve は0。
- B≠E はR全200件：比例160件、copy40件。
- Sは strict負raw→floor80件、正総量の比例対照80件、copy40件。
- 152 scenario、15拒否、scale不変性200件、raw制約差320件・週寄与0が独立照合と一致。

「保存済み制約付き非ゼロ解から、丸め差付き比例配分とstrict負値floorへの人工接続を検証済み」という結論が妥当です。ゼロ境界・将来raw非負・実性能は未保証とし、実学習・2015停止を維持して文書閉鎖へ進めます。
