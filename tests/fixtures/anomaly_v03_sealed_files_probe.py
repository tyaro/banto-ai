"""Opt-in bounded file DACL sealing; no directory sealing or native rename."""
import base64
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tests.fixtures import anomaly_v03_observed_evidence as bridge
from tests.fixtures import anomaly_v03_observed_evidence_probe as driver
from tests.fixtures import anomaly_v03_prepublication as prep
from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.fixtures import anomaly_v03_reader_reacquisition as reopen
from tests.fixtures import anomaly_v03_sealed_files as seal


class SealingScenario:
    base = ROOT / "artifacts/file-sealing-2026-09-14"

    def __init__(self):
        self.files = None
        self.writer_access = []
        self.continuation_verified = False
        self.root_unchanged = False
        self.verified = False

    def before_release(self, source, group, record):
        backend = seal.WindowsSealBackend(source)
        data = json.loads(record.raw)
        observations = tuple(prep.Observation(slot.pin, base64.b64decode(row["descriptor_b64"], validate=True))
                             for slot, row in zip(group.owner._slots, data["observations"]))
        plans = tuple(reopen.ReadPlan(index, name, raw, observations[index])
                      for index, name, raw in (
                          (1, "facts.json", base64.b64decode(data["files"][0]["bytes_b64"], validate=True)),
                          (2, "marker-pending.json", base64.b64decode(data["marker_b64"], validate=True))))
        self.files = seal.SealedFiles(backend, group=group, root_index=0, plans=plans, user=source._user)
        self.group, self.source, self.root_before = group, source, observations[0]
        def query_writers(pins):
            for lease in group._leases[1:]:
                bridge._observation_ready(lease)
                access = backend.granted_access(lease.handle)
                bridge._observation_ready(lease)
                owned._need(type(access) is int and access == reopen.WRITER_ACCESS, "writer_granted_access")
                self.writer_access.append(access)
        group.owner.borrowed((0, 1, 2), query_writers)

    def after_release(self):
        def observe_live(pins):
            owned._need(self.group.owner._busy and pins.parent == self.root_before.pin
                        and len(pins.observations) == 2 and pins.marker_index == 1
                        and all(lease.close_state == "not_started" for lease in self.files._leases),
                        "sealed_continuation_lifetime")
            root_now = bridge.inspect_native(self.group._leases[0], private_user=self.source._user,
                                             guard=self.files._guard)
            owned._need(root_now == self.root_before, "source_root_changed")
            self.root_unchanged = self.continuation_verified = True
        self.files.seal_and_use(observe_live)
        self.validate_terminal()
        self.verified = True

    def finish(self, *, primary=None):
        if self.files is not None:
            self.files.finish(primary=primary)

    def validate_terminal(self):
        owned._need(self.files is not None and self.writer_access == [reopen.WRITER_ACCESS] * 2
                    and self.continuation_verified and self.root_unchanged, "seal_scenario_incomplete")
        state = self.files.snapshot()
        owned._need(state["finished"] and not state["stopped"] and not state["resource_stop"]
                    and state["continuation"] == "returned" and len(state["sealing"]) == 2
                    and all(row["state"] == "verified" for row in state["sealing"])
                    and [row["held_access_after_seal"] for row in state["sealing"]]
                        == [seal.FILE_SEAL_ACCESS, seal.MARKER_SEAL_ACCESS]
                    and all(row["close"]["close_state"] == "closed" for row in state["readers"]),
                    "seal_scenario_incomplete")

    def snapshot(self):
        return {"file_sealing": "pass" if self.verified else "not_completed",
                "writer_granted_access": self.writer_access[:],
                "generation": None if self.files is None else self.files.snapshot(),
                "root_unchanged": self.root_unchanged, "sealed_file_count": 2 if self.continuation_verified else 0,
                "directory_sealing_performed": False, "native_rename_performed": False,
                "acceptance_status": "not_completed", "formal_permission": False, "execution_authenticated": False}


if __name__ == "__main__":
    raise SystemExit(driver.main(scenario=SealingScenario()))
