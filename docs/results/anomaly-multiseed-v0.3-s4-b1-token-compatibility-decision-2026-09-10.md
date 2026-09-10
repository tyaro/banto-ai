# S4-B1 Windows互換性と制限トークン構成の判断

状態: **原因候補を具体化 / 方針判断待ち / token構成は未変更**。

## 判断する点

保護対象への書き込み禁止を必須条件として、Windows初期化との互換性を得るために
制限トークンの構成を見直すことを許容するか。

[今回の結果](anomaly-multiseed-v0.3-s4-b1-bcrypt-device-result-2026-09-10.md)では、bcryptのKsecDD open helperが
C0000022を返した経路を確認した。親から取得したKsecDDのDACLにはRC allow1200a9があり、
固定参照の要求100003に対してwrite mask0x2が不足する。
これは拒否と整合する観測であり、実AccessCheckや唯一の原因の証明ではない。

現在の作成・検証コードはrestricting SIDをRCだけに固定している。
引継書§6の「restricted tokenを弱める」変更の禁止に対し、互換性のためのSID追加は
許可範囲を広げうるため、既存条件のまま自動適用しない。

## 方針の比較

| 方針 | 得られるもの | 条件・限界 |
| --- | --- | --- |
| 互換性を得るため構成を見直す（推奨） | 現在のWindowsで起動と保護検証を両立する候補を作れる | SID追加はそのSIDを許可する他のobjectにも効きうる。保護対象外の権限が全く同じとは主張できない |
| RCのみを必須条件として維持 | 現行の権限構成をそのまま保つ | 今回の起動障害は未解決のまま。B1受入・本流統合へ進まない |

推奨は権限追加を無条件で採用することではなく、以下の条件で候補を検証する方針である。
KsecDDのOS全体ACL変更、DLL patch、デバイスhandleの親からの引渡しは候補に含めない。

## 見直しの範囲

- RCを残し、既存ACLに対応する非特権SIDのうち最小の追加候補を調べる。現時点で追加SIDは未選定。
  未分類2 ACEをpackage/logon等と推測しない。選定時には出所と権限範囲を確認する。
- DISABLE_MAX_PRIVILEGE、WRITE_RESTRICTED、非昇格、同一user/session/integrity、
  privileged groupのdeny-only、SeChangeNotifyPrivilege以外を残さない条件を維持する。
- source/runtime照合、固定child、非継承handle、protected DACL、資源上限、失敗証跡保持を維持する。
- 昇格・別account・通常Popen fallback・required testのskip/pass化・OSや既存artifactのACL変更を行わない。
- Everyone/user/Administrators/LocalSystemのような広いgrantを単に通す変更は自動採用しない。
  狭い候補が得られなければ、判明した影響を示して方針を再判断する。

制限トークンは通常SIDとrestricting SIDの双方のアクセス検査に依存する。
restricting SIDの追加は権限を狭める操作とは限らない。
[Microsoft Restricted Tokens](https://learn.microsoft.com/en-us/windows/win32/secauthz/restricted-tokens)。

## 候補を採用する前に必要な確認

1. 追加SIDの根拠、KsecDDを含む想定効果、他objectへ効く範囲、保持する条件を固定する。
2. 候補作成と実child token照合を同じ厳密なrecipeへ更新し、pure/fakeで意図しないSID・特権・identity変化を拒否する。
3. 独立レビューで権限の広がりと保護条件を確認し、保存したcandidateに対し既存上限内で限定nativeを検証する。
4. 起動成功だけでなく、read positive、control領域のwrite positive、frozen領域の全negative operation、
   parent DELETE_CHILD、rename/replace、teardown、証跡保持を満たすことを確認する。

frozen DACLにはEveryoneへのwrite系denyが先頭にあるが、この静的事実だけで候補の保護成功とはしない。
Windowsの実AccessCheckと実操作の双方が必要である。
Python3.12/3.14を含む既定のB1必須受入は未完了のまま保持する。

この判断は権限構成見直しの方針に対するものである。具体的なSIDとrecipe、検証範囲を固定し、
独立レビューを通す前に、変更tokenでchildを実行しない。本流統合・formal・B2・publisherの許可を含まない。
