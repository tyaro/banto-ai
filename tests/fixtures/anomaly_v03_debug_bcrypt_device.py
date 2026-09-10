"""Fixed bcrypt device-opening and control-request observations."""
import struct

from tests.fixtures.anomaly_v03_debug_bcrypt_failure import DebugBcryptFailure
from tests.fixtures.anomaly_v03_debug_transport import need


class DebugBcryptDevice(DebugBcryptFailure):
    RECIPE = "bcrypt-26200.9445-device-v1"
    BREAK_RVAS = (0x8129, 0x80AC, 0x5DD5)
    DEBUG_ENABLES = 0x15
    CANDIDATES = ("open_helper_8154", "device_control_return", "cleanup_candidates")
    CALLER_OFFSETS = (0xB8, 0xB8, 0x128)
    CALLER_RVAS = (0x5D53, 0x5D53, 0x5AB5)
    CODE_READS, CODE_BYTES = 3, 1758
    STOP_REASON = "bcrypt_device_observed_stop"
    WINDOWS = (
        (0x59E0, 1068, "cb7064e15ca553b37c1b77b48de2602ed157de8497d430b5c7bf7affd40804b3"),
        (0x7F50, 660, "1a67c25ccbd32bcfb4c60ebb399b9453c6fc55882bc88651ad916de8182382bc"),
        # This is a fixed name literal, not another code window.
        (0x1F098, 30, "e7df70a79aa2fdf8e999c635fb354bc1d25ad32e2b4b52426c98a88eea54d3fb"),
    )

    def __repr__(self):
        return "DebugBcryptDevice(<private registers and caller>)"

    def _inspect_result(self, budget):
        site = self.hit_index
        eax = struct.unpack_from("<I", self.context, 120)[0]
        rsp = struct.unpack_from("<Q", self.context, 152)[0]
        r12 = struct.unpack_from("<I", self.context, 216)[0]
        value = r12 if site == 0 else eax
        self.row.update(status_u32=value, candidate=self.CANDIDATES[site],
                        status_domain=("open_helper_negative", "control_return_negative",
                                       "mixed_cleanup_candidates")[site])
        if site < 2:
            need(struct.unpack_from("<Q", self.context, 168)[0] == rsp+0x60
                 and struct.unpack_from("<Q", self.context, 176)[0] == 0
                 and struct.unpack_from("<Q", self.context, 232)[0] == 0
                 and struct.unpack_from("<Q", self.context, 240)[0] == 8, "bcrypt_device_frame")
            if site == 0:
                need(bool(r12 & 0x80000000), "bcrypt_device_open_status")
            else:
                need(r12 == 0, "bcrypt_device_open_state")
                need(bool(eax & 0x80000000), "bcrypt_device_control_status")
                # This includes warning 80000005. Stop here; any later response
                # interpretation requires a separate explicitly scoped run.
        else:
            need(struct.unpack_from("<Q", self.context, 168)[0] == self.base+0x25B10
                 and struct.unpack_from("<Q", self.context, 240)[0] == 0, "bcrypt_device_cleanup_frame")
            self.row.update(cleanup_edi=struct.unpack_from("<I", self.context, 176)[0],
                            cleanup_ebp=struct.unpack_from("<I", self.context, 160)[0])
        self._caller(rsp, budget)
