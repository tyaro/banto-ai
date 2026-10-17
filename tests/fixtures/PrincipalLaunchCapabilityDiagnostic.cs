// Fixed, read-only normal-U token diagnostic. No elevation or account operations.
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
using Banto.PrincipalSetup;

public interface IQueryHandleBackend
{
    bool Open(out IntPtr handle);
    bool Close(IntPtr handle);
    int LastError { get; }
}
// Separate acquisition confirmation from untrusted/partial out parameters.
public sealed class QueryHandleLease
{
    private readonly IQueryHandleBackend backend;
    private bool attempted, releaseAttempted;
    private IntPtr handle;
    public bool Acquired { get; private set; }
    public bool AcquisitionUnknown { get; private set; }
    public bool Closed { get; private set; }
    public int? ReleaseError { get; private set; }
    public IntPtr Handle { get { if (!Acquired || releaseAttempted) throw new InvalidOperationException("no owned query handle"); return handle; } }
    public QueryHandleLease(IQueryHandleBackend value) { if (value == null) throw new ArgumentNullException("value"); backend = value; }
    public void Acquire()
    {
        if (attempted) throw new InvalidOperationException("no acquisition retry");
        attempted = true;
        IntPtr output = IntPtr.Zero;
        try
        {
            if (!backend.Open(out output)) throw new Win32Exception(backend.LastError);
            if (output == IntPtr.Zero || output == new IntPtr(-1)) throw new InvalidOperationException("invalid query handle");
            handle = output; Acquired = true;
        }
        catch { AcquisitionUnknown = true; throw; }
    }
    public void ReleaseOnce()
    {
        if (!Acquired || releaseAttempted) return;
        releaseAttempted = true;
        try
        {
            Closed = backend.Close(handle);
            if (!Closed) ReleaseError = backend.LastError;
        }
        catch (Exception error)
        {
            Win32Exception native = error as Win32Exception;
            ReleaseError = native == null ? -1 : native.NativeErrorCode;
        }
    }
}

