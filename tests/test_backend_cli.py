import os
import unittest
from argparse import Namespace
from unittest.mock import patch

import backend.cli as cli


class TestCli(unittest.TestCase):
    def test_parse_args_defaults(self):
        with patch("sys.argv", ["cli.py"]):
            args = cli.parse_args()
        self.assertEqual(args.host, "0.0.0.0")
        self.assertEqual(args.port, 5001)
        self.assertFalse(args.debug)

    def test_parse_args_custom(self):
        with patch("sys.argv", ["cli.py", "--host", "127.0.0.1", "--port", "1234", "--debug"]):
            args = cli.parse_args()
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 1234)
        self.assertTrue(args.debug)

    def test_main_debug_sets_env_and_runs(self):
        args = Namespace(host="0.0.0.0", port=5001, debug=True)
        with patch.object(cli, "parse_args", return_value=args):
            with patch.object(cli.uvicorn, "run") as run_mock:
                os.environ.pop("NILCH_DEBUG", None)
                cli.main()
        self.assertEqual(os.environ.get("NILCH_DEBUG"), "1")
        run_mock.assert_called_once()
        _, kwargs = run_mock.call_args
        self.assertTrue(kwargs["reload"])
        self.assertEqual(kwargs["log_level"], "debug")

    def test_main_non_debug_runs(self):
        args = Namespace(host="0.0.0.0", port=5001, debug=False)
        with patch.object(cli, "parse_args", return_value=args):
            with patch.object(cli.uvicorn, "run") as run_mock:
                os.environ.pop("NILCH_DEBUG", None)
                cli.main()
        self.assertIsNone(os.environ.get("NILCH_DEBUG"))
        run_mock.assert_called_once()
        _, kwargs = run_mock.call_args
        self.assertFalse(kwargs["reload"])
        self.assertEqual(kwargs["log_level"], "info")
