// Pure protocol model: no native adapter, credentials, handles, or OS calls.
using System;

namespace Banto.PrincipalWorker
{
    public enum Operation
    {
        Preflight, HoldAncestors, HoldCode, PrepareIpc, CreateJob, AllocateSecret,
        ResetDisabledAccount, EnableAccount, Logon, DisableAccount, VerifyDisabled,
        EraseSecret, CreatePublisher, CreatePeer, VerifyWorkers, ResumePublisher,
        ResumePeer, ObserveWorkersExit, VerifyJobEmpty,
        TerminateJob, ObserveExitAfterStop, VerifyEmptyAfterStop,
        ClosePeer, ClosePublisher, CloseToken, CloseIpc, CloseJob, CloseCode, CloseAncestors
    }
    public enum Outcome { Confirmed, NoEffectFailure, Unknown }
    public enum Resource { Ancestors, Code, Ipc, Job, Secret, Token, Publisher, Peer }
    public enum Ownership { Absent, Owned, Unknown, Released }

    // Confirmed means the complete operation-specific postcondition in the design.
    // NoEffectFailure is allowed only with proof of zero side effects. Exceptions,
    // partial acquisitions and lost replies must be reported as Unknown.
    public sealed class Lifecycle
    {
        private static readonly Operation[] Normal = {
            Operation.Preflight, Operation.HoldAncestors, Operation.HoldCode,
            Operation.PrepareIpc, Operation.CreateJob, Operation.AllocateSecret,
            Operation.ResetDisabledAccount, Operation.EnableAccount, Operation.Logon,
            Operation.DisableAccount, Operation.VerifyDisabled, Operation.EraseSecret,
            Operation.CreatePublisher, Operation.CreatePeer, Operation.VerifyWorkers,
            Operation.ResumePublisher, Operation.ResumePeer, Operation.ObserveWorkersExit,
            Operation.VerifyJobEmpty, Operation.ClosePeer, Operation.ClosePublisher,
            Operation.CloseToken, Operation.CloseIpc, Operation.CloseJob,
            Operation.CloseCode, Operation.CloseAncestors
        };
        private static readonly Operation[] Containment = {
            Operation.DisableAccount, Operation.VerifyDisabled, Operation.EraseSecret,
            Operation.TerminateJob, Operation.ObserveExitAfterStop, Operation.VerifyEmptyAfterStop,
            Operation.ClosePeer, Operation.ClosePublisher, Operation.CloseToken,
            Operation.CloseIpc, Operation.CloseJob, Operation.CloseCode, Operation.CloseAncestors
        };
        private readonly Ownership[] ownership = new Ownership[8];
        // All bookkeeping storage is allocated before the instance can be used.
        // Successful Begin/Complete/Needed paths perform no managed allocation.
        private ulong attempted;
        private readonly Operation[] secondary = new Operation[(int)Operation.CloseAncestors + 1];
        private static readonly Resource[] Children = { Resource.Peer, Resource.Publisher, Resource.Token, Resource.Ipc, Resource.Secret };
        private int normalIndex, containmentIndex, secondaryCount;
        private bool pending, enabledAttempted, spawnAttempted, closeFailed;
        private Operation pendingOperation;
        public Operation? PrimaryFailure { get; private set; }
        public Outcome? PrimaryOutcome { get; private set; }
        public Operation[] SecondaryFailures
        {
            get { Operation[] copy = new Operation[secondaryCount]; Array.Copy(secondary, copy, secondaryCount); return copy; }
        }
        public bool AccountDisabledConfirmed { get; private set; }
        public bool ExitObserved { get; private set; }
        public bool JobEmptyConfirmed { get; private set; }
        public bool Finished { get; private set; }
        public bool ModelSucceeded { get { return Finished && !PrimaryFailure.HasValue && ContainmentComplete; } }
        public bool ContainmentComplete
        {
            get
            {
                if (pending || !Finished || (enabledAttempted && !AccountDisabledConfirmed)) return false;
                if (spawnAttempted && !(ExitObserved && JobEmptyConfirmed)) return false;
                foreach (Ownership state in ownership)
                    if (state == Ownership.Owned || state == Ownership.Unknown) return false;
                return true;
            }
        }
        // Pure model results can never authorize native work or formal acceptance.
        public bool NativeLaunchAuthorized { get { return false; } }
        public bool IsolationCertified { get { return false; } }
        public Ownership State(Resource resource) { return ownership[(int)resource]; }
        private static Resource? Acquires(Operation operation)
        {
            switch (operation)
            {
                case Operation.HoldAncestors: return Resource.Ancestors;
                case Operation.HoldCode: return Resource.Code;
                case Operation.PrepareIpc: return Resource.Ipc;
                case Operation.CreateJob: return Resource.Job;
                case Operation.AllocateSecret: return Resource.Secret;
                case Operation.Logon: return Resource.Token;
                case Operation.CreatePublisher: return Resource.Publisher;
                case Operation.CreatePeer: return Resource.Peer;
                default: return null;
            }
        }
        private static Resource? Releases(Operation operation)
        {
            switch (operation)
            {
                case Operation.EraseSecret: return Resource.Secret;
                case Operation.ClosePeer: return Resource.Peer;
                case Operation.ClosePublisher: return Resource.Publisher;
                case Operation.CloseToken: return Resource.Token;
                case Operation.CloseIpc: return Resource.Ipc;
                case Operation.CloseJob: return Resource.Job;
                case Operation.CloseCode: return Resource.Code;
                case Operation.CloseAncestors: return Resource.Ancestors;
                default: return null;
            }
        }
        private bool Needed(Operation operation)
        {
            if ((attempted & (1UL << (int)operation)) != 0) return false;
            if (operation == Operation.DisableAccount || operation == Operation.VerifyDisabled)
                return enabledAttempted && !AccountDisabledConfirmed;
            if (operation == Operation.EraseSecret)
                return State(Resource.Secret) == Ownership.Owned; // Unknown allocations cannot be guessed/freed.
            if (operation == Operation.TerminateJob || operation == Operation.ObserveExitAfterStop || operation == Operation.VerifyEmptyAfterStop)
                return spawnAttempted && !(ExitObserved && JobEmptyConfirmed);
            Resource? resource = Releases(operation);
            if (!resource.HasValue || closeFailed || State(resource.Value) != Ownership.Owned) return false;
            if (spawnAttempted && !(ExitObserved && JobEmptyConfirmed)) return false;
            // No outer release while a child acquisition/close is unresolved.
            if (resource.Value == Resource.Job || resource.Value == Resource.Code || resource.Value == Resource.Ancestors)
            {
                foreach (Resource child in Children)
                    if (State(child) == Ownership.Owned || State(child) == Ownership.Unknown) return false;
                if (resource.Value != Resource.Job && (State(Resource.Job) == Ownership.Owned || State(Resource.Job) == Ownership.Unknown)) return false;
                if (resource.Value == Resource.Ancestors && (State(Resource.Code) == Ownership.Owned || State(Resource.Code) == Ownership.Unknown)) return false;
            }
            return true;
        }
        // Begin records the possible effect BEFORE dispatch. If an adapter fails to
        // report completion, the pending operation cannot be repeated or bypassed.
        public Operation? Begin()
        {
            if (pending || Finished) throw new InvalidOperationException("single attempt protocol");
            Operation operation;
            if (!PrimaryFailure.HasValue)
            {
                if (normalIndex == Normal.Length) { Finished = true; return null; }
                operation = Normal[normalIndex++];
            }
            else
            {
                while (containmentIndex < Containment.Length && !Needed(Containment[containmentIndex])) containmentIndex++;
                if (containmentIndex == Containment.Length) { Finished = true; return null; }
                operation = Containment[containmentIndex++];
            }
            // The fixed schedule and Needed filter make this a non-allocating bit update.
            attempted |= 1UL << (int)operation;
            if (operation == Operation.EnableAccount) { enabledAttempted = true; AccountDisabledConfirmed = false; }
            if (operation == Operation.CreatePublisher || operation == Operation.CreatePeer) spawnAttempted = true;
            pendingOperation = operation; pending = true;
            return operation;
        }
        public void Complete(Operation operation, Outcome outcome)
        {
            if (!pending || pendingOperation != operation || outcome < Outcome.Confirmed || outcome > Outcome.Unknown)
                throw new InvalidOperationException("unexpected completion");
            pending = false;
            bool confirmed = outcome == Outcome.Confirmed;
            Resource? acquired = Acquires(operation), released = Releases(operation);
            if (acquired.HasValue)
                ownership[(int)acquired.Value] = confirmed ? Ownership.Owned : outcome == Outcome.Unknown ? Ownership.Unknown : Ownership.Absent;
            if (released.HasValue)
            {
                if (confirmed) ownership[(int)released.Value] = Ownership.Released;
                else if (outcome == Outcome.Unknown) ownership[(int)released.Value] = Ownership.Unknown;
                if (!confirmed && operation != Operation.EraseSecret) closeFailed = true;
            }
            if (confirmed)
            {
                if (operation == Operation.Preflight || operation == Operation.VerifyDisabled) AccountDisabledConfirmed = true;
                if (operation == Operation.ObserveWorkersExit || operation == Operation.ObserveExitAfterStop) ExitObserved = true;
                if (operation == Operation.VerifyJobEmpty || operation == Operation.VerifyEmptyAfterStop) JobEmptyConfirmed = true;
            }
            else if (!PrimaryFailure.HasValue) { PrimaryFailure = operation; PrimaryOutcome = outcome; }
            else secondary[secondaryCount++] = operation; // At most one entry per fixed operation.
        }
    }
}
