"""New bounded reader reacquisition scenario; reuses the observed-prepare driver."""
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


class ReaderScenario:
    base = ROOT / "artifacts/reader-reacquisition-2026-09-14"

    def __init__(self):
        self.readers = None
        self.writer_access = []
        self.verified = False

    def before_release(self, source, group, record):
        backend = reopen.WindowsReaderBackend(source)
        data = json.loads(record.raw)
        plans = tuple(reopen.ReadPlan(index, name, raw,
                                      prep.Observation(group.owner._slots[index].pin,
                                          base64.b64decode(data["observations"][index]["descriptor_b64"], validate=True)))
                      for index, name, raw in (
                          (1, "facts.json", base64.b64decode(data["files"][0]["bytes_b64"], validate=True)),
                          (2, "marker-pending.json", base64.b64decode(data["marker_b64"], validate=True))))
        self.readers = reopen.ReacquiredReaders(backend, group=group, root_index=0, plans=plans, user=source._user)
        def query_writers(pins):
            for lease in group._leases[1:]:
                bridge._observation_ready(lease)
                access = backend.granted_access(lease.handle)
                bridge._observation_ready(lease)
                owned._need(type(access) is int and access == reopen.WRITER_ACCESS, "writer_granted_access")
                self.writer_access.append(access)
        group.owner.borrowed((0, 1, 2), query_writers)

    def after_release(self):
        self.readers.acquire()
        self.validate_terminal()
        self.verified = True

    def finish(self, *, primary=None):
        if self.readers is not None:
            self.readers.finish(primary=primary)

    def validate_terminal(self):
        owned._need(self.readers is not None and self.writer_access == [reopen.WRITER_ACCESS] * 2,
                    "reader_scenario_incomplete")
        state = self.readers.snapshot()
        owned._need(state["finished"] and not state["stopped"] and not state["resource_stop"]
                    and len(state["readers"]) == 2 and all(
                        row["state"] == "verified" and row["identity_and_bytes_matched"]
                        and row["granted_access"] == reopen.READER_ACCESS and row["close"]["close_state"] == "closed"
                        for row in state["readers"]), "reader_scenario_incomplete")

    def snapshot(self):
        return {"reader_reacquisition": "pass" if self.verified else "not_completed",
                "writer_granted_access": self.writer_access[:],
                "reader_generation": None if self.readers is None else self.readers.snapshot(),
                "writer_requested_access": 0xC0020000, "reader_requested_access": reopen.READER_ACCESS,
                "reader_share": 1, "reader_creation": 3, "dacl_changed": False,
                "acceptance_status": "not_completed", "formal_permission": False, "execution_authenticated": False}


if __name__ == "__main__":
    raise SystemExit(driver.main(scenario=ReaderScenario()))
