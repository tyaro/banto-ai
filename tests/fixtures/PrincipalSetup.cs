// Engineering environment preparation only. No logon, worker, publisher or cleanup.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Text;
using System.Threading;

[assembly: DefaultDllImportSearchPaths(DllImportSearchPath.System32)]
namespace Banto.PrincipalSetup
{
    public enum Phase
    {
        Preflight = 1, HoldAncestors, CheckAbsent, CreateRoot, InspectInitialRoot,
        CreateDisabledAccount, InspectAccount, AddUsersGroup, InspectGroups,
        SetRootPolicy, InspectFinalRoot, CreateReceipt, WriteReceipt, FlushReceipt,
        CloseReceipt, CloseRoot, CloseProgramData, CloseVolume, ClosePeerToken,
        CloseLinkedToken, CloseAdminToken, StopWatchdog
    }
    public sealed class FailureState
    {
        public InspectionStep InspectionStep;
        public byte PolicyDifference;
        public bool ReleaseFailed;
        public uint ReleaseError;
        public readonly Exception ReleaseStop = new InvalidOperationException("native memory release failed");
    }
    public enum InspectionStep
    {
        None = 0, Budget, VolumePin, ParentPin, VolumePeerAccess, ParentPeerAccess,
        RootIdentity, ActualPolicy, ExpectedPolicy, CompareDetails, ExactPolicyComparison
    }
    public static class InspectionFailure
    {
        public const int Marker = 0x20000000;
        // This refines only phase 5's otherwise-unknown detail. No exception text or new OS calls.
        public static int Encode(Phase phase, int detail, Exception error, FailureState state)
        {
            int release = state.ReleaseFailed ? 0x40000000 : 0;
            if (phase != Phase.InspectInitialRoot || detail != 65535 || state.InspectionStep == InspectionStep.None)
                return ((int)phase << 16) | detail | release;
            int kind = Object.ReferenceEquals(error, state.ReleaseStop) ? 4 :
                error is Win32Exception ? 3 : error is OutOfMemoryException ? 2 :
                error is InvalidOperationException ? 1 : 0;
            return Marker | ((int)phase << 16) | (kind << 13) |
                ((int)state.InspectionStep << 8) | state.PolicyDifference | release;
        }
        public static byte ComparePolicy(string actual, string expected)
        {
            RawSecurityDescriptor a = new RawSecurityDescriptor(actual), e = new RawSecurityDescriptor(expected);
            int difference = 0;
            AccessControlSections[] sections = { AccessControlSections.Owner, AccessControlSections.Group,
                AccessControlSections.Access, AccessControlSections.Audit };
            for (int i = 0; i < sections.Length; i++)
                if (a.GetSddlForm(sections[i]) != e.GetSddlForm(sections[i])) difference |= 1 << i;
            // GetSddlForm(Audit) omits mandatory-label ACEs on this runtime.
            // Compare the raw ACL bytes as well so label SID/mask/order cannot disappear.
            if (!SameAcl(a.DiscretionaryAcl, e.DiscretionaryAcl)) difference |= 4;
            if (!SameAcl(a.SystemAcl, e.SystemAcl)) difference |= 8;
            ControlFlags changed = a.ControlFlags ^ e.ControlFlags;
            if ((changed & ControlFlags.DiscretionaryAclProtected) != 0) difference |= 16;
            if ((changed & ControlFlags.SystemAclProtected) != 0) difference |= 32;
            if ((changed & (ControlFlags.DiscretionaryAclAutoInherited | ControlFlags.DiscretionaryAclAutoInheritRequired)) != 0) difference |= 64;
            if ((changed & (ControlFlags.SystemAclAutoInherited | ControlFlags.SystemAclAutoInheritRequired)) != 0) difference |= 128;
            return (byte)difference;
        }
        private static bool SameAcl(RawAcl a, RawAcl b)
        {
            if (a == null || b == null) return a == b;
            if (a.BinaryLength != b.BinaryLength) return false;
            byte[] first = new byte[a.BinaryLength], second = new byte[b.BinaryLength];
            a.GetBinaryForm(first, 0); b.GetBinaryForm(second, 0);
            for (int i = 0; i < first.Length; i++) if (first[i] != second[i]) return false;
            return true;
        }
    }
    public interface IBackend { FailureState Failure { get; } void Execute(Phase phase); }
    public sealed class Sequence
    {
        private bool started;
        public Phase Current { get; private set; }
        public int Run(IBackend backend)
        {
            if (started) throw new InvalidOperationException("setup cannot be reused");
            started = true;
            FailureState failure = backend.Failure; // Obtain preallocated state before any operation.
            try
            {
                foreach (Phase phase in Enum.GetValues(typeof(Phase)))
                {
                    Current = phase;
                    backend.Execute(phase);
                }
                return 0;
            }
            catch (Exception error)
            {
                // No further backend calls, retries, compensation or handle closes.
                // Native raw handles and buffers stay rooted until process exit.
                Win32Exception native = error as Win32Exception;
                int detail = Object.ReferenceEquals(error, failure.ReleaseStop) ? unchecked((int)failure.ReleaseError) :
                    native == null ? 65535 : native.NativeErrorCode;
                if (detail <= 0 || detail > 65534) detail = 65535;
                return InspectionFailure.Encode(Current, detail, error, failure);
            }
        }
    }
    public static class ReleaseGuard
    {
        public static void Free(FailureState state, Func<uint> release)
        { Run(state, delegate { return 0; }, release); }
        // Single release; retain the original operation failure if release also fails.
        public static T Run<T>(FailureState state, Func<T> body, Func<uint> release)
        {
            Exception first = null; T result = default(T);
            try { result = body(); } catch (Exception error) { first = error; }
            try
            {
                uint status = release();
                if (status != 0)
                {
                    if (!state.ReleaseFailed) state.ReleaseError = status;
                    state.ReleaseFailed = true;
                    if (first == null) first = state.ReleaseStop;
                }
            }
            catch (Exception error) { state.ReleaseFailed = true; if (first == null) first = error; }
            // Preserve the exception object/code, without Exception.Data or Capture allocations.
            if (first != null) throw first;
            return result;
        }
    }
    public interface IPrivilegeBackend
    {
        bool ReadEnabled();
        void SetEnabled(bool enabled);
    }
    public sealed class PrivilegeLease
    {
        private readonly IPrivilegeBackend backend;
        private bool started, active, original;
        public PrivilegeLease(IPrivilegeBackend backend) { this.backend = backend; }
        public void Enable()
        {
            Policy.Require(!started, "privilege lease cannot be reused");
            started = true;
            original = backend.ReadEnabled(); // Missing privilege must fail before adjustment.
            if (!original) backend.SetEnabled(true);
            Policy.Require(backend.ReadEnabled(), "privilege enable not confirmed");
            active = true;
        }
        public void Restore()
        {
            Policy.Require(active, "privilege lease not active");
            active = false; // A failed restoration is terminal, never retried.
            if (!original) backend.SetEnabled(false);
            Policy.Require(backend.ReadEnabled() == original, "privilege restore not confirmed");
        }
        public static void RequireAdjusted(bool succeeded, int error)
        {
            // TRUE with ERROR_NOT_ALL_ASSIGNED is a failure too.
            if (!succeeded || error != 0) throw new Win32Exception(error > 0 ? error : 65535);
        }
        public static bool ReadEnabled(byte[] bytes, Native.LUID target)
        {
            Policy.Require(bytes != null && bytes.Length >= 4 && bytes.Length <= 4096, "privilege buffer bound");
            uint count = BitConverter.ToUInt32(bytes, 0);
            Policy.Require(count <= (bytes.Length - 4) / 12 && 4 + count * 12 == bytes.Length, "privilege ABI");
            bool found = false, enabled = false;
            for (int index = 0; index < count; index++)
            {
                int offset = 4 + index * 12;
                if (BitConverter.ToUInt32(bytes, offset) != target.Low || BitConverter.ToInt32(bytes, offset + 4) != target.High) continue;
                Policy.Require(!found, "duplicate privilege response");
                uint attributes = BitConverter.ToUInt32(bytes, offset + 8);
                Policy.Require((attributes & 4) == 0, "removed privilege response");
                found = true; enabled = (attributes & 2) != 0;
            }
            if (!found) throw new Win32Exception(1314);
            return enabled;
        }
    }
    // This adapter borrows the one owned B process token; it never closes or replaces it.
    public sealed class NativeSecurityPrivilege : IPrivilegeBackend
    {
        private readonly IntPtr token;
        private Native.LUID luid;
        public NativeSecurityPrivilege(IntPtr token)
        {
            Policy.Require(token != IntPtr.Zero && token != new IntPtr(-1), "privilege token authority");
            this.token = token;
            if (!Native.LookupPrivilegeValueW(null, "SeSecurityPrivilege", out luid))
                throw new Win32Exception(Marshal.GetLastWin32Error());
        }
        public bool ReadEnabled()
        {
            IntPtr buffer = Marshal.AllocHGlobal(4096);
            try
            {
                uint needed;
                if (!Native.GetTokenInformation(token, 3, buffer, 4096, out needed))
                    throw new Win32Exception(Marshal.GetLastWin32Error());
                Policy.Require(needed >= 4 && needed <= 4096, "privilege response bound");
                byte[] bytes = new byte[needed]; Marshal.Copy(buffer, bytes, 0, bytes.Length);
                return PrivilegeLease.ReadEnabled(bytes, luid);
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }
        public void SetEnabled(bool enabled)
        {
            Native.TOKEN_PRIVILEGES_ONE state = new Native.TOKEN_PRIVILEGES_ONE();
            state.Count = 1; state.Luid = luid; state.Attributes = enabled ? 2U : 0U;
            bool succeeded = Native.AdjustTokenPrivileges(token, false, ref state, 0, IntPtr.Zero, IntPtr.Zero);
            int error = Marshal.GetLastWin32Error();
            PrivilegeLease.RequireAdjusted(succeeded, error);
        }
    }
    public static class Policy
    {
        public const string Account = "BantoS4Publisher";
        public const string Root = @"C:\ProgramData\BantoAI-S4B2-principal-20260916g";
        public const string Peer = "S-1-5-21-2169670816-255940906-2713565042-1001";
        public const string Users = "S-1-5-32-545";
        public const uint DisabledNormalFlags = 0x203;
        public const uint RootAccess = 0x1600a7;
        public const uint DangerousAncestorAccess = 0x000d0040; // DELETE, WDAC, WOWNER, DELETE_CHILD
        public static string Descriptor(string publisher)
        {
            if (publisher != null)
            {
                SecurityIdentifier sid = new SecurityIdentifier(publisher);
                if (!sid.IsAccountSid() || publisher == Peer) throw new InvalidOperationException("publisher SID");
            }
            return "O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;0x1200a9;;;" + Peer + ")" +
                (publisher == null ? "" : "(A;;0x1200a9;;;" + publisher + ")") + "S:P(ML;;NW;;;ME)";
        }
        public static void Require(bool value, string reason)
        { if (!value) throw new InvalidOperationException(reason); }
    }
    public static class Entry
    {
        private static NativeBackend live;
        public static int Run()
        {
            // Caller must immediately exit with the returned status, including failures.
            live = new NativeBackend();
            return new Sequence().Run(live);
        }
    }
    public sealed class NativeBackend : IBackend
    {
        private readonly FailureState failure = new FailureState();
        public FailureState Failure { get { return failure; } }
        private IntPtr volume, parent, root, receipt, adminToken, linkedToken, peerToken;
        private IntPtr initialSd, finalSd;
        private PrivilegeLease securityPrivilege;
        private string volumePin, parentPin, rootPin, publisher, usersName, finalPolicy;
        private byte[] receiptBytes;
        private readonly ManualResetEvent stopped = new ManualResetEvent(false);
        private readonly Stopwatch elapsed = Stopwatch.StartNew();
        private Thread watchdog;
        private long peakPrivate, peakWorking, minimumRam = long.MaxValue, minimumDisk = long.MaxValue;

