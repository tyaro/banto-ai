using System;
using System.Collections.Generic;
using Banto.PrincipalWorker;

public static class PrincipalWorkerLifecycleTests
{
    private static int count;
    private static void Assert(bool value, string reason) { if (!value) throw new Exception(reason); }
    private static void Reject(Action body) { bool rejected = false; try { body(); } catch (InvalidOperationException) { rejected = true; } Assert(rejected, "protocol accepted invalid input"); }
    private static void Test(string name, Action body) { body(); count++; Console.WriteLine("PASS " + name); }
    private sealed class Run
    {
        public readonly Lifecycle Model = new Lifecycle();
        public readonly List<Operation> Trace = new List<Operation>();
        public void Execute(Dictionary<Operation, Outcome> failures)
        {
            for (int budget = 0; budget < 45; budget++)
            {
                Operation? next = Model.Begin(); if (!next.HasValue) return;
                Operation op = next.Value;
                Assert(!Trace.Contains(op), "operation repeated"); Trace.Add(op);
                if (op == Operation.CreatePublisher || op == Operation.CreatePeer)
                {
                    Assert(Model.AccountDisabledConfirmed && Model.State(Resource.Secret) == Ownership.Released, "launch before disable/zeroization");
                    Assert(Model.State(Resource.Job) == Ownership.Owned, "launch outside owned job");
                    Assert(!Model.PrimaryFailure.HasValue, "new launch after primary failure");
                }
                if (op == Operation.ResumePublisher || op == Operation.ResumePeer)
                    Assert(Trace.Contains(Operation.VerifyWorkers) && Model.State(Resource.Publisher) == Ownership.Owned && Model.State(Resource.Peer) == Ownership.Owned, "resume before both workers verified");
                if (op == Operation.CloseCode || op == Operation.CloseAncestors)
                {
                    if (Trace.Contains(Operation.CreatePublisher)) Assert(Model.ExitObserved && Model.JobEmptyConfirmed, "released protection before exit/empty proof");
                    foreach (Resource child in new Resource[] { Resource.Peer, Resource.Publisher, Resource.Token, Resource.Ipc, Resource.Job, Resource.Secret })
                        Assert(Model.State(child) == Ownership.Absent || Model.State(child) == Ownership.Released, "released protection with unresolved child");
                }
                Outcome outcome;
                Model.Complete(op, failures.TryGetValue(op, out outcome) ? outcome : Outcome.Confirmed);
                Assert(!Model.NativeLaunchAuthorized && !Model.IsolationCertified, "model granted native permission");
            }
            throw new Exception("unbounded protocol");
        }
    }
    private static Dictionary<Operation, Outcome> Failure(Operation op, Outcome outcome)
    { Dictionary<Operation, Outcome> result = new Dictionary<Operation, Outcome>(); result.Add(op, outcome); return result; }
    public static int Main()
    {
        try
        {
            Run success = new Run(); success.Execute(new Dictionary<Operation, Outcome>());
            Test("success disables and erases before launch, then drains before outer close", delegate { Assert(success.Model.ModelSucceeded && success.Model.ContainmentComplete && success.Trace.Count == 26, "incomplete normal path"); });
            foreach (Operation failed in success.Trace)
            {
                foreach (Outcome outcome in new Outcome[] { Outcome.NoEffectFailure, Outcome.Unknown })
                {
                    Operation primary = failed; Outcome result = outcome;
                    Test("bounded failure " + primary + " " + result, delegate
                    {
                        Run run = new Run(); run.Execute(Failure(primary, result));
                        Assert(run.Model.Finished && !run.Model.ModelSucceeded && run.Model.PrimaryFailure == primary && run.Model.PrimaryOutcome == result, "primary failure lost");
                        int index = run.Trace.IndexOf(primary);
                        for (int i = index + 1; i < run.Trace.Count; i++)
                            Assert(run.Trace[i] != Operation.EnableAccount && run.Trace[i] != Operation.Logon && run.Trace[i] != Operation.CreatePublisher && run.Trace[i] != Operation.CreatePeer && run.Trace[i] != Operation.ResumePublisher && run.Trace[i] != Operation.ResumePeer, "new work after failure");
                    });
                }
            }
            Test("unknown enable still disables and verifies exactly once", delegate
            {
                Run run = new Run(); run.Execute(Failure(Operation.EnableAccount, Outcome.Unknown));
                int enable = run.Trace.IndexOf(Operation.EnableAccount);
                Assert(run.Trace[enable + 1] == Operation.DisableAccount && run.Trace[enable + 2] == Operation.VerifyDisabled && run.Model.AccountDisabledConfirmed, "missed disable obligation");
                Assert(!run.Trace.Contains(Operation.Logon) && run.Model.ContainmentComplete, "unsafe continuation");
            });
            Test("disable request success alone is not confirmation", delegate
            {
                Run run = new Run(); run.Execute(Failure(Operation.VerifyDisabled, Outcome.Unknown));
                Assert(!run.Model.AccountDisabledConfirmed && !run.Model.ContainmentComplete && !run.Trace.Contains(Operation.CreatePublisher), "assumed disabled");
            });
            Test("unknown logon retains token uncertainty after account disable", delegate
            {
                Run run = new Run(); run.Execute(Failure(Operation.Logon, Outcome.Unknown));
                Assert(run.Model.AccountDisabledConfirmed && run.Model.State(Resource.Token) == Ownership.Unknown && !run.Trace.Contains(Operation.CloseAncestors), "disable treated as token revocation");
            });
            Test("secret release failure prevents launch and outer release", delegate
            {
                Run run = new Run(); run.Execute(Failure(Operation.EraseSecret, Outcome.Unknown));
                Assert(!run.Trace.Contains(Operation.CreatePublisher) && !run.Trace.Contains(Operation.CloseAncestors) && !run.Model.ContainmentComplete, "unreleased secret ignored");
            });
            Test("unknown child creation needs containment and retains unknown handle ownership", delegate
            {
                Run run = new Run(); run.Execute(Failure(Operation.CreatePeer, Outcome.Unknown));
                Assert(run.Trace.Contains(Operation.TerminateJob) && run.Model.ExitObserved && run.Model.JobEmptyConfirmed, "no job containment");
                Assert(!run.Trace.Contains(Operation.ClosePeer) && !run.Trace.Contains(Operation.CloseAncestors) && !run.Model.ContainmentComplete, "unknown handle guessed closed");
            });
            foreach (Operation secondary in new Operation[] { Operation.TerminateJob, Operation.ObserveExitAfterStop, Operation.VerifyEmptyAfterStop })
            {
                Operation stopFailure = secondary;
                Test("timeout plus containment failure " + stopFailure, delegate
                {
                    Dictionary<Operation, Outcome> failures = Failure(Operation.ObserveWorkersExit, Outcome.Unknown); failures.Add(stopFailure, Outcome.Unknown);
                    Run run = new Run(); run.Execute(failures);
                    Assert(run.Model.PrimaryFailure == Operation.ObserveWorkersExit && run.Model.SecondaryFailures.Length == 1 && run.Model.SecondaryFailures[0] == stopFailure, "failure precedence");
                    if (stopFailure == Operation.TerminateJob)
                        Assert(run.Model.ContainmentComplete, "exit and job-empty proof should permit release despite failed stop request");
                    else Assert(!run.Model.ContainmentComplete && !run.Trace.Contains(Operation.CloseAncestors), "stop request mistaken for exit proof");
                });
            }
            Test("secondary disable failure preserves original and does not retry", delegate
            {
                Dictionary<Operation, Outcome> failures = Failure(Operation.Logon, Outcome.NoEffectFailure); failures.Add(Operation.DisableAccount, Outcome.Unknown);
                Run run = new Run(); run.Execute(failures);
                Assert(run.Model.PrimaryFailure == Operation.Logon && run.Model.SecondaryFailures.Length == 1 && run.Trace.Contains(Operation.VerifyDisabled) && run.Model.AccountDisabledConfirmed, "missing independent verification");
            });
            Test("failed close stops all enclosing close attempts", delegate
            {
                Run run = new Run(); run.Execute(Failure(Operation.ClosePeer, Outcome.Unknown));
                Assert(run.Trace[run.Trace.Count - 1] == Operation.ClosePeer && !run.Model.ContainmentComplete, "continued close after unknown release");
            });
            Test("fixed bookkeeping records every secondary failure without dynamic collection growth", delegate
            {
                Dictionary<Operation, Outcome> failures = Failure(Operation.CreatePeer, Outcome.Unknown);
                failures.Add(Operation.TerminateJob, Outcome.Unknown);
                failures.Add(Operation.ObserveExitAfterStop, Outcome.Unknown);
                failures.Add(Operation.VerifyEmptyAfterStop, Outcome.Unknown);
                Run run = new Run(); run.Execute(failures);
                Operation[] saved = run.Model.SecondaryFailures;
                Assert(saved.Length == 3 && saved[0] == Operation.TerminateJob && saved[1] == Operation.ObserveExitAfterStop && saved[2] == Operation.VerifyEmptyAfterStop, "lost secondary record");
                saved[0] = Operation.Preflight;
                Assert(run.Model.SecondaryFailures[0] == Operation.TerminateJob, "caller changed failure ledger");
                Assert((int)Operation.CloseAncestors < 64 && !run.Model.ContainmentComplete, "bitset capacity or false completion");
            });
            Test("pending, mismatched, duplicate and terminal completions are rejected", delegate
            {
                Lifecycle model = new Lifecycle();
                Reject(delegate { model.Complete(Operation.Preflight, Outcome.Confirmed); });
                Assert(model.Begin() == Operation.Preflight, "first operation");
                Reject(delegate { model.Begin(); });
                Reject(delegate { model.Complete(Operation.HoldCode, Outcome.Confirmed); });
                Reject(delegate { model.Complete(Operation.Preflight, (Outcome)99); });
                Assert(!model.ContainmentComplete && !model.ModelSucceeded, "pending reply counted complete");
                model.Complete(Operation.Preflight, Outcome.Unknown);
                Reject(delegate { model.Complete(Operation.Preflight, Outcome.Confirmed); });
                Assert(!model.Begin().HasValue, "unexpected cleanup without resources");
                Reject(delegate { model.Begin(); });
            });
            Console.WriteLine("RESULT passed=" + count + " native_calls=0 isolation_certified=false"); return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
