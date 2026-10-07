# v0.3 親source callback・archive部品のCI保存照合（2026-10-07）

## 完了runとHEAD

| 対象 | 外部HEAD | run/attempt | 各minor試験数 | 3.12 / 3.14 / compare job ID |
| --- | --- | --- | ---: | --- |
| source callback | 9af4a965c345930a0ccc2d18417ca0a1fa7244cb | [37568898031](https://github.com/tyaro/banto-ai/actions/runs/37568898031) / 1 | 3,099 | 112622846623 / 112622846390 / 112633558044 |
| archive部品 | 1159b9ace9ea7e213033ecaa0ac0b9ee680f67b8 | [37570913852](https://github.com/tyaro/banto-ai/actions/runs/37570913852) / 1 | 3,118 | 112629094355 / 112629094481 / 112639149037 |

両runとも全3job success、各minor fail0/error0/skip237/source不変。run/attempt別jobs、2 journal、comparison/regression、3 job logをそれぞれ新専用rootへ保存した。外部HEAD/workflow/run/attemptを固定したlocal verifierの結果は保存remote regressionと全値一致し、共有29fixture・必須28試験/各minorを確認した。

workflow SHA-256は `1376641c6a394b2f4781bb0ceaa8acfa735f35dfa1799d8503300ba9268815e8`。各保存sourceのGit workflow blobも一致する。rawは `artifacts/ci-diagnostic-37568898031/` と `artifacts/ci-diagnostic-37570913852/`。各10 rawとsummary/candidate/result/runner summaryの計14 pinを索引へ固定した。完成済みCI37559835322等は反復していない。

## runner候補

| run | Python3.12 | Python3.14 | compare |
| --- | --- | --- | --- |
| 37568898031 | 20260927.320.1 | 20261004.327.1 | 20260927.320.1 |
| 37570913852 | 20261004.327.1 | 20260927.320.1 | 20261004.327.1 |

runner v2は正確なjob inventory、実log prefix/image宣言、各minor journalと固定HEAD、保存済み公式release/README metadata・Git blobを照合し、両runをconsistent_candidateと判定した。20261004.327.1の保存releaseはprerelease=true、外部候補pinも同値。VM digest未取得・候補未採択、正式許可falseを維持する。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| 37568898031 complete-summary | 2,570 | 86ff1882297057ec1d66256ec165adf94779815100d3dfabe96d505b3e7eafe0 |
| 37568898031 candidate-pins | 3,462 | 92e56fe7b0835b33ec4df791808b0f38efcc5a59443b7e2124a28f790c040ddf |
| 37568898031 runner result | 3,959 | 108105a3751b57806245618d5ddeffa8ab85f22cc5e6b91de3d9d1a84f50aa86 |
| 37568898031 ci-complete-index | 2,783 | 445b42f2b27ec8ab785d7cca52b10303d69be38541aba0f096f39a96ff96e84f |
| 37570913852 complete-summary | 2,576 | a8d321b5df2a411ece3ae2ae42c4e34d442a4619b695430df3425308aeae1164 |
| 37570913852 candidate-pins | 3,462 | 7cc6c83bec8540c1c0bacf9e65a9e0b94daede3da343bc90bc1b9e085ed8064d |
| 37570913852 runner result | 3,959 | 88674d2793694c4b07469b07134376509befc16aba8b197f96e08a8bbe5975cf |
| 37570913852 ci-complete-index | 2,783 | d6536ed588890031052066b643396086dac41a1bdec3a9ecebd7f3c3628585d1 |

## 次の単位

actor code9c49c4aのCI37572914427も完了し、以下へ保存した。残るcallback code e4cb23aのCI37576149693は未完了。先行CIを新codeや最終revisionへ読み替えない。[限定親Git native](anomaly-multiseed-v0.3-parent-git-blob-budget-native-2026-10-07.md)はclean d57326e/code9c49c4aで終了済みだが、全経路最終受入は未了。

正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0、登録holdout観測未読。[正式5残件](anomaly-multiseed-v0.3-preformal-evidence-index-2026-10-07.md)を維持し、doc-only追補の追加CIは抑止する。

## 親blob actor CIの完了追補

[CI37572914427](https://github.com/tyaro/banto-ai/actions/runs/37572914427)、HEAD `9c49c4a9c15e7f754572eb1add8b834203f1100d`、attempt1。Python3.12 job112635338844・3.14 job112635338513・compare112645834890は全success。各minor3,131件、fail0/error0/skip237/source不変。workflow pinは上記と同一、10 rawの保存と外部HEAD/run/attempt固定のlocal回帰は保存remoteと全値一致、共有29fixture/必須28試験もpass。

全3jobのimageは20261004.327.1。保存済み公式release/README metadata/Git blob、外部prerelease=trueと各journal/logをrunner v2へ結び、consistent_candidate。candidate入力には使用した単一imageの公式rawだけを含めた。digest未取得・候補未採択・formal falseを保持する。

rawは `artifacts/ci-diagnostic-37572914427/`。10 complete raw＋summary/candidate/result/runner summaryの14 pinを固定した。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| complete-summary.json | 2,578 | 69bcb4001e8feb6cb5e16ce0109b2d0a7a11e66be0d8e49c5f4d62d869e053f3 |
| 37572914427-candidate-pins.json | 2,565 | 27ab352cefc0b581203616dbae7f29df02088761b76f109d77d652ada014d479 |
| 37572914427-result.json | 3,062 | 79d608fe737facea23d7903cca91a5815208f72e9da6273c5e1fc48c84d073f5 |
| ci-complete-index.json | 2,783 | 0f557afce46d27d5abcc758dea43e5cfec0ad9934bca4458ecc1f25a683acf94 |

限定親nativeはdocs HEAD d57326e/code9c49c4aであり、このCIはcode9c49c4a。選択sourceの同code証拠で、最終凍結same-revisionの全7役・正式同形経路の受入ではない。callback code e4cb23aへのnative証明でもない。旧raw/pin/失敗を保全し、全7役と親138Jobは反復していない。
