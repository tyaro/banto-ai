# 公開研究データの取得状況

取得日: 2026-10-14 JST

需要予測と設備状態の研究に使う公開原本を、Git管理外のローカルcacheへ保存した。今回は油圧設備とOnline Retail IIの2件、原本合計122,224,122 bytes。取得完了はモデル性能や実用性の評価完了とは区別する。

## 取得済み

| データ | 原本bytes | 保存先 | 利用条件と用途 |
| --- | ---: | --- | --- |
| [Condition monitoring of hydraulic systems](https://archive.ics.uci.edu/dataset/447/condition+monitoring+of+hydraulic+systems) | 76,601,704 | [source manifest](../../data/public/research-20261014-uci/hydraulic-systems/source-manifest.json) | CC BY 4.0。油圧装置の多変量信号と部品状態。状態診断向けで、自然な長期劣化・残存寿命の正解とはしない |
| [Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) | 45,622,418 | [source manifest](../../data/public/research-20261014-uci/online-retail-ii/source-manifest.json) | CC BY 4.0。2年間のギフト小売取引。季節・暦の研究向け。食品メーカー出荷や販促予定履歴の代替とはしない |

帰属: Helwig, N., Pignanelli, E., & Schtze, A. (2015), UCI, DOI [10.24432/C5CW21](https://doi.org/10.24432/C5CW21)。Chen, D. (2012), UCI, DOI [10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D)。原公開ページの取得bytesとCC BY 4.0の参照を保存した。

油圧ZIPは20member、Online Retail II ZIPはExcel原本1member。展開せず全memberをstream読取りし、CRC・bytes・SHA-256を保存した。元ZIP全体のSHA-256は次の通り。これらは今回観測したbyte pinで、配布者署名や既知の外部期待hashとはしない。

- hydraulic.zip: `24128aad2ee45eea7e6b63ebbd9992cdf25d0483a2cebefbfc13bc69079af1f2`
- online-retail-ii.zip: `572e36277c2390fbfde10664750731e0a86f55e33470d91919085f0408e67bfb`

### 原本の読取り

1file最大32MiBを維持し、元ZIPを連続したpartsへ分割保存した。油圧3parts、小売2parts。source-manifestのparts順に読めば元ZIP bytesとなる。各partにもSHA-256がある。保存先のroot-closedは完了状態と不変のinventoryを保持し、追記・上書きしない。

取得scriptの `PartsReader` はpartsをseek可能なfile-like objectとして読み、`zipfile.ZipFile`へ渡せる。大型ZIPを別fileへ再結合する必要はない。script正本は `artifacts/representative-public-dataset-acquisition-20261014-continuation-prep/download.py`。元scriptのmainは再実行しない。新しい変換unitでは必要な読取り機能だけを使う。

既存の[MetroPT-3 source manifest](../../datasets/manifests/metropt3-source.json)と取込済み探索用データは保持し、再取得・完成評価の反復は行わなかった。

## 保留候補

| 候補 | 今回の状態 | 再開前に確認すること |
| --- | --- | --- |
| [FreshRetailNet-50K](https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K) | 公式メタデータGETが接続reset/curl exit35。データ本体0bytes、採用revision未固定 | ネットワーク障害の解消後に新unitで版・CC BY 4.0・公開LFS pinを確認。90日・正規化数量という研究境界を維持 |
| [Favorita Store Sales](https://www.kaggle.com/competitions/store-sales-time-series-forecasting/data) | 未取得 | Kaggle認証・当該競技の利用条件。多年間季節と販促を扱う候補 |
| [CARE to Compare](https://zenodo.org/records/15846963) | 未取得 | 修正済み版・利用条件・必要fileの容量。先行版の約6.1GB archiveは現在の取得上限内へ入れない |
| [XJTU-SY](https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets) | 未取得 | 公開元の研究利用案内と再配布/商用条件、必要な軸受trajectoryの容量 |
| [Paderborn](https://mb.uni-paderborn.de/en/kat/forschung/bearing-datacenter) | 未取得 | CC BY-NC 4.0の非商用範囲と対象archiveの選択 |

## 失敗の保存と接続経路

初回Python urllibはUCIのTLS certificate expiredでexit1。取得本体0bytes、原例外とtracebackをfailed recordへ保存した。証明書検証を無効化しない。

Windows curl 8.21.0/SchannelでUCIのHEAD 200を確認した後、新root・新scriptでUCIだけを取得した。HTTPSだけにprotocol/redirectを制限し、証明書検証を維持。完成2件のscriptはexit0。HTTP本文の完了はcurlの正常終了とZIP構造/全CRCで確認し、GETの未捕捉HTTP header/statusを200へ補わない。

Hugging FaceのHEAD diagnosticはconnection reset。公式メタデータのGETを新rootで一度確認してもcurl exit35で失敗した。原stderr `Recv failure: Connection was reset` と返値を保存し、データ取得前に停止。TLS失敗や通信失敗をモデル・CI・native・Sol容量失敗へしない。選択tool観測は元process全stdioとは区別する。

## 保存記録と次の作業

- 初回失敗: `artifacts/representative-public-dataset-acquisition-20261014-records`（failed閉鎖）
- UCI取得: `artifacts/representative-public-dataset-acquisition-20261014-continuation-records`（complete閉鎖）
- FreshRetail接続失敗: `artifacts/representative-freshretail-acquisition-20261014-records`（failed閉鎖）
- 本文保存: `artifacts/representative-public-dataset-acquisition-20261014-doc-records`。Git保存後は同git-recordsのpost-save/root-closedを優先。

次は取得済み原本から少数ケースのschema・時刻・単位・欠測・labelの役割を定義する。油圧cycleを連続した実設備寿命とみなさず、小売実施価格を将来既知販促予定へ置き換えない。学習や比較を先に開始しない。

追加取得は通信と利用条件が整うまで停止。既存automationのPAUSEDを維持し更新0。実行側900秒/private2GiB/output1GiB/single32MiB/files32、記録側分割/失敗予備を維持。各新dataset rootは512MiB/32file、今回取得合計1GiB以内の上限を設定し、chunk・script・失敗記録・閉鎖metadataも書込み前に件数とbytesを確認した。容量checkpointはblocking/global/native容量の証明ではない。原本・顧客データをGitへ送信しない。

formal gate=s4_acceptance_not_frozen / formal_permission=false / credit0 / 登録holdout未読 / native reader禁止 / 正式受入・モデル採択未完了。完成済みモデル・評価・試験・CI反復0。
