// Fault injection only: never construct NativeBackend or call either native Entry.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using Banto.PrincipalSetup;
using Banto.PrincipalPreflight;

public static class PrincipalPreflightDiagnosticTests
{
    private sealed class Backend : IBackend
    {
        public readonly List<Phase> Calls = new List<Phase>();
        public readonly FailureState State = new FailureState();
        public FailureState Failure { get { return State; } }
        public Phase? Fault;
        public Exception Error = new Win32Exception(5);
        public void Execute(Phase phase) { Calls.Add(phase); if (phase == Fault) throw Error; }
    }
    private static int count;
    private static void Assert(bool ok, string message) { if (!ok) throw new Exception(message); }
    private static void Test(string name, Action body) { body(); count++; Console.WriteLine("PASS " + name); }
    private static void NoReuse(DiagnosticSequence sequence, Backend backend)
    {
        int before = backend.Calls.Count; bool rejected = false;
        try { sequence.Run(backend); } catch (InvalidOperationException) { rejected = true; }
        Assert(rejected && before == backend.Calls.Count, "second run touched backend");
    }
    public static int Main()
    {
        try
        {
            Phase[] allowed = { Phase.Preflight, Phase.ClosePeerToken, Phase.CloseLinkedToken,
                Phase.CloseAdminToken, Phase.StopWatchdog };
            Test("success calls only preflight then three token closes and watchdog stop", delegate()
            {
                Backend backend = new Backend(); DiagnosticSequence sequence = new DiagnosticSequence();
                Assert(sequence.Run(backend) == 0 && backend.Calls.Count == allowed.Length, "success");
                for (int i = 0; i < allowed.Length; i++) Assert(backend.Calls[i] == allowed[i], "unexpected phase");
                NoReuse(sequence, backend);
            });
            for (int i = 0; i < allowed.Length; i++)
            {
                int index = i;
                Test("failure at " + allowed[index] + " is terminal", delegate()
                {
                    Backend backend = new Backend(); backend.Fault = allowed[index];
                    DiagnosticSequence sequence = new DiagnosticSequence();
                    Assert(sequence.Run(backend) == (((int)allowed[index] << 16) | 5), "phase/error");
                    Assert(backend.Calls.Count == index + 1, "failure called later phases");
                    NoReuse(sequence, backend);
                });
            }
            Test("non-native preflight rejection preserves unknown detail", delegate()
            {
                Backend backend = new Backend(); backend.Fault = Phase.Preflight;
                backend.Error = new InvalidOperationException();
                Assert(new DiagnosticSequence().Run(backend) == 131071, "unknown detail");
                Assert(backend.Calls.Count == 1, "post-failure close");
            });
            Test("primary native error survives a recorded release failure", delegate()
            {
                Backend backend = new Backend(); backend.Fault = Phase.Preflight;
                backend.State.ReleaseFailed = true; backend.State.ReleaseError = 6;
                Assert(new DiagnosticSequence().Run(backend) == (0x40010000 | 5), "primary overwritten");
            });
            Test("standalone release failure keeps its native detail", delegate()
            {
                Backend backend = new Backend(); backend.Fault = Phase.StopWatchdog;
                backend.State.ReleaseFailed = true; backend.State.ReleaseError = 6;
                backend.Error = backend.State.ReleaseStop;
                Assert(new DiagnosticSequence().Run(backend) == (0x40000000 | ((int)Phase.StopWatchdog << 16) | 6), "release detail");
            });
            Console.WriteLine("RESULT " + count + " passed; OS mutations=0; no native backend entry");
            return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error.GetType().Name + ": " + error.Message); return 1; }
    }
}