public static class PrincipalLaunchCapabilityDiagnostic
{
    private const string ExpectedUser = "S-1-5-21-2169670816-255940906-2713565042-1001";
    private static void Check(bool ok) { if (!ok) throw new Win32Exception(Marshal.GetLastWin32Error()); }
    private static byte[] Query(IntPtr token, int kind, uint capacity)
    {
        IntPtr buffer = Marshal.AllocHGlobal((int)capacity);
        try
        {
            uint needed; Check(Native.GetTokenInformation(token, kind, buffer, capacity, out needed));
            if (needed < 4 || needed > capacity) throw new InvalidOperationException("query length");
            byte[] bytes = new byte[needed]; Marshal.Copy(buffer, bytes, 0, (int)needed); return bytes;
        }
        finally { Marshal.FreeHGlobal(buffer); }
    }
    private static int Scalar(IntPtr token, int kind)
    {
        byte[] bytes = Query(token, kind, 4);
        if (bytes.Length != 4) throw new InvalidOperationException("scalar length");
        return BitConverter.ToInt32(bytes, 0);
    }
    private static void RequireUser(IntPtr token)
    {
        // TOKEN_USER contains a pointer into this buffer, so parse before freeing it.
        IntPtr buffer = Marshal.AllocHGlobal(512);
        try
        {
            uint needed; Check(Native.GetTokenInformation(token, 1, buffer, 512, out needed));
            if (needed < 16 || needed > 512) throw new InvalidOperationException("user size");
            IntPtr sid = Marshal.ReadIntPtr(buffer);
            long offset = sid.ToInt64() - buffer.ToInt64();
            if (offset < 16 || offset > needed - 8) throw new InvalidOperationException("user pointer");
            int length = 8 + Marshal.ReadByte(sid, 1) * 4;
            if (length > needed - offset) throw new InvalidOperationException("user SID size");
            byte[] bytes = new byte[length]; Marshal.Copy(sid, bytes, 0, length);
            if (new System.Security.Principal.SecurityIdentifier(bytes, 0).Value != ExpectedUser)
                throw new InvalidOperationException("unexpected user");
        }
        finally { Marshal.FreeHGlobal(buffer); }
    }
    private static void NonInherit(IntPtr token)
    { uint flags; Check(Native.GetHandleInformation(token, out flags)); if ((flags & 1) != 0) throw new InvalidOperationException("inherited token"); }
    private static int FailureCode(Exception error)
    { Win32Exception native = error as Win32Exception; return native == null ? -1 : native.NativeErrorCode; }
    private sealed class QueryBackend : IQueryHandleBackend
    {
        public IntPtr LinkedParent;
        public int LastError { get { return Marshal.GetLastWin32Error(); } }
        public bool Open(out IntPtr output)
        {
            output = IntPtr.Zero;
            if (LinkedParent == IntPtr.Zero) return Native.OpenProcessToken(Native.GetCurrentProcess(), 8, out output);
            IntPtr buffer = Marshal.AllocHGlobal(IntPtr.Size);
            try
            {
                uint needed;
                Check(Native.GetTokenInformation(LinkedParent, 19, buffer, (uint)IntPtr.Size, out needed));
                output = Marshal.ReadIntPtr(buffer);
                if (needed != IntPtr.Size || output == LinkedParent) throw new InvalidOperationException("linked handle shape");
                return true;
            }
            finally { Marshal.FreeHGlobal(buffer); }
        }
        public bool Close(IntPtr value) { return Native.CloseHandle(value); }
    }
    public static int Main()
    {
        QueryBackend linkedBackend = new QueryBackend();
        QueryHandleLease own = new QueryHandleLease(new QueryBackend()), linked = new QueryHandleLease(linkedBackend);
        bool complete = false;
        int? primary = null;
        string stage = "preflight";
        StringBuilder privileges = new StringBuilder();
        try
        {
            if (IntPtr.Size != 8 || Environment.OSVersion.Platform != PlatformID.Win32NT) throw new InvalidOperationException("Win64 required");
            stage = "open-own-query"; own.Acquire();
            stage = "verify-own"; NonInherit(own.Handle); RequireUser(own.Handle);
            if (Scalar(own.Handle, 20) != 0 || Scalar(own.Handle, 18) != 3) throw new InvalidOperationException("limited U required");
            stage = "get-linked";
            linkedBackend.LinkedParent = own.Handle; linked.Acquire();
            stage = "verify-linked"; NonInherit(linked.Handle); RequireUser(linked.Handle);
            if (Scalar(linked.Handle, 20) != 1 || Scalar(linked.Handle, 18) != 2) throw new InvalidOperationException("full linked token required");
            stage = "query-linked-privileges"; byte[] values = Query(linked.Handle, 3, 4096);
            foreach (string name in new string[] { "SeIncreaseQuotaPrivilege", "SeAssignPrimaryTokenPrivilege", "SeImpersonatePrivilege" })
            {
                Native.LUID luid; Check(Native.LookupPrivilegeValueW(null, name, out luid));
                bool present = true, enabled = false;
                try { enabled = PrivilegeLease.ReadEnabled(values, luid); }
                catch (Win32Exception error) { if (error.NativeErrorCode != 1314) throw; present = false; }
                if (privileges.Length != 0) privileges.Append(',');
                privileges.Append("{\"name\":\"").Append(name).Append("\",\"present\":").Append(present ? "true" : "false")
                    .Append(",\"enabled\":").Append(present ? (enabled ? "true" : "false") : "null").Append('}');
            }
            stage = "close"; complete = true;
        }
        catch (Exception error) { primary = FailureCode(error); }
        finally
        {
            linked.ReleaseOnce(); own.ReleaseOnce();
        }
        int? release = linked.ReleaseError ?? own.ReleaseError;
        bool success = complete && own.Closed && linked.Closed && !primary.HasValue && !release.HasValue;
        Console.WriteLine("{\"utc\":\"" + DateTime.UtcNow.ToString("o") + "\",\"query_complete\":" + (success ? "true" : "false")
            + ",\"stage\":\"" + stage + "\",\"primary_error\":" + (primary.HasValue ? primary.Value.ToString() : "null")
            + ",\"release_error\":" + (release.HasValue ? release.Value.ToString() : "null")
            + ",\"own_token_closed\":" + (own.Closed ? "true" : "false") + ",\"linked_token_closed\":" + (linked.Closed ? "true" : "false")
            + ",\"own_acquisition_unknown\":" + (own.AcquisitionUnknown ? "true" : "false") + ",\"linked_acquisition_unknown\":" + (linked.AcquisitionUnknown ? "true" : "false")
            + ",\"own_release_error\":" + (own.ReleaseError.HasValue ? own.ReleaseError.Value.ToString() : "null") + ",\"linked_release_error\":" + (linked.ReleaseError.HasValue ? linked.ReleaseError.Value.ToString() : "null")
            + ",\"privileges\":[" + (complete ? privileges.ToString() : "") + "],\"token_adjusted\":false,\"account_modified\":false,\"worker_launched\":false,\"native_launch_authorized\":false}");
        return success ? 0 : 1;
    }
}
