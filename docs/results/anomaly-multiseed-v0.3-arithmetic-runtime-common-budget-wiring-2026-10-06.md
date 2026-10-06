# v0.3 算術runtime在庫の共通予算接続（2026-10-06）

code保存点 `dfa61e8350c78289fca1170f82f1559a18391710`。焦点9 module・固有109件は157.091秒、fail0/error0/skip0、試験対象source/scientific pinの前後一致でpass。repository safetyもpass。

analysis/audit の外部pin付きruntime候補を、2役bridge・連続文書・保存control公開・生成から公開までの共通callerへ渡す接続を追加した。今回の変更はfixture試験の対象。新接続を使うnative全工程は未実施で、旧clean `af3e7a5` の2役native a3、旧clean `02d567f` の共通e04成功とは分ける。

正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0、登録holdout観測payload未読を維持する。追加agent0、新しいengineering観測評価0、正式実行0。科学計画・registryと子/親の既存予算上限を維持する。

## 接続と失敗時の扱い

各入口に任意の `arithmetic_runtime_profiles` を追加した。両役それぞれの `raw: bytes` と `expected_pin: {bytes, sha256}` をcallerが供給する。候補作成・Git由来の確認はcallerの責任で、旧a3のfull revision/pinを新HEADへ流用しない。

新root作成前に、両roleの存在、外部raw pin、role/operation/source root/full revision、候補scopeを検証し、callerの可変pin dictをコピーして保持する。共有sampler開始後には現runtime tuple、選択済みGit source pinとの一致を両役とも確認する。両profileをexclusive保存し、実算術のownerと親verifierへ各役のpinを渡す。

実childの前後stdlib・loaded inventory照合、元handle identityとの一致、exit/reap、終了後disk照合は既存の任意observerを使う。profile保存、child側照合、親照合、文書/公開後のprofile・stdout・前後sidecar raw再照合は既存の共有時計内に入る。profileの準備自体は時計外で、nativeの測定時間を今回は提示しない。

公開側が `measured` を返しても、在庫照合済みの厳密な `True` とcallerが保持した両profile pinが揃わなければ、外側resultは `failed` として保存する。partial保存や停止時の照合flagはfalseのまま。両算術役の照合後に後段が失敗した場合は、その部分照合と全工程failedをそれぞれ保持する。終端再照合の例外が全工程の成功へ残らない順序にした。

対象はanalysis/auditのみ。producer・初期reader・保存reader・writer・fresh reader、外部Git/helperの在庫、異常子孫回収、全runtime閉包・正式経路・独立S6を完了した証拠ではない。CLIの旧引数は同じで、新候補はPython APIから明示的に渡す。

## 試験と保存

新試験は両役欠落/差替え、古いrevision、caller pin変異、第二roleのsource不一致、runtime tuple不一致、共有stop、exclusive write失敗、実算術callerの両pin伝播、親verifier失敗、終端sidecar変更を扱う。公開側の証拠欠落・pin差替えを拒否し、一致するfixtureでは共有工程の成功と正式flag falseを保持する。

最終まとめ試験は109件すべてpass。新規13件を含み、既存profile/bridge/連続文書/保存control/観測subset/公開経路も対象にした。試験の正確なID・時間・source/log pinは [focused.json](../../artifacts/preformal-runtime-composition-20261006-prep/focused.json)、生logは [focused.log](../../artifacts/preformal-runtime-composition-20261006-prep/focused.log) に保存。fixturesとmock ownerによる接続試験で、実native受入とは分ける。最初のouter試験ではmock readerの必須 `verified_evaluations` 欄を補い、接続先の拒否まで実際に到達するよう修正した。55件の先行確認と35件の接続確認は最終109件へ含まれるため加算しない。

| 保存raw | bytes | SHA256 |
| --- | ---: | --- |
| focused.json | 18,377 | `7bf66d186acb4a265e36569461b41aee14a9d07b7e06a501ef4914e7ac8ef097` |
| focused.log | 22,754 | `4f6a4c92f2d24696b0deaf18fccf530fd4ec8092c833a802fdae7b91c2be2ba9` |
| focused.py | 3,128 | `7ab764268bd6ec0f8971d12bc400df1b54efae15593fd766b54c2dae89affbbc` |
| CI37431372011 composition-status | 4,683 | `f6213cda36ecc262d74e994e6cd2de9e3da6606fe28f487dabbb21f65aae35fa` |
| CI37431372011 complete-summary | 2,830 | `b254a2557a73c53880822f7b3e11a0fb5ee8382d8ea92f0936045b68a73a8014` |

## CIと次の残件

旧算術nativeと同code `af3e7a598c5fe372a5cb9a5a96ddbcefe4f54f2e` の [CI37431372011](https://github.com/tyaro/banto-ai/actions/runs/37431372011) は**全3job成功、両minor各3,013件・fail0/error0/skip237、共有29fixture/必須28試験pass**。run/jobs原metadata・両journal・比較/回帰・3job log・ローカルverifier出力、計10完了rawと先行2 partialを保存し、12 pinを再照合した。ローカルverifier結果はremote回帰結果と一致した。[complete-summary](../../artifacts/ci-diagnostic-37431372011/complete-summary.json)へ集約。runner log表示は3jobともUbuntu24.04 / `20260927.320.1`、digest未取得・正式採択false。

進行中だった[別名status raw](../../artifacts/ci-diagnostic-37431372011/composition-status-20261006.json)と初回snapshotは履歴として保全。集約helper初版のrunner version抽出失敗も `save-complete.py` / `save-complete-failed.json` として保持し、別 `save-complete-v2.py` で隣接するImage/Version行を照合した。CIの失敗ではない。この成功は`af3e7a5`の結果で、後続`dfa61e8`の共通接続と正式最終受入へ代用しない。

次は残るproducer/3 reader/writerの実境界への期待runtime inventory接続と、今回保存点のCI確認を進める。全役を接続した後、最終clean full HEADの候補を準備し、必要な限定native共通工程を一回測る。旧e04/a3や失敗rootは保全し、長い全工程を自動反復しない。

正式開始までの残りは [受入範囲案v3](../anomaly-v03-s4-acceptance-scope-draft-v3.md)の5群：運用契約採択、正式入力/consumer受入、全使用source/runtime・終了/回収、最終revisionのLinux/Windows・dev8/smoke2と独立受入、全工程予算・smoke全容量の2倍。今回の候補実装を正式受入に読み替えない。
