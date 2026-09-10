"""Parent/restricted token ownership, fake native outputs only."""

from contextlib import ExitStack
import unittest
from unittest.mock import Mock, patch

from tests.fixtures import anomaly_v03_debug_tokens as t


class DebugTokensTests(unittest.TestCase):
    def owner(self, stack):
        api = Mock()
        api.k.GetCurrentProcess.return_value = -1
        api.k.CloseHandle.return_value = True
        api.k.LocalFree.return_value = None
        group = sorted(t.w._PRIVILEGED)[0]
        parent, restricted = {"groups": [[group, 0]], "user": ["DUMMY", 0]}, {"restricted": True}
        api.profile.side_effect = [parent, restricted]
        def parent_token(process, access, pointer):
            pointer.contents.value = 401
            return True
        def sid(value, pointer):
            pointer.contents.value = {group: 601, t.w._RC: 602, t.w._RESTRICTED_PACKAGES: 603}[value]
            return True
        def restrict(*args):
            args[-1].contents.value = 402
            return True
        api.a.OpenProcessToken.side_effect = parent_token
        api.a.ConvertStringSidToSidW.side_effect = sid
        api.a.CreateRestrictedToken.side_effect = restrict
        stack.enter_context(patch.object(t.w, "_validate_parent"))
        validate = stack.enter_context(patch.object(t.w, "_validate_restricted"))
        return t.DebugTokens(api), api, validate

    def test_recipe_and_exactly_once_owned_release(self):
        with ExitStack() as stack:
            owner, api, validate = self.owner(stack)
            self.assertIs(owner.prepare(), owner)
            self.assertEqual(owner.status, "prepared")
            args = api.a.CreateRestrictedToken.call_args.args
            self.assertEqual(args[:3], (401, 9, 1))
            self.assertEqual(args[4:7], (0, None, 2))
            self.assertEqual(args[3][0].sid, 601)
            self.assertEqual(args[7][0].sid, 602)
            self.assertEqual([(row.sid, row.attributes) for row in args[7]], [(602, 0), (603, 0)])
            self.assertEqual([call.args[0] for call in api.k.LocalFree.call_args_list], [601, 602, 603])
            self.assertTrue(owner.close())
            self.assertTrue(owner.close())
            self.assertEqual([call.args[0] for call in api.k.CloseHandle.call_args_list], [402, 401])

    def test_uncertain_output_is_retained_and_cannot_be_called_resolved(self):
        for phase in ("parent", "sid", "compatibility_sid", "restricted"):
            with ExitStack() as stack, self.subTest(phase=phase):
                owner, api, validate = self.owner(stack)
                function = {"parent": api.a.OpenProcessToken, "sid": api.a.ConvertStringSidToSidW,
                            "compatibility_sid": api.a.ConvertStringSidToSidW,
                            "restricted": api.a.CreateRestrictedToken}[phase]
                original = function.side_effect
                def interrupted(*args):
                    result = original(*args)
                    if phase != "compatibility_sid" or args[0] == t.w._RESTRICTED_PACKAGES:
                        raise MemoryError()
                    return result
                function.side_effect = interrupted
                owner.prepare()
                self.assertEqual(owner.status, "failed")
                self.assertTrue(owner.resource_stop)
                self.assertFalse(owner.close())
                index = {"parent": 0, "restricted": 1, "sid": 2,
                         "compatibility_sid": len(owner.buffers) - 1}[phase]
                self.assertEqual(owner.acquire[index], "uncertain")
                self.assertIsNotNone(owner.buffers[index].value)
                released = [call.args[0] for call in api.k.CloseHandle.call_args_list + api.k.LocalFree.call_args_list]
                self.assertNotIn(owner.buffers[index].value, released)

    def test_validation_failure_preserves_confirmed_tokens_for_close(self):
        with ExitStack() as stack:
            owner, api, validate = self.owner(stack)
            original = MemoryError()
            validate.side_effect = original
            owner.prepare()
            self.assertIs(owner.primary, original)
            self.assertTrue(owner.close())
            self.assertEqual(api.k.CloseHandle.call_count, 2)

    def test_release_false_and_interrupt_are_not_retried(self):
        for release in ("token", "sid"):
            with ExitStack() as stack, self.subTest(release=release):
                owner, api, validate = self.owner(stack)
                if release == "sid":
                    api.k.LocalFree.side_effect = [MemoryError(), None, None]
                owner.prepare()
                if release == "token":
                    api.k.CloseHandle.side_effect = [False, True]
                self.assertFalse(owner.close())
                counts = (api.k.LocalFree.call_count, api.k.CloseHandle.call_count)
                self.assertFalse(owner.close())
                self.assertEqual(counts, (api.k.LocalFree.call_count, api.k.CloseHandle.call_count))

    def test_close_before_prepare_disables_acquisition(self):
        with ExitStack() as stack:
            owner, api, validate = self.owner(stack)
            self.assertTrue(owner.close())
            with self.assertRaises(t.TransportError):
                owner.prepare()
            api.a.OpenProcessToken.assert_not_called()


if __name__ == "__main__":
    unittest.main()
