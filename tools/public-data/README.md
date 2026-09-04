# 公開データ source pinning

MetroPT-3の取得元と再配布可能性を固定し、取得済みarchiveを検証するための最小ツールです。sourceのraw archiveはGitへ追加せず、repository外のcacheで管理します。core importは標準ライブラリだけで、外部通信は明示的な準備コマンドを実行した場合に限ります。

## 準備

`--accept-cc-by-4.0` を付けない限り、cache作成・ネットワークアクセス・ダウンロードは開始しません。

```text
python tools/public-data/prepare_metropt3.py --cache-dir D:\banto-cache\public\metropt3 --accept-cc-by-4.0
```

既定manifestは[`datasets/manifests/metropt3-source.json`](../../datasets/manifests/metropt3-source.json)です。source URL、archive filename、archive size/SHA-256、ZIPの全member、member size/SHA-256、UCIのdataset facts、CC-BY-4.0、attribution、取得元revision相当を固定しています。URLやfilenameをCLIから差し替えることはできません。

## 検証と安全境界

- cacheはrepository外の既存または作成可能な通常directoryだけを受け付けます。
- archiveが存在する場合は、symlinkやdirectoryを拒否し、archive全体、ZIP CRC、member集合、member size、member SHA-256を検証します。
- archiveがない場合は同じ外部cache内のunique temporary fileへstreamし、検証完了後に既存targetを置換しないatomic publishを行います。途中失敗時は自分のtemporaryだけを削除し、partial archiveは公開しません。
- 既存archiveの検証失敗時に再ダウンロードして上書きすることはありません。修正は別cacheまたは明示的な手動退避後に行います。
- ZIPのduplicate member、extra/missing member、path traversal、壊れたCRC、member hash不一致はfail closedです。展開処理は行いません。
- 出力JSONは実行時のarchive pathを含みますが、tracked manifestにはローカル絶対pathを記録しません。

## MetroPT-3の未解決事項

UCI metadataには、instances descriptionの「1 Hz」とvariable informationの「0.1 Hz」というsampling frequencyの矛盾があります。CSV変換前に実データのtimestamp差分を経験的に検証し、どちらかを暗黙に採用してはいけません。またCSV timestampに明示timezoneがないため、timezoneの仮定を決めるまで変換・benchmark投入を開始しません。

このsource pinningは取得元の同一性を保証しますが、時系列canonical化、role mapping、欠損／stale処理、split作成は別の変換工程です。変換時にはraw archive hash、変換設定hash、code revision、出力hash、license attribution、時系列split、known-futureのavailability根拠を別manifestへ記録してください。
