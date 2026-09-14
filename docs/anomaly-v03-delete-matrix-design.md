# S4 B2: fresh empty-file deletion matrix

Date: 2026-09-14. Engineering experiment only; acceptance remains `not_completed`.

The preceding [peer acquisition trial](results/anomaly-multiseed-v0.3-s4-b2-directory-peer-2026-09-14.md) acquired DELETE_CHILD access despite a retained directory handle sharing READ only. This experiment tests actual DeleteFileW requests against four new empty files, separating creation-time ACL assignments from child sharing settings.

## Fixed cases

| Case | Parent DELETE_CHILD | Child DELETE | Child share |
| --- | --- | --- | --- |
| file-permission | explicit deny | allow | READ, WRITE, DELETE (7) |
| parent-permission | allow | explicit deny | READ, WRITE, DELETE (7) |
| sharing-block | allow | explicit deny | READ, WRITE (3) |
| both-denied | explicit deny | explicit deny | READ, WRITE, DELETE (7) |

Each case is a sibling directory beneath a new `attempt-1`, with one new `empty.bin`. No enclosing source-fixture directory is created or retained. A protected creation-time DACL contains an optional Everyone DENY ACE for DELETE_CHILD (0x40) on the parent or DELETE (0x10000) on the child, then full-control allow ACEs for the current user, SYSTEM and Administrators. Exact same-handle ACL readback is required. There is no ACL mutation, AccessCheck, impersonation, restricted token or additional peer process.

Case directories use CreateDirectory2W with access 0x1600a7, share READ=1, redirect rejection and noninheritance. Each child uses CREATE_NEW, access 0x120081 (no DELETE or WRITE_DAC), noninheritance, OPEN_REPARSE_POINT and its fixed share mask. Standard information from the retained child handle must establish a non-directory, one link, zero allocation, zero length and no delete-pending state before an empty-content pin is accepted. Identity and security are read using the retained handles; case paths are not reopened for verification.

## Operation and interpretation

DeleteFileW is called once by path per case under the same worker's primary token. The first case is a positive control and must succeed. Failure responses capture GetLastError immediately; only errors 5 and 32 are classified. Other cases may be accepted or return a classified refusal, and the result is recorded rather than inferred from an ACL inspection.

After a classified response, read FileIdInfo, security and FILE_STANDARD_INFO using the retained child handle. Identity and descriptor must remain unchanged; DeletePending must be true for success and false for refusal. Standard information is Win64 size 24 with one-byte BOOLEAN fields at offsets 20 and 21. Close the child, release its descriptor, then close the case directory. Completed cases close before evidence persistence. Ancestors and private evidence leases close last.

This records a deletion request, delete-pending observation and confirmed handle closure. It does not inspect the path after close or prove namespace absence, absence of external handles, use of a retained parent capability, independent-process isolation or formal acceptance. Microsoft documents the file DELETE or parent DELETE_CHILD permission route, sharing constraints and last-handle deletion behavior in [DeleteFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-deletefilew); the observed state is described in [FILE_STANDARD_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_standard_info).

## Failure and resource boundaries

An unknown deletion result retains the child, case root, native path input and ancestors until worker exit, skips subsequent reads/cases/evidence, and never retries the request. Unknown file acquisition, descriptor release or child close likewise retains the parent and ancestors. A known request followed by a read failure closes known resources and reports failure. Primary error identity and later resource-stop signals survive cleanup; finish is at most once and reentry latches a failure.

Lifetime decisions use backend state directly instead of allocating reporting snapshots. If that state query fails, retain conservatively, preserve the first error and latch a later resource stop. A started root whose close is not confirmed also requires worker exit. These failures are checked before the caller decides whether to close ancestors.

The batch permits one worker attempt containing at most four fresh cases. It uses Python 3.14.0 x64, a reviewed clean detached checkout and recorded Git/source hashes. Limits: 40 seconds internally, 45 seconds externally, five seconds for forced exit confirmation, 256 resource checkpoints, 256 MiB private memory, 384 MiB working set, and at least 2 GiB available RAM/disk. Evidence is capped at 16 KiB, worker report at 128 KiB, combined supervisor output at 192 KiB. The supervisor only terminates its own worker. No old source fixtures, completed batches or other processes are operated on; no retry or cleanup is authorized by this batch.

Record OS build, UBR and boot as engineering context following the user's Windows Update relaxation. This does not change the formal environment pin. No publication, push, merge, CI change or protected commit permission follows from this experiment.
