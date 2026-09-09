"""Synthetic bounded bytes only; no filesystem or native calls."""

import json
import unittest

from tests.fixtures import anomaly_v03_debug_evidence_reader as r


class EvidenceReaderTests(unittest.TestCase):
    def packet(self, *, modify=None, events=None, tail=False):
        state = {"confirmed_buffers": 4, "pending": None, "wait_inflight": False,
                 "continue_inflight": False, "file_closed": [True] * 256,
                 "file_close_state": ["closed"] * 256}
        metadata = {"version": 1, "pointer_bits": 64, "byte_order": "little",
                    "slots_per_region": 256, "event_size": 176,
                    "raw_scope": "all_preallocated_slots_including_unconfirmed",
                    "result_scope": "before_evidence_write_flush_and_file_close",
                    "normal": state, "drain": dict(state, confirmed_buffers=0),
                    "nonce": "DUMMY_PRIVATE"}
        if modify:
            modify(metadata)
        normal = (r.DebugEvent * 256)()
        for index, kind in enumerate(events or (3, 6, 7, 5)):
            normal[index].kind, normal[index].pid, normal[index].tid = kind, 17, 19
            normal[index].info.create_process.base = 0x12340000
            if kind == 6:
                normal[index].info.load_dll.base = 0x56780000
            elif kind == 7:
                normal[index].info.unload_base = 0x56780000
            elif kind == 5:
                normal[index].info.exit_code = 0xC0000142
        if tail:
            normal[9].kind = 6
        encoded = json.dumps(metadata).encode("ascii")
        return (r.Format.HEADER.pack(r.Format.MAGIC, len(encoded), 176, 256, 2) + encoded
                + bytes(normal) + bytes(r.Format.REGION_SIZE))

    def test_anonymous_lifetimes_and_public_redaction(self):
        raw = self.packet()
        result = r.interpret(raw)
        rows = result["regions"][0]["events"]
        self.assertEqual([row.get("module") for row in rows], [0, 1, 1, None])
        self.assertEqual(rows[-1]["code"], 0xC0000142)
        self.assertEqual(result["regions"][1]["events"], [])
        self.assertIs(result.private_raw, raw)
        self.assertFalse(result["provenance_verified"])
        self.assertFalse(result["native_accepted"])
        self.assertNotIn("DUMMY_PRIVATE", repr(result) + json.dumps(result))
        self.assertNotIn("address", json.dumps(result))

    def test_truncated_trailing_wrong_header_and_bad_counts_are_rejected(self):
        raw = self.packet()
        for invalid in (raw[:-1], raw + b"x", b"bad" + raw[3:], b"",
                        self.packet(modify=lambda m: m["normal"].update(confirmed_buffers=True)),
                        self.packet(modify=lambda m: m["normal"].update(confirmed_buffers=257))):
            with self.assertRaises(ValueError):
                r.interpret(invalid)

    def test_unconfirmed_slot_is_retained_but_never_promoted_to_event(self):
        result = r.interpret(self.packet(tail=True))
        normal = result["regions"][0]
        self.assertTrue(normal["unconfirmed_bytes_nonzero"])
        self.assertEqual(len(normal["events"]), 4)

    def test_unknown_unload_and_duplicate_base_are_not_false_matches(self):
        result = r.interpret(self.packet(events=(3, 7, 6, 6)))
        rows = result["regions"][0]["events"]
        self.assertIsNone(rows[1]["module"])
        self.assertIsNone(rows[3]["module"])
        self.assertTrue(rows[3]["module_ambiguous"])

    def test_duplicate_json_keys_and_nonfinite_constants_are_rejected(self):
        raw = self.packet()
        _, size, *_ = r.Format.HEADER.unpack_from(raw)
        body = raw[r.Format.HEADER.size:r.Format.HEADER.size + size]
        for prefix in (b'{"version":1,', b'{"extra":NaN,'):
            altered = prefix + body[1:]
            invalid = (r.Format.HEADER.pack(r.Format.MAGIC, len(altered), 176, 256, 2)
                       + altered + raw[r.Format.HEADER.size + size:])
            with self.assertRaises(ValueError):
                r.interpret(invalid)


if __name__ == "__main__":
    unittest.main()
