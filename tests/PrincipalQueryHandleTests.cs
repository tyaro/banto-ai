using System;
using System.ComponentModel;

public static class PrincipalQueryHandleTests
{
    private sealed class Backend : IQueryHandleBackend
    {
        public IntPtr Output = new IntPtr(731);
        public bool OpenResult = true, CloseResult = true, ThrowOpen, ThrowClose;
        public int OpenCalls, CloseCalls;
        public int LastError { get { return 5; } }
        public bool Open(out IntPtr handle)
        { OpenCalls++; handle = Output; if (ThrowOpen) throw new Win32Exception(1234); return OpenResult; }
        public bool Close(IntPtr handle)
        { if (handle != Output) throw new Exception("wrong handle"); CloseCalls++; if (ThrowClose) throw new Win32Exception(4321); return CloseResult; }
    }
    private static int count;
    private static void Assert(bool value, string reason) { if (!value) throw new Exception(reason); }
    private static void Reject(Action body) { bool rejected = false; try { body(); } catch (InvalidOperationException) { rejected = true; } catch (Win32Exception) { rejected = true; } Assert(rejected, "accepted invalid lease"); }
    private static void Test(string name, Action body) { body(); count++; Console.WriteLine("PASS " + name); }
    public static int Main()
    {
        try
        {
            Test("only confirmed output is exposed and closed once", delegate
            {
                Backend b = new Backend(); QueryHandleLease lease = new QueryHandleLease(b);
                Reject(delegate { IntPtr value = lease.Handle; }); lease.ReleaseOnce(); Assert(b.CloseCalls == 0, "closed before acquisition");
                lease.Acquire(); Assert(lease.Handle == b.Output && lease.Acquired && !lease.AcquisitionUnknown, "ownership");
                lease.ReleaseOnce(); lease.ReleaseOnce(); Reject(lease.Acquire); Reject(delegate { IntPtr value = lease.Handle; });
                Assert(b.OpenCalls == 1 && b.CloseCalls == 1 && lease.Closed && !lease.ReleaseError.HasValue, "duplicate calls");
            });
            foreach (bool throws in new bool[] { false, true })
            {
                bool throwOpen = throws;
                Test("unconfirmed nonzero output is never closed, exception=" + throwOpen, delegate
                {
                    Backend b = new Backend(); b.OpenResult = false; b.ThrowOpen = throwOpen;
                    QueryHandleLease lease = new QueryHandleLease(b); Reject(lease.Acquire); lease.ReleaseOnce(); Reject(lease.Acquire);
                    Assert(!lease.Acquired && lease.AcquisitionUnknown && !lease.Closed && b.CloseCalls == 0 && b.OpenCalls == 1, "guessed unknown output ownership");
                });
            }
            foreach (long invalid in new long[] { 0, -1 })
            {
                long value = invalid;
                Test("invalid successful handle remains unresolved " + value, delegate
                {
                    Backend b = new Backend(); b.Output = new IntPtr(value);
                    QueryHandleLease lease = new QueryHandleLease(b); Reject(lease.Acquire); lease.ReleaseOnce();
                    Assert(lease.AcquisitionUnknown && !lease.Acquired && b.CloseCalls == 0, "closed invalid output");
                });
            }
            foreach (bool throws in new bool[] { false, true })
            {
                bool throwClose = throws;
                Test("release failure cannot mask primary or skip other owned close, exception=" + throwClose, delegate
                {
                    Backend first = new Backend(), second = new Backend(); first.CloseResult = false; first.ThrowClose = throwClose;
                    QueryHandleLease linked = new QueryHandleLease(first), own = new QueryHandleLease(second);
                    linked.Acquire(); own.Acquire();
                    int? primary = null;
                    try { throw new Win32Exception(1314); }
                    catch (Win32Exception error) { primary = error.NativeErrorCode; }
                    finally { linked.ReleaseOnce(); own.ReleaseOnce(); }
                    linked.ReleaseOnce(); own.ReleaseOnce();
                    Assert(primary == 1314 && linked.ReleaseError == (throwClose ? 4321 : 5) && !linked.Closed && own.Closed, "primary/secondary or second release lost");
                    Assert(first.CloseCalls == 1 && second.CloseCalls == 1, "release retry");
                });
            }
            Test("both release exceptions retained independently", delegate
            {
                Backend a = new Backend(), b = new Backend(); a.ThrowClose = true; b.CloseResult = false;
                QueryHandleLease first = new QueryHandleLease(a), second = new QueryHandleLease(b);
                first.Acquire(); second.Acquire(); first.ReleaseOnce(); second.ReleaseOnce();
                Assert(first.ReleaseError == 4321 && second.ReleaseError == 5 && !first.Closed && !second.Closed, "lost release errors");
            });
            Console.WriteLine("RESULT passed=" + count + " native_calls=0"); return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
