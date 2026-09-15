// No account, directory, process launch or other privileged API is called here.
using System;
using System.Collections.Generic;
using System.Collections;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using Banto.PrincipalSetup;

public static class PrincipalSetupTests
{
    private sealed class FaultBackend : IBackend
    {
        public readonly List<Phase> Calls = new List<Phase>();
        public FailureState State = new FailureState();
        public FailureState Failure { get { return State; } }
        public Phase? Fault;
        public Exception Error = new Win32Exception(5);
        public void Execute(Phase phase) { Calls.Add(phase); if (phase == Fault) throw Error; }
    }
    private sealed class HostileDataException : Win32Exception
    {
        public int DataReads;
        private readonly Exception secondary = new OutOfMemoryException("injected Data allocation failure");
        public HostileDataException() : base(5) { }
        public override IDictionary Data { get { DataReads++; throw secondary; } }
    }
    private static int count;
    private static void Assert(bool value, string name)
    { if (!value) throw new Exception(name); }
    private static void Test(string name, Action action) { action(); count++; Console.WriteLine("PASS " + name); }
    public static int Main()
    {
        try
        {
            Test("complete setup closes child before each ancestor", delegate()
            {
                FaultBackend backend = new FaultBackend(); Sequence sequence = new Sequence();
                Assert(sequence.Run(backend) == 0, "success");
                Assert(backend.Calls.IndexOf(Phase.CreateDisabledAccount) > backend.Calls.IndexOf(Phase.InspectInitialRoot), "policy before account");
                Assert(backend.Calls.IndexOf(Phase.CloseReceipt) < backend.Calls.IndexOf(Phase.CloseRoot), "child before root");
                Assert(backend.Calls.IndexOf(Phase.CloseRoot) < backend.Calls.IndexOf(Phase.CloseProgramData), "root before parent");
                Assert(backend.Calls.IndexOf(Phase.CloseProgramData) < backend.Calls.IndexOf(Phase.CloseVolume), "parent before volume");
            });
            foreach (Phase failure in Enum.GetValues(typeof(Phase)))
            {
                Phase fail = failure;
                Test("fault at " + fail + " stops all subsequent effects and cleanup", delegate()
                {
                    FaultBackend backend = new FaultBackend(); backend.Fault = fail;
                    Sequence sequence = new Sequence(); int result = sequence.Run(backend);
                    Assert(result == (((int)fail << 16) | 5), "first phase/error retained");
                    Assert(backend.Calls.Count == (int)fail && backend.Calls[backend.Calls.Count - 1] == fail, "no retry/cleanup");
                    bool rejected = false; try { sequence.Run(backend); } catch (InvalidOperationException) { rejected = true; }
                    Assert(rejected && backend.Calls.Count == (int)fail, "no second attempt");
                });
            }
            Test("unknown account response preserves ancestors with no policy/group calls", delegate()
            {
                FaultBackend backend = new FaultBackend(); backend.Fault = Phase.CreateDisabledAccount;
                backend.Error = new InvalidOperationException("lost response");
                Assert(new Sequence().Run(backend) == (((int)Phase.CreateDisabledAccount << 16) | 65535), "unknown status");
                Assert(!backend.Calls.Contains(Phase.AddUsersGroup) && !backend.Calls.Contains(Phase.CloseRoot), "no subsequent action");
            });
            Test("initial and final root policy exclude ordinary peer mutation", delegate()
            {
                string publisher = "S-1-5-21-2169670816-255940906-2713565042-2999";
                foreach (string value in new string[] { null, publisher })
                {
                    string canonical = NativeBackend.Canonical(Policy.Descriptor(value));
                    RawSecurityDescriptor sd = new RawSecurityDescriptor(canonical);
                    Assert(sd.Owner.Value == "S-1-5-32-544" && sd.Group.Value == "S-1-5-32-544", "admin owner/group");
                    Assert((sd.ControlFlags & ControlFlags.DiscretionaryAclProtected) != 0, "protected DACL");
                    Assert((sd.ControlFlags & ControlFlags.SystemAclProtected) != 0, "protected label ACL");
                    Assert(sd.DiscretionaryAcl.Count == (value == null ? 3 : 4), "no shared-group extras");
                    for (int i = 2; i < sd.DiscretionaryAcl.Count; i++)
                    {
                        CommonAce ace = (CommonAce)sd.DiscretionaryAcl[i];
                        Assert(ace.AceQualifier == AceQualifier.AccessAllowed && ace.AccessMask == 0x1200a9, "read-only mask");
                        Assert((ace.AccessMask & 0xd0156) == 0 && ace.AceFlags == AceFlags.None, "no mutation/inheritance");
                    }
                    Assert(canonical.Contains("(ML;;NW;;;ME)"), "medium no-write-up");
                }
            });
            Test("publisher must be distinct account SID", delegate()
            {
                foreach (string value in new string[] { Policy.Peer, "S-1-5-32-545", "invalid" })
                {
                    bool rejected = false; try { Policy.Descriptor(value); } catch (ArgumentException) { rejected = true; } catch (InvalidOperationException) { rejected = true; }
                    Assert(rejected, "invalid publisher");
                }
            });
            Test("account flags include disabled standard normal account", delegate()
            { Assert(Policy.DisabledNormalFlags == (1 | 2 | 0x200), "no password exemptions or enable"); });
            Test("Win64 native struct sizes and password pointer", delegate()
            {
                Assert(IntPtr.Size == 8, "Win64");
                Assert(Marshal.SizeOf(typeof(Native.SA)) == 24 && Marshal.OffsetOf(typeof(Native.SA), "Descriptor").ToInt32() == 8, "SA");
                Assert(Marshal.SizeOf(typeof(Native.USER_INFO_1)) == 56 && Marshal.OffsetOf(typeof(Native.USER_INFO_1), "Flags").ToInt32() == 40, "USER1");
                Assert(typeof(Native.USER_INFO_1).GetField("Password").FieldType == typeof(IntPtr), "no managed password string marshalling");
                Assert(Marshal.SizeOf(typeof(Native.USER_INFO_23)) == 40 && Marshal.OffsetOf(typeof(Native.USER_INFO_23), "Sid").ToInt32() == 32, "USER23");
                Assert(Marshal.SizeOf(typeof(Native.MEMORYSTATUSEX)) == 64, "memory ABI");
            });
            Test("release failure prevents continuation after successful inner operation", delegate()
            {
                int releases = 0; bool continued = false; Exception caught = null;
                FailureState state = new FailureState();
                try { ReleaseGuard.Run(state, delegate { return 42; }, delegate { releases++; return 8u; }); continued = true; }
                catch (Exception error) { caught = error; }
                Assert(!continued && releases == 1 && Object.ReferenceEquals(caught, state.ReleaseStop) && state.ReleaseFailed && state.ReleaseError == 8, "release failure");
            });
            Test("secondary release failure retains primary error and exit detail", delegate()
            {
                Exception first = new Win32Exception(5), caught = null; int releases = 0;
                FailureState state = new FailureState();
                try { ReleaseGuard.Run<int>(state, delegate { throw first; }, delegate { releases++; return 8u; }); } catch (Exception error) { caught = error; }
                Assert(Object.ReferenceEquals(first, caught) && releases == 1 && state.ReleaseFailed, "first error retained");
                FaultBackend backend = new FaultBackend(); backend.State = state; backend.Fault = Phase.InspectInitialRoot; backend.Error = caught;
                int code = new Sequence().Run(backend);
                Assert(code == (0x40000000 | ((int)Phase.InspectInitialRoot << 16) | 5), "separate release bit");
                Assert(!backend.Calls.Contains(Phase.CreateDisabledAccount), "account not called");
            });
            Test("successful release preserves original failure without release flag", delegate()
            {
                Exception first = new InvalidOperationException("operation"), caught = null; int releases = 0;
                FailureState state = new FailureState();
                try { ReleaseGuard.Run<int>(state, delegate { throw first; }, delegate { releases++; return 0u; }); } catch (Exception error) { caught = error; }
                Assert(Object.ReferenceEquals(first, caught) && releases == 1 && !state.ReleaseFailed, "operation failure");
            });
            Test("allocation failure in Exception.Data cannot erase primary phase/code", delegate()
            {
                HostileDataException first = new HostileDataException(); Exception caught = null; FailureState state = new FailureState();
                try { ReleaseGuard.Run<int>(state, delegate { throw first; }, delegate { return 8u; }); } catch (Exception error) { caught = error; }
                FaultBackend backend = new FaultBackend(); backend.State = state; backend.Fault = Phase.InspectInitialRoot; backend.Error = caught;
                Assert(new Sequence().Run(backend) == (0x40000000 | ((int)Phase.InspectInitialRoot << 16) | 5), "phase/code");
                Assert(first.DataReads == 0 && Object.ReferenceEquals(first, caught), "Data never inspected or mutated");
            });
            Test("nested memory releases retain the first release failure code", delegate()
            {
                FailureState state = new FailureState(); Exception caught = null;
                try { ReleaseGuard.Run(state, delegate { return ReleaseGuard.Run(state, delegate { return 1; }, delegate { return 8u; }); }, delegate { return 14u; }); }
                catch (Exception error) { caught = error; }
                FaultBackend backend = new FaultBackend(); backend.State = state; backend.Fault = Phase.InspectInitialRoot; backend.Error = caught;
                Assert(new Sequence().Run(backend) == (0x40000000 | ((int)Phase.InspectInitialRoot << 16) | 8), "first release code");
            });
            Test("terminal descriptor release records failure bit and makes one call", delegate()
            {
                FailureState state = new FailureState(); int calls = 0; Exception caught = null;
                try { ReleaseGuard.Free(state, delegate { calls++; return 8u; }); } catch (Exception error) { caught = error; }
                FaultBackend backend = new FaultBackend(); backend.State = state; backend.Fault = Phase.StopWatchdog; backend.Error = caught;
                Assert(calls == 1 && new Sequence().Run(backend) == (0x40000000 | ((int)Phase.StopWatchdog << 16) | 8), "terminal release status");
            });
            Test("all initial inspection substeps retain phase and unknown exception classification", delegate()
            {
                foreach (InspectionStep step in Enum.GetValues(typeof(InspectionStep)))
                {
                    if (step == InspectionStep.None) continue;
                    FaultBackend backend = new FaultBackend(); backend.Fault = Phase.InspectInitialRoot;
                    backend.Error = new InvalidOperationException("do not disclose"); backend.State.InspectionStep = step;
                    int code = new Sequence().Run(backend);
                    Assert(code == (InspectionFailure.Marker | (5 << 16) | (1 << 13) | ((int)step << 8)), "substep encoding");
                    Assert(backend.Calls.Count == 5, "no calls after inspection failure");
                }
            });
            Test("inspection exception kinds are bounded and preserve unknown native classification", delegate()
            {
                FailureState state = new FailureState(); state.InspectionStep = InspectionStep.RootIdentity;
                Exception[] errors = { new Exception(), new InvalidOperationException(), new OutOfMemoryException(), new Win32Exception(65535), state.ReleaseStop };
                for (int i = 0; i < errors.Length; i++)
                    Assert(((InspectionFailure.Encode(Phase.InspectInitialRoot, 65535, errors[i], state) >> 13) & 7) == i, "kind");
            });
            Test("known native errors and noninitial failures preserve legacy encoding", delegate()
            {
                FailureState state = new FailureState(); Exception error = new Win32Exception(5);
                Assert(InspectionFailure.Encode(Phase.InspectInitialRoot, 65535, error, state) == ((5 << 16) | 65535), "no stale observation");
                state.InspectionStep = InspectionStep.ExactPolicyComparison;
                Assert(InspectionFailure.Encode(Phase.InspectInitialRoot, 5, error, state) == ((5 << 16) | 5), "native error");
                Assert(InspectionFailure.Encode(Phase.CreateReceipt, 65535, error, state) == ((12 << 16) | 65535), "other phase");
            });
            Test("secondary release flag survives diagnostic encoding without cleanup", delegate()
            {
                FaultBackend backend = new FaultBackend(); backend.Fault = Phase.InspectInitialRoot;
                backend.Error = new InvalidOperationException(); backend.State.InspectionStep = InspectionStep.ExactPolicyComparison;
                backend.State.PolicyDifference = 40; backend.State.ReleaseFailed = true; backend.State.ReleaseError = 8;
                int code = new Sequence().Run(backend);
                Assert(code == (0x60000000 | (5 << 16) | (1 << 13) | (10 << 8) | 40), "release and diagnostic fields");
                Assert(backend.Calls.Count == 5, "no cleanup");
            });
            Test("policy comparison separates owner group and exact match", delegate()
            {
                string expected = Policy.Descriptor(null);
                Assert(InspectionFailure.ComparePolicy(expected, expected) == 0, "equal");
                Assert(InspectionFailure.ComparePolicy(expected.Replace("O:BA", "O:SY"), expected) == 1, "owner");
                Assert(InspectionFailure.ComparePolicy(expected.Replace("G:BA", "G:SY"), expected) == 2, "group");
            });
            Test("policy comparison retains DACL rights inheritance and protection differences", delegate()
            {
                string expected = Policy.Descriptor(null);
                foreach (string actual in new string[] { expected.Replace("0x1200a9", "FA"), expected.Replace("(A;;FA;;;SY)", "(A;OI;FA;;;SY)"), expected.Replace("D:P", "D:") })
                    Assert((InspectionFailure.ComparePolicy(actual, expected) & 4) != 0, "DACL difference");
                Assert(InspectionFailure.ComparePolicy(expected.Replace("D:P", "D:"), expected) == 20, "DACL protection");
                Assert(InspectionFailure.ComparePolicy(expected.Replace("D:P", "D:PAI"), expected) == 68, "DACL auto flag");
            });
            Test("policy comparison retains label and SACL control differences", delegate()
            {
                string expected = Policy.Descriptor(null);
                Assert(InspectionFailure.ComparePolicy(expected.Replace("S:P", "S:"), expected) == 40, "SACL protection");
                Assert(InspectionFailure.ComparePolicy(expected.Replace("S:PAI", "S:P"), expected) == 136, "SACL auto flag");
                Assert(InspectionFailure.ComparePolicy(expected.Replace(";;;ME)", ";;;HI)"), expected) == 8, "label level");
                Assert(InspectionFailure.ComparePolicy(expected.Replace("ML;;NW", "ML;;NR"), expected) == 8, "label mask");
            });
            Test("tagged exception path never accesses Exception Data", delegate()
            {
                HostileDataException error = new HostileDataException(); FailureState state = new FailureState();
                state.InspectionStep = InspectionStep.ActualPolicy;
                int code = InspectionFailure.Encode(Phase.InspectInitialRoot, 65535, error, state);
                Assert(error.DataReads == 0 && ((code >> 13) & 7) == 3, "no exception metadata allocations");
            });
            Test("diagnostic failure remains single use with no account continuation", delegate()
            {
                FaultBackend backend = new FaultBackend(); backend.Fault = Phase.InspectInitialRoot;
                backend.Error = new OutOfMemoryException(); backend.State.InspectionStep = InspectionStep.CompareDetails;
                Sequence sequence = new Sequence(); sequence.Run(backend);
                bool rejected = false; try { sequence.Run(backend); } catch (InvalidOperationException) { rejected = true; }
                Assert(rejected && backend.Calls.Count == 5 && !backend.Calls.Contains(Phase.CreateDisabledAccount), "terminal");
            });
            Test("explicit SACL AI changes only inheritance-state bit while preserving all security bytes", delegate()
            {
                foreach (string publisher in new string[] { null, "S-1-5-21-2169670816-255940906-2713565042-2999" })
                {
                    string current = NativeBackend.Canonical(Policy.Descriptor(publisher));
                    RawSecurityDescriptor actual = new RawSecurityDescriptor(current);
                    RawSecurityDescriptor prior = new RawSecurityDescriptor(current.Replace("S:PAI", "S:P"));
                    Assert((actual.ControlFlags ^ prior.ControlFlags) == ControlFlags.SystemAclAutoInherited, "one state bit only");
                    Assert((actual.ControlFlags & (ControlFlags.DiscretionaryAclProtected | ControlFlags.SystemAclProtected)) ==
                        (ControlFlags.DiscretionaryAclProtected | ControlFlags.SystemAclProtected), "both protected");
                    Assert(actual.SystemAcl.Count == 1 && current.Contains("(ML;;NW;;;ME)"), "one explicit medium label");
                    byte[] a = new byte[actual.BinaryLength], b = new byte[prior.BinaryLength];
                    actual.GetBinaryForm(a, 0); prior.GetBinaryForm(b, 0);
                    Assert(a.Length == b.Length, "same descriptor length");
                    for (int i = 0; i < a.Length; i++) Assert((i == 3 ? a[i] ^ 8 : a[i]) == b[i], "unchanged owner/group/ACL bytes");
                }
            });
            Test("existing principal sequence skips all account mutation phases", delegate()
            {
                FaultBackend backend = new FaultBackend();
                Assert(new Sequence(true).Run(backend) == 0, "success");
                Assert(backend.Calls.Count == 20 && !backend.Calls.Contains(Phase.CreateDisabledAccount) && !backend.Calls.Contains(Phase.AddUsersGroup), "no account mutation phases");
                Assert(backend.Calls.IndexOf(Phase.CheckAbsent) < backend.Calls.IndexOf(Phase.CreateRoot) && backend.Calls.Contains(Phase.InspectAccount) && backend.Calls.Contains(Phase.InspectGroups), "checks retained");
                Assert(backend.Calls.IndexOf(Phase.CloseReceipt) < backend.Calls.IndexOf(Phase.CloseRoot) && backend.Calls[19] == Phase.StopWatchdog, "normal teardown retained");
            });
            Test("every existing-principal failure is terminal and single use", delegate()
            {
                int expectedCalls = 0;
                foreach (Phase phase in Enum.GetValues(typeof(Phase)))
                {
                    if (phase == Phase.CreateDisabledAccount || phase == Phase.AddUsersGroup) continue;
                    expectedCalls++;
                    FaultBackend backend = new FaultBackend(); backend.Fault = phase; Sequence sequence = new Sequence(true);
                    Assert(sequence.Run(backend) == (((int)phase << 16) | 5) && backend.Calls.Count == expectedCalls, "first failure and prefix retained");
                    bool rejected = false; try { sequence.Run(backend); } catch (InvalidOperationException) { rejected = true; }
                    Assert(rejected && backend.Calls.Count == expectedCalls, "no retry");
                }
            });
            Test("existing account pin rejects changed name SID and every changed flag bit", delegate()
            {
                Policy.RequireExistingAccount(Policy.Account, Policy.ExistingPublisher, Policy.DisabledNormalFlags);
                string[] names = { "other", Policy.Account, Policy.Account };
                string[] sids = { Policy.ExistingPublisher, Policy.Peer, null };
                for (int i = 0; i < names.Length; i++)
                {
                    bool rejected = false; try { Policy.RequireExistingAccount(names[i], sids[i], 0x203); } catch (InvalidOperationException) { rejected = true; }
                    Assert(rejected, "name/SID pin");
                }
                for (int i = 0; i < 32; i++)
                {
                    bool rejected = false; try { Policy.RequireExistingAccount(Policy.Account, Policy.ExistingPublisher, 0x203u ^ (1u << i)); } catch (InvalidOperationException) { rejected = true; }
                    Assert(rejected, "flags exact");
                }
            });
            Test("native library has no account creation membership change or secret-generation imports", delegate()
            {
                foreach (string name in new string[] { "NetUserAdd", "NetLocalGroupAddMembers", "NetUserSetInfo", "NetUserDel", "LogonUserW", "BCryptGenRandom" })
                    Assert(typeof(Native).GetMethod(name) == null, "forbidden import " + name);
                Assert(typeof(ExistingEntry).GetMethod("Run") != null, "explicit existing-principal entry");
            });
            Test("final inspection diagnostic identifies all substeps with original phase", delegate()
            {
                foreach (InspectionStep step in Enum.GetValues(typeof(InspectionStep)))
                {
                    if (step == InspectionStep.None) continue;
                    FaultBackend backend = new FaultBackend(); backend.Fault = Phase.InspectFinalRoot; backend.Error = new InvalidOperationException();
                    backend.State.InspectionStep = step; backend.State.PolicyDifference = 68;
                    int code = new Sequence(true).Run(backend);
                    Assert(code == (InspectionFailure.Marker | (11 << 16) | (1 << 13) | ((int)step << 8) | 68), "final step/phase");
                    Assert(backend.Calls.Count == 9 && !backend.Calls.Contains(Phase.CreateReceipt), "terminal before receipt");
                }
            });
            Test("final DACL AI changes only its state bit and leaves initial policy unchanged", delegate()
            {
                foreach (string publisher in new string[] { null, Policy.ExistingPublisher })
                {
                    string current = NativeBackend.Canonical(Policy.Descriptor(publisher));
                    RawSecurityDescriptor actual = new RawSecurityDescriptor(current);
                    RawSecurityDescriptor prior = new RawSecurityDescriptor(current.Replace("D:PAI", "D:P"));
                    ControlFlags delta = publisher == null ? 0 : ControlFlags.DiscretionaryAclAutoInherited;
                    Assert((actual.ControlFlags ^ prior.ControlFlags) == delta, "one final state bit only");
                    Assert((actual.ControlFlags & (ControlFlags.DiscretionaryAclProtected | ControlFlags.SystemAclProtected)) ==
                        (ControlFlags.DiscretionaryAclProtected | ControlFlags.SystemAclProtected), "both protected");
                    Assert((actual.ControlFlags & (ControlFlags.DiscretionaryAclAutoInheritRequired | ControlFlags.SystemAclAutoInheritRequired)) == 0, "no AR flags");
                    byte[] a = new byte[actual.BinaryLength], b = new byte[prior.BinaryLength];
                    actual.GetBinaryForm(a, 0); prior.GetBinaryForm(b, 0); Assert(a.Length == b.Length, "same length");
                    for (int i = 0; i < a.Length; i++) Assert((i == 3 && publisher != null ? a[i] ^ 4 : a[i]) == b[i], "all other descriptor bytes unchanged");
                }
            });
            Console.WriteLine("RESULT " + count + " passed; OS mutations=0"); return 0;
        }
        catch (Exception error) { Console.WriteLine("FAIL " + error); return 1; }
    }
}
