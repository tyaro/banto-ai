// Pure state/ABI fault tests. No native privilege, token, account or root operation.
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.InteropServices;
using Banto.PrincipalSetup;

public static class PrincipalPrivilegeTests
{
    private sealed class Backend : IPrivilegeBackend
    {
        public readonly List<string> Calls = new List<string>();
        public bool Enabled, IgnoreAdjustment;
        public int FailAt;
        private void Call(string name) { Calls.Add(name); if (Calls.Count == FailAt) throw new Win32Exception(5); }
        public bool ReadEnabled() { Call("read"); return Enabled; }
        public void SetEnabled(bool enabled) { Call(enabled ? "enable" : "restore"); if (!IgnoreAdjustment) Enabled = enabled; }
    }
    private static int count;
    private static void Assert(bool value, string reason) { if (!value) throw new Exception(reason); }
    private static void Test(string name, Action body) { body(); count++; Console.WriteLine("PASS " + name); }
    private static void Reject(Action body) { bool rejected = false; try { body(); } catch { rejected = true; } Assert(rejected, "accepted invalid operation"); }
    private static byte[] Record(uint low, int high, uint flags)
    {
        byte[] bytes = new byte[16]; Buffer.BlockCopy(BitConverter.GetBytes(1U), 0, bytes, 0, 4);
        Buffer.BlockCopy(BitConverter.GetBytes(low), 0, bytes, 4, 4); Buffer.BlockCopy(BitConverter.GetBytes(high), 0, bytes, 8, 4);
        Buffer.BlockCopy(BitConverter.GetBytes(flags), 0, bytes, 12, 4); return bytes;
    }
    public static int Main()
    {
        try
        {
            Test("disabled privilege is enabled, verified, restored, verified once", delegate()
            {
                Backend b = new Backend(); PrivilegeLease lease = new PrivilegeLease(b);
                lease.Enable(); Assert(b.Enabled, "not enabled"); lease.Restore(); Assert(!b.Enabled, "not restored");
                Assert(String.Join(",", b.Calls.ToArray()) == "read,enable,read,restore,read", "sequence");
                int before = b.Calls.Count; Reject(lease.Enable); Reject(lease.Restore); Assert(b.Calls.Count == before, "retry backend call");
            });
            Test("already enabled privilege is preserved without adjustment", delegate()
            {
                Backend b = new Backend(); b.Enabled = true; PrivilegeLease lease = new PrivilegeLease(b); lease.Enable(); lease.Restore();
                Assert(b.Enabled && String.Join(",", b.Calls.ToArray()) == "read,read,read", "changed existing privilege");
            });
            Test("restore before enable never touches backend", delegate()
            {
                Backend b = new Backend(); PrivilegeLease lease = new PrivilegeLease(b); Reject(lease.Restore); Assert(b.Calls.Count == 0, "early restore");
            });
            for (int step = 1; step <= 5; step++)
            {
                int failure = step;
                Test("failure at lifecycle operation " + failure + " cannot retry", delegate()
                {
                    Backend b = new Backend(); b.FailAt = failure; PrivilegeLease lease = new PrivilegeLease(b);
                    bool caught = false;
                    try { lease.Enable(); lease.Restore(); } catch (Win32Exception error) { caught = error.NativeErrorCode == 5; }
                    Assert(caught && b.Calls.Count == failure, "primary operation failure");
                    Reject(lease.Enable); Reject(lease.Restore); Assert(b.Calls.Count == failure, "retried failed lifecycle");
                });
            }
            Test("missing enable change is rejected", delegate()
            {
                Backend b = new Backend(); b.IgnoreAdjustment = true; PrivilegeLease lease = new PrivilegeLease(b);
                Reject(lease.Enable); Reject(lease.Restore); Assert(b.Calls.Count == 3, "continued after unconfirmed enable");
            });
            Test("missing restore change is rejected", delegate()
            {
                Backend b = new Backend(); PrivilegeLease lease = new PrivilegeLease(b); lease.Enable(); b.IgnoreAdjustment = true;
                Reject(lease.Restore); Reject(lease.Restore); Assert(b.Calls.Count == 5, "continued after unconfirmed restore");
            });
            Test("TRUE and ERROR_NOT_ALL_ASSIGNED remains failure", delegate()
            {
                bool caught = false; try { PrivilegeLease.RequireAdjusted(true, 1300); } catch (Win32Exception e) { caught = e.NativeErrorCode == 1300; }
                Assert(caught, "partial adjustment accepted"); PrivilegeLease.RequireAdjusted(true, 0);
                Reject(delegate { PrivilegeLease.RequireAdjusted(false, 0); }); Reject(delegate { PrivilegeLease.RequireAdjusted(false, 5); });
            });
            Test("native one-privilege structure has correct Win64 offsets", delegate()
            {
                Assert(Marshal.SizeOf(typeof(Native.LUID)) == 8 && Marshal.SizeOf(typeof(Native.TOKEN_PRIVILEGES_ONE)) == 16, "ABI size");
                Assert(Marshal.OffsetOf(typeof(Native.TOKEN_PRIVILEGES_ONE), "Luid").ToInt32() == 4 && Marshal.OffsetOf(typeof(Native.TOKEN_PRIVILEGES_ONE), "Attributes").ToInt32() == 12, "ABI offset");
            });
            Native.LUID target = new Native.LUID(); target.Low = 8; target.High = 2;
            Test("parser matches full LUID and preserves enabled state", delegate()
            {
                Assert(!PrivilegeLease.ReadEnabled(Record(8, 2, 1), target), "disabled");
                Assert(PrivilegeLease.ReadEnabled(Record(8, 2, 0x80000003), target), "enabled");
                Reject(delegate { PrivilegeLease.ReadEnabled(Record(8, 3, 2), target); });
            });
            Test("missing privilege is reported before any adjustment", delegate()
            {
                bool caught = false; try { PrivilegeLease.ReadEnabled(new byte[4], target); } catch (Win32Exception e) { caught = e.NativeErrorCode == 1314; }
                Assert(caught, "missing privilege status");
            });
            Test("parser rejects short oversized count-overflow duplicate and removed responses", delegate()
            {
                foreach (byte[] bytes in new byte[][] { null, new byte[3], new byte[4097], new byte[] { 255, 255, 255, 255 }, Record(8, 2, 4) })
                { byte[] value = bytes; Reject(delegate { PrivilegeLease.ReadEnabled(value, target); }); }
                byte[] duplicate = new byte[28]; duplicate[0] = 2;
                Buffer.BlockCopy(Record(8, 2, 2), 4, duplicate, 4, 12); Buffer.BlockCopy(Record(8, 2, 2), 4, duplicate, 16, 12);
                Reject(delegate { PrivilegeLease.ReadEnabled(duplicate, target); });
            });
            Console.WriteLine("RESULT " + count + " passed; OS mutations=0; no native privilege adjustment"); return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error.GetType().Name + ": " + error.Message); return 1; }
    }
}
