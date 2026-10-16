# Rust R1 — 初期化判定の公開契約確認と呼出先照合（2026-10-16）

**SDKの-1比較はinline fast pathで、初期化完了の一般的な外部判定として数値を読む方法は公開APIの契約ではない。Appleの同期APIの保証を使うには、保存命令の呼出先との同一性が必要だった。独立のmetadata照合ではその直接同一性を確認できず、query/train経路は保留した。** 保存済みonce値52638546の内部表現は未解釈。元warm-binding失敗、モデル・許容差、R1安定版累積1点未達/R2停止を保持した。

## SDKと公開APIの仕様

[事前のsource/design条件](../../examples/configs/rust-r1-sgemm-once-semantics-admission-20261016.json)に沿い、installed SDKのdispatch/once.h、base.h、dispatch_once.3、libdispatch.tbd、SDKSettings.json、SDK/Xcodeの版plistをhashと共に保存した。SDK27.0/build26A425、Xcode27.1/build27A9275、stub current-version1605.0.2。保存した実行OSは27.0.1/Darwin27.0.0。SDKは実行時libraryそのものではなく、stub版を実行中の版と認定していない。

once.hはpredicateのzero初期化と、初期化した変数を使う前にdispatch_onceを呼ぶことを要求する。inlineはpredicate==~0lならcompiler barrier、それ以外なら公開関数を呼ぶ。末尾にはcompiler assumptionもある。base.hではそのassumptionが__builtin_assumeであることを確認した。これらはSDKで生成するwrapperの定義であり、実行時のprivate predicate状態が常に-1と読めるという検査仕様に読み替えていない。