        public void Execute(Phase phase)
        {
            failure.InspectionStep = phase == Phase.InspectInitialRoot ? InspectionStep.Budget : InspectionStep.None;
            failure.PolicyDifference = 0;
            if (phase != Phase.Preflight) Budget();
            if (phase >= Phase.CheckAbsent && phase <= Phase.CloseRoot) CheckAncestors();
            switch (phase)
            {
                case Phase.Preflight: Preflight(); break;
                case Phase.HoldAncestors:
                    volume = OpenDirectory(@"C:\"); volumePin = Pin(volume);
                    parent = OpenDirectory(@"C:\ProgramData"); parentPin = Pin(parent);
                    CheckPeerParent(volume); CheckPeerParent(parent); break;
                case Phase.CheckAbsent: CheckAbsent(); break;
                case Phase.CreateRoot:
                    initialSd = Parse(Policy.Descriptor(null), failure);
                    Native.SA sa = new Native.SA(initialSd);
                    root = Native.CreateDirectory2W(Policy.Root, Policy.RootAccess, 1, 1, ref sa);
                    ValidHandle(root); break;
                case Phase.InspectInitialRoot:
                    MarkInspection(InspectionStep.RootIdentity);
                    rootPin = Identity(root); VerifyPolicy(root, Policy.Descriptor(null)); break;
                case Phase.CreateDisabledAccount: CreateAccount(); break;
                case Phase.InspectAccount: InspectAccount(); break;
                case Phase.AddUsersGroup: AddUsers(); break;
                case Phase.InspectGroups: InspectGroups(); break;
                case Phase.SetRootPolicy:
                    finalPolicy = Policy.Descriptor(publisher); finalSd = Parse(finalPolicy, failure);
                    bool present, defaulted; IntPtr acl;
                    Check(Native.GetSecurityDescriptorDacl(finalSd, out present, out acl, out defaulted));
                    Policy.Require(present && acl != IntPtr.Zero && !defaulted, "DACL");
                    Status(Native.SetSecurityInfo(root, 1, 0x80000004, IntPtr.Zero, IntPtr.Zero, acl, IntPtr.Zero)); break;
                case Phase.InspectFinalRoot:
                    Policy.Require(Identity(root) == rootPin, "root identity");
                    VerifyPolicy(root, finalPolicy); InspectAccount(); InspectGroups(); break;
                case Phase.CreateReceipt:
                    receiptBytes = Receipt();
                    Native.SA childSa = new Native.SA(finalSd);
                    receipt = Native.CreateFileW(Policy.Root + @"\bootstrap-result.json", 0x40000000, 1,
                        ref childSa, 1, 0x00200000, IntPtr.Zero);
                    ValidHandle(receipt); VerifyNonInherit(receipt); break;
                case Phase.WriteReceipt:
                    uint written; Check(Native.WriteFile(receipt, receiptBytes, (uint)receiptBytes.Length, out written, IntPtr.Zero));
                    Policy.Require(written == receiptBytes.Length, "short receipt write"); break;
                case Phase.FlushReceipt: Check(Native.FlushFileBuffers(receipt)); break;
                case Phase.CloseReceipt: Close(ref receipt); break;
                case Phase.CloseRoot: Close(ref root); break;
                case Phase.CloseProgramData: Close(ref parent); break;
                case Phase.CloseVolume: Close(ref volume); break;
                case Phase.ClosePeerToken: Close(ref peerToken); break;
                case Phase.CloseLinkedToken: Close(ref linkedToken); break;
                case Phase.CloseAdminToken:
                    securityPrivilege.Restore(); Close(ref adminToken); break;
                case Phase.StopWatchdog:
                    // These allocated descriptors are not file ownership authorities.
                    Free(ref finalSd); Free(ref initialSd);
                    stopped.Set(); Policy.Require(watchdog.Join(1500), "watchdog join"); break;
                default: throw new InvalidOperationException("phase");
            }
        }
        private void Preflight()
        {
            Policy.Require(Environment.Is64BitProcess && Environment.OSVersion.Platform == PlatformID.Win32NT, "Win64");
            using (WindowsIdentity identity = WindowsIdentity.GetCurrent())
                Policy.Require(new WindowsPrincipal(identity).IsInRole(WindowsBuiltInRole.Administrator), "elevated admin required");
            // A self-terminating watchdog covers blocking SAM/file APIs. U need not hold PROCESS_TERMINATE on B.
            Budget();
            watchdog = new Thread(delegate()
            {
                try { while (!stopped.WaitOne(500)) Budget(); }
                catch { Environment.Exit(80); }
            });
            watchdog.IsBackground = true; watchdog.Start();
            Check(Native.OpenProcessToken(Native.GetCurrentProcess(), 0x002a, out adminToken)); // QUERY, DUPLICATE, ADJUST_PRIVILEGES.
            IntPtr buffer = Marshal.AllocHGlobal(64);
            try
            {
                uint size;
                Check(Native.GetTokenInformation(adminToken, 19, buffer, (uint)IntPtr.Size, out size));
                Policy.Require(size == IntPtr.Size, "linked token ABI");
                linkedToken = Marshal.ReadIntPtr(buffer); ValidHandle(linkedToken);
                using (WindowsIdentity identity = new WindowsIdentity(linkedToken))
                    Policy.Require(identity.User.Value == Policy.Peer, "UAC must link to expected ordinary user");
                Check(Native.GetTokenInformation(linkedToken, 20, buffer, 4, out size));
                Policy.Require(size == 4 && Marshal.ReadInt32(buffer) == 0, "peer must be unelevated");
                Check(Native.DuplicateToken(linkedToken, 1, out peerToken)); // SecurityIdentification: AccessCheck only.
                VerifyNonInherit(adminToken); VerifyNonInherit(linkedToken); VerifyNonInherit(peerToken);
            }
            finally { Marshal.FreeHGlobal(buffer); }
            Policy.Require(File.Exists(@"C:\Python314\python.exe"), "existing runtime absent");
            securityPrivilege = new PrivilegeLease(new NativeSecurityPrivilege(adminToken));
            securityPrivilege.Enable();
        }
        private void Budget()
        {
            if (elapsed.ElapsedMilliseconds > 40000) throw new InvalidOperationException("time bound");
            using (Process process = Process.GetCurrentProcess())
            {
                long p = process.PrivateMemorySize64, w = process.WorkingSet64;
                if (p > 256L * 1024 * 1024 || w > 384L * 1024 * 1024) throw new InvalidOperationException("memory bound");
                Interlocked.Exchange(ref peakPrivate, Math.Max(Interlocked.Read(ref peakPrivate), p));
                Interlocked.Exchange(ref peakWorking, Math.Max(Interlocked.Read(ref peakWorking), w));
            }
            Native.MEMORYSTATUSEX memory = new Native.MEMORYSTATUSEX(); memory.Length = 64;
            Check(Native.GlobalMemoryStatusEx(ref memory));
            ulong available, total, free; Check(Native.GetDiskFreeSpaceExW(@"C:\", out available, out total, out free));
            if (memory.AvailablePhysical < 2UL * 1024 * 1024 * 1024 || available < 2UL * 1024 * 1024 * 1024)
                throw new InvalidOperationException("free resource bound");
            Interlocked.Exchange(ref minimumRam, Math.Min(Interlocked.Read(ref minimumRam), (long)memory.AvailablePhysical));
            Interlocked.Exchange(ref minimumDisk, Math.Min(Interlocked.Read(ref minimumDisk), (long)available));
        }
        private static IntPtr OpenDirectory(string path)
        {
            Native.SA sa = new Native.SA(IntPtr.Zero);
            IntPtr handle = Native.CreateFileW(path, 0x120080, 3, ref sa, 3, 0x02200000, IntPtr.Zero);
            ValidHandle(handle); return handle;
        }
        private void CheckAncestors()
        {
            MarkInspection(InspectionStep.VolumePin);
            Policy.Require(Pin(volume) == volumePin, "ancestor identity/policy changed");
            MarkInspection(InspectionStep.ParentPin);
            Policy.Require(Pin(parent) == parentPin, "ancestor identity/policy changed");
            MarkInspection(InspectionStep.VolumePeerAccess); CheckPeerParent(volume);
            MarkInspection(InspectionStep.ParentPeerAccess); CheckPeerParent(parent);
        }
        private string Pin(IntPtr handle)
        { return Identity(handle) + ":" + Security(handle, failure); }
        private static string Identity(IntPtr handle)
        {
            VerifyNonInherit(handle);
            byte[] attributes = new byte[8], identity = new byte[24];
            Check(Native.GetFileInformationByHandleEx(handle, 9, attributes, 8));
            Policy.Require((BitConverter.ToUInt32(attributes, 0) & 0x410) == 0x10 && BitConverter.ToUInt32(attributes, 4) == 0, "directory or reparse");
            Check(Native.GetFileInformationByHandleEx(handle, 18, identity, 24));
            return Convert.ToBase64String(identity);
        }
        private void CheckPeerParent(IntPtr handle)
        {
            IntPtr sd = GetSd(handle, failure), privileges = Marshal.AllocHGlobal(4096);
            ReleaseGuard.Run(failure, delegate
            {
                Native.GENERIC_MAPPING mapping = new Native.GENERIC_MAPPING();
                mapping.Read = 0x120089; mapping.Write = 0x120116; mapping.Execute = 0x1200a0; mapping.All = 0x1f01ff;
                uint length = 4096, granted; bool allowed;
                Check(Native.AccessCheck(sd, peerToken, 0x02000000, ref mapping, privileges, ref length, out granted, out allowed));
                Policy.Require(allowed && (granted & Policy.DangerousAncestorAccess) == 0, "ordinary peer may alter ancestor namespace/policy");
                return 0;
            }, delegate { Marshal.FreeHGlobal(privileges); return FreeStatus(sd); });
        }
        private void CheckAbsent()
        {
            IntPtr info;
            uint result = Native.NetUserGetInfo(null, Policy.Account, 23, out info);
            ReleaseGuard.Run(failure, delegate { Policy.Require(result == 2221, "account exists or account query failed"); return 0; },
                delegate { return info == IntPtr.Zero ? 0 : Native.NetApiBufferFree(info); });
            uint attributes = Native.GetFileAttributesW(Policy.Root);
            int error = Marshal.GetLastWin32Error();
            Policy.Require(attributes == 0xffffffff && error == 2, "root exists or absence is uncertain");
        }
        private static void CreateAccount()
        {
            IntPtr random = IntPtr.Zero, password = IntPtr.Zero;
            try
            {
                random = Marshal.AllocHGlobal(32); password = Marshal.AllocHGlobal(138);
                Policy.Require(Native.BCryptGenRandom(IntPtr.Zero, random, 32, 2) == 0, "system RNG failure");
                const string prefix = "Aa9!";
                for (int i = 0; i < 4; i++) Marshal.WriteInt16(password, i * 2, prefix[i]);
                const string hex = "0123456789abcdef";
                for (int i = 0; i < 32; i++)
                {
                    byte value = Marshal.ReadByte(random, i);
                    Marshal.WriteInt16(password, (4 + i * 2) * 2, hex[value >> 4]);
                    Marshal.WriteInt16(password, (5 + i * 2) * 2, hex[value & 15]);
                }
                Marshal.WriteInt16(password, 136, 0);
                // No managed secret array/string, GC relocation copy or password string marshalling.
                Native.USER_INFO_1 info = new Native.USER_INFO_1();
                info.Name = Policy.Account; info.Password = password; info.Privilege = 1;
                info.Flags = Policy.DisabledNormalFlags; info.Comment = "Banto S4-B2 isolated engineering; disabled at rest";
                uint parameter; Status(Native.NetUserAdd(null, 1, ref info, out parameter));
            }
            finally
            {
                if (password != IntPtr.Zero)
                {
                    for (int i = 0; i < 138; i++) Marshal.WriteByte(password, i, 0);
                    Marshal.FreeHGlobal(password);
                }
                if (random != IntPtr.Zero) { for (int i = 0; i < 32; i++) Marshal.WriteByte(random, i, 0); Marshal.FreeHGlobal(random); }
            }
        }
        private void InspectAccount()
        {
            IntPtr buffer; uint status = Native.NetUserGetInfo(null, Policy.Account, 23, out buffer);
            ReleaseGuard.Run(failure, delegate
            {
                Status(status); Policy.Require(buffer != IntPtr.Zero, "account response");
                Native.USER_INFO_23 info = (Native.USER_INFO_23)Marshal.PtrToStructure(buffer, typeof(Native.USER_INFO_23));
                Policy.Require(Marshal.PtrToStringUni(info.Name) == Policy.Account && (info.Flags & 0x203) == 0x203 &&
                    (info.Flags & (0x10 | 0x20 | 0x100 | 0x800 | 0x1000 | 0x2000)) == 0, "account flags");
                string actual = new SecurityIdentifier(info.Sid).Value;
                Policy.Require(actual != Policy.Peer && new SecurityIdentifier(actual).IsAccountSid(), "account SID");
                Policy.Require(publisher == null || publisher == actual, "account SID changed"); publisher = actual;
                return 0;
            }, delegate { return buffer == IntPtr.Zero ? 0 : Native.NetApiBufferFree(buffer); });
        }
        private void AddUsers()
        {
            SecurityIdentifier group = new SecurityIdentifier(Policy.Users);
            string translated = ((NTAccount)group.Translate(typeof(NTAccount))).Value;
            int slash = translated.IndexOf('\\'); Policy.Require(slash > 0 && slash == translated.LastIndexOf('\\'), "Users alias");
            usersName = translated.Substring(slash + 1);
            SecurityIdentifier sid = new SecurityIdentifier(publisher); byte[] bytes = new byte[sid.BinaryLength]; sid.GetBinaryForm(bytes, 0);
            IntPtr pointer = Marshal.AllocHGlobal(bytes.Length);
            try
            {
                Marshal.Copy(bytes, 0, pointer, bytes.Length);
                Native.LOCALGROUP_MEMBERS_INFO_0 info = new Native.LOCALGROUP_MEMBERS_INFO_0(); info.Sid = pointer;
                uint status = Native.NetLocalGroupAddMembers(null, usersName, 0, ref info, 1);
                if (status != 1378) Status(status); // Already a member still requires the full verification below.
            }
            finally { Marshal.FreeHGlobal(pointer); }
        }
        private void InspectGroups()
        {
            IntPtr buffer; uint read, total;
            uint status = Native.NetUserGetLocalGroups(null, Policy.Account, 0, 1, out buffer, 65536, out read, out total);
            ReleaseGuard.Run(failure, delegate
            {
                Status(status); Policy.Require(read == 1 && total == 1 && buffer != IntPtr.Zero, "unexpected/incomplete groups");
                string name = Marshal.PtrToStringUni(Marshal.ReadIntPtr(buffer));
                Policy.Require(String.Equals(name, usersName, StringComparison.OrdinalIgnoreCase), "unexpected group");
                return 0;
            }, delegate { return buffer == IntPtr.Zero ? 0 : Native.NetApiBufferFree(buffer); });
        }
        private byte[] Receipt()
        {
            string text = "{\n  \"schema\": \"banto-principal-setup-v1\",\n  \"state\": \"prepared-preclose\",\n" +
                "  \"account\": \"" + Policy.Account + "\",\n  \"publisher_sid\": \"" + publisher + "\",\n" +
                "  \"peer_sid\": \"" + Policy.Peer + "\",\n  \"local_group_sid\": \"" + Policy.Users + "\",\n" +
                "  \"account_disabled\": true,\n  \"publisher_logon_performed\": false,\n  \"isolation_certified\": false,\n" +
                "  \"root_pin\": \"" + Pin(root) + "\",\n  \"root_sddl\": \"" + Security(root, failure) + "\",\n" +
                "  \"utc\": \"" + DateTime.UtcNow.ToString("o") + "\",\n  \"elapsed_ms\": " + elapsed.ElapsedMilliseconds + ",\n" +
                "  \"peak_private_bytes\": " + Interlocked.Read(ref peakPrivate) + ",\n  \"peak_working_bytes\": " + Interlocked.Read(ref peakWorking) + ",\n" +
                "  \"minimum_ram_bytes\": " + Interlocked.Read(ref minimumRam) + ",\n  \"minimum_c_free_bytes\": " + Interlocked.Read(ref minimumDisk) + "\n}\n";
            byte[] bytes = Encoding.UTF8.GetBytes(text); Policy.Require(bytes.Length <= 65536, "receipt bound"); return bytes;
        }
        private static IntPtr GetSd(IntPtr handle, FailureState state)
        {
            IntPtr owner, group, dacl, sacl, descriptor;
            uint status = Native.GetSecurityInfo(handle, 1, 0x17, out owner, out group, out dacl, out sacl, out descriptor);
            if (status != 0) ReleaseGuard.Run(state, delegate { Status(status); return 0; }, delegate { return descriptor == IntPtr.Zero ? 0 : FreeStatus(descriptor); });
            Policy.Require(descriptor != IntPtr.Zero, "security response"); return descriptor;
        }
        private static string Security(IntPtr handle, FailureState state)
        {
            IntPtr sd = GetSd(handle, state);
            return ReleaseGuard.Run(state, delegate { return Sddl(sd, state); }, delegate { return FreeStatus(sd); });
        }
        public static string Canonical(string value)
        { return Canonical(value, new FailureState()); }
        private static string Canonical(string value, FailureState state)
        { IntPtr sd = Parse(value, state); return ReleaseGuard.Run(state, delegate { return Sddl(sd, state); }, delegate { return FreeStatus(sd); }); }
        private static string Sddl(IntPtr sd, FailureState state)
        {
            IntPtr output; uint length;
            bool converted = Native.ConvertSecurityDescriptorToStringSecurityDescriptorW(sd, 1, 0x17, out output, out length);
            int error = Marshal.GetLastWin32Error();
            return ReleaseGuard.Run(state, delegate { if (!converted) throw new Win32Exception(error); Policy.Require(length > 0 && length <= 32768, "SDDL bound"); return Marshal.PtrToStringUni(output); },
                delegate { return output == IntPtr.Zero ? 0 : FreeStatus(output); });
        }
        private static IntPtr Parse(string value, FailureState state)
        {
            IntPtr sd; uint size; bool converted = Native.ConvertStringSecurityDescriptorToSecurityDescriptorW(value, 1, out sd, out size);
            int error = Marshal.GetLastWin32Error();
            if (!converted) ReleaseGuard.Run<int>(state, delegate { throw new Win32Exception(error); }, delegate { return sd == IntPtr.Zero ? 0 : FreeStatus(sd); });
            return sd;
        }
        private void MarkInspection(InspectionStep step)
        { if (failure.InspectionStep != InspectionStep.None) failure.InspectionStep = step; }
        private void VerifyPolicy(IntPtr handle, string expected)
        {
            MarkInspection(InspectionStep.ActualPolicy);
            string actual = Security(handle, failure);
            MarkInspection(InspectionStep.ExpectedPolicy);
            string canonical = Canonical(expected, failure);
            if (failure.InspectionStep != InspectionStep.None)
            {
                MarkInspection(InspectionStep.CompareDetails);
                failure.PolicyDifference = InspectionFailure.ComparePolicy(actual, canonical);
                MarkInspection(InspectionStep.ExactPolicyComparison);
            }
            Policy.Require(actual == canonical, "exact owner/group/DACL/label policy");
        }
        private static void VerifyNonInherit(IntPtr handle)
        { uint flags; Check(Native.GetHandleInformation(handle, out flags)); Policy.Require((flags & 1) == 0, "inheritable handle"); }
        private static void ValidHandle(IntPtr handle)
        { if (handle == IntPtr.Zero || handle == new IntPtr(-1)) throw new Win32Exception(Marshal.GetLastWin32Error()); }
        private static void Check(bool value) { if (!value) throw new Win32Exception(Marshal.GetLastWin32Error()); }
        private static void Status(uint value) { if (value != 0) throw new Win32Exception(unchecked((int)value)); }
        private static void Close(ref IntPtr handle)
        { Policy.Require(handle != IntPtr.Zero && handle != new IntPtr(-1), "close authority"); Check(Native.CloseHandle(handle)); handle = IntPtr.Zero; }
        private void Free(ref IntPtr memory)
        {
            if (memory != IntPtr.Zero)
            {
                IntPtr held = memory;
                ReleaseGuard.Free(failure, delegate { return FreeStatus(held); });
                memory = IntPtr.Zero;
            }
        }
        private static uint FreeStatus(IntPtr memory)
        {
            if (Native.LocalFree(memory) == IntPtr.Zero) return 0;
            int error = Marshal.GetLastWin32Error(); return error > 0 ? (uint)error : 65535;
        }
    }
    public static class Native
    {
        [StructLayout(LayoutKind.Sequential)] public struct LUID { public uint Low; public int High; }
        [StructLayout(LayoutKind.Sequential)] public struct TOKEN_PRIVILEGES_ONE { public uint Count; public LUID Luid; public uint Attributes; }
        [StructLayout(LayoutKind.Sequential)] public struct SA
        { public uint Length; public IntPtr Descriptor; public int Inherit; public SA(IntPtr sd) { Length = 24; Descriptor = sd; Inherit = 0; } }
        [StructLayout(LayoutKind.Sequential)] public struct GENERIC_MAPPING { public uint Read, Write, Execute, All; }
        [StructLayout(LayoutKind.Sequential)] public struct MEMORYSTATUSEX
        { public uint Length, Load; public ulong TotalPhysical, AvailablePhysical, TotalPageFile, AvailablePageFile, TotalVirtual, AvailableVirtual, AvailableExtendedVirtual; }
        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] public struct USER_INFO_1
        { [MarshalAs(UnmanagedType.LPWStr)] public string Name; public IntPtr Password; public uint PasswordAge, Privilege; public IntPtr Home; [MarshalAs(UnmanagedType.LPWStr)] public string Comment; public uint Flags; public IntPtr Script; }
        [StructLayout(LayoutKind.Sequential)] public struct USER_INFO_23 { public IntPtr Name, FullName, Comment; public uint Flags; public IntPtr Sid; }
        [StructLayout(LayoutKind.Sequential)] public struct LOCALGROUP_MEMBERS_INFO_0 { public IntPtr Sid; }
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] public static extern IntPtr CreateDirectory2W(string path, uint access, uint share, uint flags, ref SA sa);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] public static extern IntPtr CreateFileW(string path, uint access, uint share, ref SA sa, uint disposition, uint flags, IntPtr template);
        [DllImport("kernel32.dll", SetLastError = true)] public static extern bool GetFileInformationByHandleEx(IntPtr handle, int type, byte[] buffer, uint size);
        [DllImport("kernel32.dll", SetLastError = true)] public static extern bool GetHandleInformation(IntPtr handle, out uint flags);
        [DllImport("kernel32.dll", SetLastError = true)] public static extern bool CloseHandle(IntPtr handle);
        [DllImport("kernel32.dll", SetLastError = true)] public static extern IntPtr LocalFree(IntPtr memory);
        [DllImport("kernel32.dll")] public static extern IntPtr GetCurrentProcess();
        [DllImport("kernel32.dll", SetLastError = true)] public static extern bool WriteFile(IntPtr file, byte[] buffer, uint size, out uint written, IntPtr overlapped);
        [DllImport("kernel32.dll", SetLastError = true)] public static extern bool FlushFileBuffers(IntPtr file);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] public static extern uint GetFileAttributesW(string path);
        [DllImport("kernel32.dll", SetLastError = true)] public static extern bool GlobalMemoryStatusEx(ref MEMORYSTATUSEX memory);
        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] public static extern bool GetDiskFreeSpaceExW(string path, out ulong available, out ulong total, out ulong free);
        [DllImport("advapi32.dll", SetLastError = true)] public static extern bool OpenProcessToken(IntPtr process, uint access, out IntPtr token);
        [DllImport("advapi32.dll", SetLastError = true)] public static extern bool GetTokenInformation(IntPtr token, int type, IntPtr data, uint length, out uint needed);
        [DllImport("advapi32.dll", SetLastError = true)] public static extern bool DuplicateToken(IntPtr token, int level, out IntPtr duplicate);
        [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)] public static extern bool LookupPrivilegeValueW(string system, string name, out LUID luid);
        [DllImport("advapi32.dll", SetLastError = true)] public static extern bool AdjustTokenPrivileges(IntPtr token, bool disableAll, ref TOKEN_PRIVILEGES_ONE state, uint length, IntPtr previous, IntPtr needed);
        [DllImport("advapi32.dll", SetLastError = true)] public static extern bool AccessCheck(IntPtr sd, IntPtr token, uint desired, ref GENERIC_MAPPING mapping, IntPtr privileges, ref uint length, out uint granted, out bool allowed);
        [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)] public static extern bool ConvertStringSecurityDescriptorToSecurityDescriptorW(string text, uint revision, out IntPtr descriptor, out uint size);
        [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)] public static extern bool ConvertSecurityDescriptorToStringSecurityDescriptorW(IntPtr descriptor, uint revision, uint information, out IntPtr text, out uint length);
        [DllImport("advapi32.dll")] public static extern uint GetSecurityInfo(IntPtr handle, uint type, uint information, out IntPtr owner, out IntPtr group, out IntPtr dacl, out IntPtr sacl, out IntPtr descriptor);
        [DllImport("advapi32.dll")] public static extern uint SetSecurityInfo(IntPtr handle, uint type, uint information, IntPtr owner, IntPtr group, IntPtr dacl, IntPtr sacl);
        [DllImport("advapi32.dll", SetLastError = true)] public static extern bool GetSecurityDescriptorDacl(IntPtr sd, out bool present, out IntPtr dacl, out bool defaulted);
        [DllImport("netapi32.dll", CharSet = CharSet.Unicode)] public static extern uint NetUserAdd(string server, uint level, ref USER_INFO_1 info, out uint parameter);
        [DllImport("netapi32.dll", CharSet = CharSet.Unicode)] public static extern uint NetUserGetInfo(string server, string user, uint level, out IntPtr info);
        [DllImport("netapi32.dll", CharSet = CharSet.Unicode)] public static extern uint NetUserGetLocalGroups(string server, string user, uint level, uint flags, out IntPtr groups, uint max, out uint read, out uint total);
        [DllImport("netapi32.dll", CharSet = CharSet.Unicode)] public static extern uint NetLocalGroupAddMembers(string server, string group, uint level, ref LOCALGROUP_MEMBERS_INFO_0 info, uint count);
        [DllImport("netapi32.dll")] public static extern uint NetApiBufferFree(IntPtr buffer);
        [DllImport("bcrypt.dll")] public static extern uint BCryptGenRandom(IntPtr algorithm, IntPtr buffer, uint length, uint flags);
    }
}
