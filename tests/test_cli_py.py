import unittest
from unittest.mock import Mock, patch

import synapseindex.cli as cli_mod


class TestCli(unittest.TestCase):
    def test_main_runs_index_with_args(self):
        fake_coro = object()
        with patch.object(cli_mod.Path, "exists", return_value=True), patch.object(
            cli_mod, "run_index", Mock(return_value=fake_coro)
        ) as index_mock, patch.object(cli_mod.asyncio, "run") as run_mock:
            exit_code = cli_mod.main(["/tmp/in.md", "/tmp/out", "--root-name", "root"])

        self.assertEqual(exit_code, 0)
        run_mock.assert_called_once_with(fake_coro)
        index_mock.assert_called_once_with(source="/tmp/in.md", destination="/tmp/out", root_name="root")

    def test_main_errors_when_source_missing(self):
        with patch.object(cli_mod.Path, "exists", return_value=False):
            with self.assertRaises(SystemExit):
                cli_mod.main(["/tmp/missing.md", "/tmp/out"])