Appleの[dispatch_once公式仕様](https://developer.apple.com/documentation/dispatch/dispatch_once-c.func)は、処理を一度実行し、競合する呼出しも完了を待つ同期動作を保証する。predicateはglobal/static storageが前提。このAPI保証と内部predicateの数値表現を区別した。今回、その内部表現を説明する同版runtime sourceは得ておらず、他版のlibdispatch実装を根拠に52638546をgeneration値などと断定していない。

公式ページの検索抽出は読めたが、HTML openはJavaScript案内、Markdownリンク取得はtoolのcontent-type/cache errorだった。帰属付き要約とURL、取得方法の限界を記録し、完全なpage snapshotや版対応sourceの代わりにしていない。SDK本文は別途zipで保存した。

## API identity確認を別工程として固定

source auditは新数値演算/live read0でcomplete閉鎖。その後、[独立したmetadata照合条件](../../examples/configs/rust-r1-once-api-binding-20261016.json)を先に保存した。保存済みqueryのBL@0x18123cdd4とcoreのBL@0x181392aacを元code bytesからdecodeし、両targetが0x1880e1a60であることを検証した。元六関数codeのlive再読取りはない。

一度目は、OS情報に含まれるruntimeのtupleと保存JSONのlistを直接比較していたため、dispatch API照合前のharnessチェックで停止した。二つの閉鎖済みmetadataのJSONを比較するとOS情報とlibBLAS UUIDは一致した。[形式修正の固定条件](../../examples/configs/rust-r1-once-api-format-repair-20261016.json)を保存し、元source/failed rootを変更せずfresh source/rootsを作成。修正はplatformのJSON正規化、出力root名とsource来歴の追加だけで、差分を機械照合した。

その修正後の一度のAPI identity観測では、保存target+shared-cache slideと、libSystemから解決した公開dispatch_onceが一致しなかった。targetに対するdladdrの戻り値は0だった。

| 観測 | 値 |
| --- | --- |
| 保存BL target / image virtual | 0x1880e1a60 |
| current shared-cache slide | 209043456 |
| 計算したtarget runtime address | 6786636384 |
| 解決したpublic dispatch_once runtime address | 6658635120 |
| targetのdladdr | 0（image/symbolを識別できず） |
| native dispatch_once/query/initializer呼出し | 0 |

このaddress照合は公開関数を呼ばずに行った。条件未達で即停止し、別symbolや別addressの探索・再観測はしていない。dispatch image header/版取得はこのgate後の予定だったため未実行。したがって実dispatch UUID/版は今回も未確定。dladdr0は未mappingの証明ではなく、中間stubの証明でもない。直接の公開API入口ではない、という今回の照合結果だけを扱う。

## 保存値からできる判断と残る不足

元warm runの6,144出力bit一致、global@940=1、設定の二度同一という観測は変更していない。元once==-1 gateの失敗もfailedのまま。呼出先の意味が未確認なので、global1だけでquery1、あるいは初期化の成功/失敗を宣言しない。Appleの公開保証を未同定のcallへ当てはめず、train kernelも未確定とする。

次の不足は内部predicateを推測することではなく、既に固定されたtarget0x1880e1a60の転送先/役割である。[次unitの限定条件](../../examples/configs/rust-r1-once-call-target-admission-20261016.json)を保存した。fresh declarationでown-task VM mappingのSDK宣言をpinし、readable+executable/boundsを確認できる場合だけ、正確なtargetの最大64bytesを非実行で読む。一つの転送先が見えてもこのunitで追跡せず、別条件として固定する。mapping/SDK/読取りに不明点があればそのまま停止する。今回はこの読取りをまだ実行していない。

元六関数scopeやfailed rootsの上限をリセットせず、別のexact-address scopeとして扱う。新しいtensor/BLAS/operator/model比較や算術候補の試行を追加しない。

## 資源・保護・OS分離

全12rootsを検証し、うち4failed roots（型比較のpreflightとAPI identity未達、各records込み）を保持した。元warmの2failed rootsも別途pinのまま保持。全source/SDK/hash/stdio/exit/state/closure、修正差分、保存selectorと観測、文書前後をartifacts/rust-r1-once-results-20261016と同-evidenceに保存。publication自体のstdio/exit/stateは同-records。

全phaseは親900/子870秒、physical footprintとpeakRSS各2GiB、build cache+target1.5GiB、旧artifact/EvidenceStore/stdio枠を維持。今回最大監視込みfootprint 181,536,016B、RSS系 244,383,744B、cache+target 1,037,488,009B。sample監視には捕捉限界がありhard OS capではない。

model.rs SHA acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80、lock/許容差/元参照は不変。本工程からのCargo/default編集は0（作業中の別差分は次の最終確認注記）。共通coreや新Rust候補の変更がないためRustテスト・全7case再評価は追加実行していない。R1安定版累積1点未達/R2停止。保全・点検支援第一、自作モデルの産業/需要での実用性、Rustの学習/推論/optimizer再開の目的を維持。

需要2015/CARE test再評価・学習・下流編集・Git push・製品採用0。需要2014以前調整、同休業mean28、四季過小量/過大量非増加、観測のみ/欠測0分離、heartbeat PAUSED維持。SDK/Accelerate/dyld/own-process metadataはMac固有の証拠であり、Windows固有機能・OS依存suiteは未実行として分ける。

## 最終確認注記

全artifact/EvidenceStore、元source/SDK/model/lock pinsの確認は通過した。一方、全体git diff --checkはcrates/banto-ai/Cargo.toml末尾の空行を指摘してexit2。このmanifestは本工程では編集しておらず、source declaration時のsnapshotと現在のbytesが異なることを確認した。変更者や意図は推定せず、現在の変更をそのまま保護した。したがって本報告の「変更0」は本工程からの編集が0という意味であり、他作業を含めたworkspace全体が開始時と同じという意味ではない。docs限定のdiff --checkはexit0。

最初の最終検査recordsはfailedのまま保持し、この区別を保存したfresh最終検査はartifacts/rust-r1-once-final-check2-20261016、同-records、同-evidence。追加の数値演算/live read/命令読取りはない。
