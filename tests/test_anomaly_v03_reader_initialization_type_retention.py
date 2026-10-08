"""Original worker type remains retained when a caller replaces its factory."""
from types import SimpleNamespace
from unittest.mock import Mock,patch
import unittest
from banto_ai import anomaly_v03_preformal_reader_git_worker as reader


class Escape(BaseException):pass


class ReaderInitializationTypeRetentionTests(unittest.TestCase):
    def test_original_worker_survives_public_factory_replacement_without_new_owner(self):
        worker=reader.ReaderGitWorker.__new__(reader.ReaderGitWorker)
        actor=SimpleNamespace(original_constructor_inputs=(object(),),control_publication=object())
        worker.original_initializing_actor=actor;worker.original_entry=object();worker.child=SimpleNamespace(stopped=False)
        failure=OSError('original initializing actor IO');failure.reader_git_worker=worker
        with (patch.object(reader,'ReaderGitWorker',Mock()),
              patch.object(reader.ReaderInitializationRetention,'_pause',side_effect=Escape),self.assertRaises(Escape)):
            reader.retain_reader_initialization(failure)
        self.assertIs(worker.original_initialization_retention.actor,actor)
        self.assertIs(worker.original_initialization_retention.original_error,failure)
        self.assertTrue(worker.child.stopped)
