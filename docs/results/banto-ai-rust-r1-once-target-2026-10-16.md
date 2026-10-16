# Rust R1 — 固定call target64bytesの確認（2026-10-16）

**固定target0x1880e1a60の最大64bytesを範囲・権限確認後に読み、同じ64bytesの再照合も一致した。先頭16bytesはADRP→ADD→LDR→BRAAの間接転送stubで、pointer slot0x1e7ff0db8を導いた。そのslotや分岐先は読まず、公開API identity/query/train経路は未確定のまま工程を閉じた。** ターゲット実行・数値演算・full model・学習0。元warmの-1 gate失敗を保持。R1安定版累積1点未達/R2停止。

## 事前条件・SDK型の証明

[固定した64byte条件](../../examples/configs/rust-r1-once-call-target-admission-20261016.json)と[具体的な実行条件](../../examples/configs/rust-r1-once-target-execution-20261016.json)に従った。fresh declarationでsource、SDK Mach宣言、元BL selectors、libtorch/model/lock、開始時のCargo manifest、旧22rootsのclosureをpin。旧scopeの失敗7rootsもstatusを変えず保持した。元六関数codeは再読取りしていない。

SDK vm_region.hのpack4をPython側で推測するだけにせず、SDKをincludeした小さなC helperをpinしたclangでcompileした。C helperはsizeof/offsetof/constantsを出力するだけでMach APIやtargetを呼ばない。struct vm_region_submap_info_64は84bytes、V3 count21、全23fieldのoffset、関数引数用の各整数型size、READ1/EXECUTE4/KERN_SUCCESS0をctypes定義と照合した。全て一致、compile/helper exit0。SDK本文とhash、C source/binary/commands/stdioを保存した。

loaded libBLASのUUID31104d4f4a7e3fa79e1855937b2011f2、元libtorch_cpu SHA、torch gitと同一OS情報を検証。platformはJSONの表現へ正規化して比較し、前工程のtuple/list形式問題を繰り返していない。

## own-task mappingと64byte読取り

mach_vm_region_recurseはmach_task_selfだけに使った。要求addressは毎回同じtargetへ戻し、submapのときだけdepthを増やす上限16の手順を固定した。実際は2queryで終わった。

| depth | 結果 | 保護属性 | 次の処理 |
| --- | --- | --- | --- |
| 0 | targetを含むsubmap、returned count21 | READ | 同じtargetでdepth1へ |
| 1 | targetを含むleaf、returned count21 | READ+EXECUTE | 全64bytesの境界を確認 |

leaf/effective boundsは[6786596864, 6786842624)、target runtime addressは6786636384。親submapとの共通範囲にもtarget..target+64が収まることを確認した。上位submapのREAD属性だけでleafを判断せず、返却されたleafのREAD+EXECUTEを確認した。region探査で別addressへ移動していない。

mach_vm_read_overwriteで64bytesを一度読み、同じ64bytesだけ一度再照合した。両方OS成功/返却64bytes、bytes不変。unique64bytes、SHA f4ef8f3dda5a91c4e5538c3ac456284d1a7e905875906315a53ec7d3acc8c79a。これ以外のlive executable read0、pointer/data/TLS/config read0。Mach-O header/load commands/function-startsはlibrary identity用の既定上限内metadataとして分けて保存した。

## 命令から分かること

pinしたllvm-objdumpで非実行ELF containerの.textだけをdisassemble。これはMach-O原fileでも実行用binaryでもない。対象の先頭4命令は次の通り。

| image virtual PC | 命令 | 今回の解釈 |
| --- | --- | --- |
| 0x1880e1a60 | ADRP X17, 0x1e7ff0000 | PC relative page address |
| 0x1880e1a64 | ADD X17, X17, #0xdb8 | slot0x1e7ff0db8 |
| 0x1880e1a68 | LDR X16, [X17] | pointerをload |
| 0x1880e1a6c | BRAA X16, X17 | load値への認証付き間接transfer |

元machine wordsはf02ff871/9136e231/f9400230/d71f0a11。ADRPのsigned21bit page offsetとADD immediateをbytesから独立decodeし、listingとslotを照合した。これは行列積や初期化処理本体ではなくtransfer stub。関数全体の境界は仮定していない。残り48bytesにも似た並びは見えるが、隣のentryやslotを追っていない。

dladdr0だった位置に実際の転送命令があることは確認できたが、転送先の値や公開dispatch_onceとのidentityは依然未観測。元の直接API不一致を公開APIの破損や初期化失敗と解釈しない。元once値52638546を-1へ読み替えず、数値許容差も変えていない。

## 次工程

[一つの8byte slotだけを扱う次条件](../../examples/configs/rust-r1-once-slot-admission-20261016.json)を保存した。slotは今回の保存命令から導いた0x1e7ff0db8だけ。新たなfresh declarationとown-taskのreadable/bounds確認が必要。認証付きpointerの表現はSDKに根拠のある方法だけを使い、上位bitのmaskを推測しない。表現処理を証明できなければraw bytesと不明点を保持する。

次unitでもpointerの実行・認証・callee codeの読取り・BLAS/tensor/query/initializerはしない。公開entryとの比較はmetadataとして限定し、identityが得られるまでquery/train kernelを確定しない。今回のunitではslot内容/分岐先読取り0で停止し、この次工程はまだ実行していない。

## 資源・保護・OS分離

新規6rootsは全complete。全source/SDK/commands/stdio/exit/state/closure、layout proof、mapping全返答、raw64bytesと再照合、disassembly、派生slot、文書前後はartifacts/rust-r1-once-target-results-20261016と同-evidence。publication自身のstdio/exit/stateは同-records。

親900/子870秒、physical footprintとpeakRSS各2GiB、cache+target1.5GiB、元artifact/EvidenceStore/stdio上限を維持。今回最大監視込みfootprint 183,240,264B、RSS系 243,007,488B、cache+target 1,037,488,009B。sample監視でありhard OS capではない。C helper/clang/linkerも同一process group監視下。

model.rs SHA acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80、lock/許容差/参照と開始時source pins不変。Cargo/default/製品側編集0。開始時から残るCargo.toml末尾空行により全体diff --checkはexit2、docs限定はexit0。manifestは開始時hash 208d25a943d172bfed88da59714f450d899c19e4d09e8f86988d68b92b9529f6のまま保持し、本工程で修正していない。Rust core変更がないため既存Rustテスト/固定7caseを反復していない。

保全・点検支援第一、自作モデルの産業/需要での実用性、Rustの学習/推論/optimizer再開目的を維持。R1累積1点未達/R2停止、需要2015/CARE test再評価・学習・下流編集・Git push・製品採用0。需要2014以前調整、同休業mean28、四季過小/過大非増加、観測のみ/欠測0分離、heartbeat PAUSEDを維持。

SDK/Mach mapping/Accelerate/PAC transferの今回の証拠はMac固有。Windows固有機能・OS依存suiteは未実行で、共通RustモデルやWindows上での数値成立はこの観測で認定していない。
