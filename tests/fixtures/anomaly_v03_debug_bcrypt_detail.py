"""Fixed deeper bcrypt failure sites; observation only, no policy changes."""
import struct

from tests.fixtures.anomaly_v03_debug_bcrypt_failure import DebugBcryptFailure
from tests.fixtures.anomaly_v03_debug_transport import need


class DebugBcryptDetail(DebugBcryptFailure):
    RECIPE = "bcrypt-26200.9445-detail-v1"
    BREAK_RVAS = (0x5AF1, 0x5DAF, 0x5DD5, 0xB22D)
    CANDIDATES = ("critical_section", "event_last_error", "cleanup_candidates", "outer_fallback")
    CALLER_OFFSETS = (0x48, 0x128, 0x128, 0x48)
    CALLER_RVAS = (0xB217, 0x5AB5, 0x5AB5, 0x111CF)
    CODE_READS, CODE_BYTES = 3, 1790
    STOP_REASON = "bcrypt_detail_observed_stop"
    WINDOWS = (
        (0x59E0, 1068, "cb7064e15ca553b37c1b77b48de2602ed157de8497d430b5c7bf7affd40804b3"),
        (0xB1C0, 247, "4deae110e20cec3932557987e6fcc1814cad99931cc2d02ac0499cf192f3260b"),
        (0x11140, 475, "7ad0379a750d6a424bdae27d8d4800b5562e59bc73a59547915a86806990e75a"),
    )

    def __repr__(self):
        return "DebugBcryptDetail(<private registers and caller>)"

    def _inspect_result(self, budget):
        site = self.hit_index
        eax = struct.unpack_from("<I", self.context, 120)[0]
        self.row.update(status_u32=eax, candidate=self.CANDIDATES[site],
                        status_domain=("negative_candidate", "win32_candidate",
                                       "mixed_cleanup_candidates", "unclassified_nonzero")[site])
        if site in (0, 3):
            ebx = struct.unpack_from("<I", self.context, 144)[0]
            need(eax == ebx and (bool(eax & 0x80000000) if site == 0 else eax != 0),
                 "bcrypt_detail_result")
        else:
            # The checked direct caller passes this fixed output slot; no
            # dereference or policy mutation is needed to check that argument.
            need(struct.unpack_from("<Q", self.context, 168)[0] == self.base+0x25B10
                 and struct.unpack_from("<Q", self.context, 240)[0] == 0, "bcrypt_detail_frame")
            ebp = struct.unpack_from("<I", self.context, 160)[0]
            if site == 1:
                need(ebp == 0, "bcrypt_detail_event_state")
                # Keep GetLastError zero as returned, without claiming success.
            else:
                self.row.update(cleanup_edi=struct.unpack_from("<I", self.context, 176)[0],
                                cleanup_ebp=ebp)
                # Multiple paths converge before cleanup. These registers do
                # not identify one API or a completed conversion to NTSTATUS.
        self._caller(struct.unpack_from("<Q", self.context, 152)[0], budget)
