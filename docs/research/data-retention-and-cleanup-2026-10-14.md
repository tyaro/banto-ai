# 研究方針に合わせたデータの保管と整理

## 後続の方針変更・現在状態

人の明示承認により、ここで保管した旧C0 archiveを含む指定旧証拠約3.46GBをbackupなしで削除した。[最新の削除結果と保管範囲](workspace-retention-2026-10-14.md)を優先。以下は圧縮保管/元129root削除当時の履歴であり、archiveが現在も存在するという状態ではない。削除したraw証拠はこのworkspaceから復元不可。現在の需要研究・公開原本は保持した。

整理日: 2026-10-14 JST

現在使う公開データと、終了した合成異常検知研究の保存データを分けた。旧C0/C1/C2評価の原本約4.26GBを約243MBの復元可能なアーカイブへまとめ、全2,489fileを読戻して元bytes/SHA-256との一致を確認した。人の具体的な承認後、元129dev rootsを削除済み。整理前からの純削減は約4.02GB。

## 現在の研究に残すデータ

| 対象 | 調査時の容量 | 用途 |
| --- | ---: | --- |
| Store Sales原本 | 約22.4MB | 季節・販促を加味した需要予測の主候補 |
| UCI油圧原本 | 約76.6MB | 工場設備の多変量状態診断候補 |
| MetroPT-3の既存変換済み探索日 | 約1.51MB | 小型独自モデルの既存入力と再現情報 |
| 小型独自モデルのsource・学習結果・選択予測 | 継続保管 | TimesFM公開構造を参考にした独立モデル研究の成果 |
| environments/timesfm3/.venv | 約735.6MB | 現在の小型独自モデルでもTorch依存に使う隔離環境 |

Store Salesは[受領記録](store-sales-source-intake-2026-10-14.md)、工業公開データは[取得状況](public-dataset-acquisition-2026-10-14.md)、小型モデルは[一回探索](timesfm3-small-model-pilot-2026-10-14.md)を参照する。TimesFM用という環境名だけで現在不要とは判定しない。

Online Retail II原本約45.6MBは、より直接的な季節・販促入力を含むStore Salesを取得したため、当面の主入力から外して保留候補とする。閉鎖済みUCI取得rootの中にあるため、今回そのfileを個別削除してinventoryを壊さない。CARE/XJTU/FreshRetail本体は未取得で、削除対象となる原本はない。

## 容量の内訳

workspace内の通常fileをmetadataだけで集計した。外部cache・顧客repoは今回の対象外で、観測本文による再評価は行っていない。次の容量は圧縮copyを作る前の調査値。

| 区分 | bytes | 状態 |
| --- | ---: | --- |
| artifacts全体 | 10,447,092,823 | 過去の実験結果、失敗・CI/native証拠、現在の成果が混在 |
| 旧代表異常評価 | 4,259,850,154 | 129dev roots、2,489files。全129rootにroot-closedあり |
| その他artifacts | 6,187,242,669 | formal/native・過去失敗の保持条件を含むため、名前だけで不要と判定しない |
| data/public | 144,655,972 | 公開原本と取得metadata |
| environments | 735,646,330 | 現行依存を含む |
| datasets | 5,925 | source manifestと配置文書 |

容量の大半は最近取得した公開データではなく、従来の合成異常検知・受入準備のartifactである。root-closedがない親directoryにも固定済み子root・失敗証拠があり、「未閉鎖だから削除可能」とは判断しない。

## 完了した圧縮保管

対象を次の一つに限定した。

- 元root: `artifacts/representative-anomaly-evaluation/`
- 内容: 129個の `dev-*` root、2,489files
- 元file合計: **4,259,850,154 bytes**
- 保存先: `data/archives/retired-anomaly-evaluation-20261014/`
- `data/archives/retired-anomaly-evaluation-20261014/archive-manifest.json`（当時のpath、現在削除済み）
- gzip済みtar: **242,871,553 bytes**、32MiB以下の8parts
- manifestとclosureを含む保存先全体: **243,369,377 bytes**
- 元rootを削除した場合の整理前からの純削減見込み: **4,016,480,777 bytes**
- 連続した圧縮原本のSHA-256: `d93aa452beb00d7095175110d1bf422b225d9095f5f4c712a45edb4d3b40b14a`

全fileをtarへcopyする時にbytes/SHA-256を捕捉し、生成したpartsをtarとして一度stream読戻して2,489fileすべての一致を確認した。元fileのsize/mtime/inodeはcopy前後で一致。元rootへの書込み・追加・削除0。既存root-closedのbytes、元失敗、CLI原出力、input/config/result対応をそのまま含む。

この処理はデータ保管の確認であり、完成済みモデル・異常検知・試験・CIの再実行ではない。対象は保存済みdev outputsのみで、登録holdoutの元観測やnative所有権を観測・解決した証拠とはしない。処理38.18秒。新出力だけに1GiB/32file/single32MiB上限と閉鎖metadata予備を適用し、各書込み前に件数/bytesを確認した。新rootは閉鎖済みで追記しない。

## 完了した原本削除

人の明示承認対象は **`D:/develop/banto-ai/artifacts/representative-anomaly-evaluation` の元129dev rootsだけ**。人は具体確認へ「圧縮アーカイブを残して元フォルダを削除する（推奨）」と回答した。承認対象を一度削除し、復元可能な圧縮保管とmanifest・研究文書を残した。その他artifacts、登録holdout、公開原本、現行モデル・環境の削除0。

以前の閉鎖root・原証拠保全指示を変更する具体承認を保存した。削除前に8archive partsと連続圧縮原本のSHA、元2,489fileのbytes/SHAとarchive manifest、directory/file集合を照合。workspace内の指定絶対targetとarchiveが別であることを確認したPowerShell Remove-Itemで削除した。初回archive/読戻しは再実行せず、新しい削除記録rootへ元返値・stdout/stderr・終端を保存した。archive作成時manifestのsource_deleted=falseは作成当時の履歴として変更せず、現在の削除済み状態は別の削除recordを優先する。

削除後は旧文書の元pathが通常の読取り先ではなく履歴参照となる。必要な旧結果はarchiveから新しい通常directoryへ復元して読む。閉鎖rootへ再展開・追記しない。復元時はmanifestに従ってparts順序・file相対path・bytes/SHAを照合する。

## 保存状態

圧縮copy・原本一致確認・明示承認対象の元root削除が完了。元root不存在、archive retained。原削除保存は `artifacts/representative-retired-anomaly-delete-20261014-records`（complete閉鎖）。圧縮copyは `artifacts/representative-retired-anomaly-archive-20261014-records` とarchive manifest/root-closed。作成時の元保存・原承認は変更しない。本文の初回確認待ち保存は同data-retention doc-records、完了追記は `artifacts/representative-data-retention-delete-20261014-doc-records`。Git後は同data-retention git-recordsのpost-save/root-closedを優先する。

既存automation PAUSEDを維持/更新0。追加agent0、旧helper反復0、model/test/CI反復0。formal_permission=false/credit0、正式受入・モデル採択未完了、登録holdout未読、native reader禁止。原本やarchiveをGitへ送信しない。
