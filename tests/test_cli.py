import contextlib
import io
import unittest

from toki.cli import build_parser, main


class CliTests(unittest.TestCase):
    def test_invalid_subcommand_arguments_are_rejected(self):
        parser = build_parser()
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                parser.parse_args(["alarm", "set", "not-a-time", "--repeat", "weekly"])
        self.assertEqual(error.exception.code, 2)

    def test_invalid_timer_duration_has_clear_error(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = main(["timer", "nonsense"])
        self.assertEqual(result, 2)
        self.assertIn("duration", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
