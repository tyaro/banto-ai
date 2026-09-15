// Preflight-only engineering diagnostic. The caller must exit immediately.
using System;
using System.ComponentModel;
using System.Threading;
using Banto.PrincipalSetup;

namespace Banto.PrincipalPreflight
{
    public sealed class DiagnosticSequence
    {
        private bool started;
        public Phase Current { get; private set; }
        public int Run(IBackend backend)
        {
            if (started) throw new InvalidOperationException("diagnostic cannot be reused");
            started = true;
            FailureState failure = backend.Failure;
            try
            {
                foreach (Phase phase in new Phase[] { Phase.Preflight, Phase.ClosePeerToken,
                    Phase.CloseLinkedToken, Phase.CloseAdminToken, Phase.StopWatchdog })
                {
                    Current = phase;
                    backend.Execute(phase);
                }
                return 0;
            }
            catch (Exception error)
            {
                // No further calls after failure. Raw handles remain rooted to process exit.
                Win32Exception native = error as Win32Exception;
                int detail = Object.ReferenceEquals(error, failure.ReleaseStop) ? unchecked((int)failure.ReleaseError) :
                    native == null ? 65535 : native.NativeErrorCode;
                if (detail <= 0 || detail > 65534) detail = 65535;
                return ((int)Current << 16) | detail | (failure.ReleaseFailed ? 0x40000000 : 0);
            }
        }
    }
    public static class Entry
    {
        private static int started;
        private static NativeBackend live;
        public static int Run()
        {
            if (Interlocked.Exchange(ref started, 1) != 0)
                throw new InvalidOperationException("diagnostic entry cannot be reused");
            live = new NativeBackend();
            return new DiagnosticSequence().Run(live);
        }
    }
}
