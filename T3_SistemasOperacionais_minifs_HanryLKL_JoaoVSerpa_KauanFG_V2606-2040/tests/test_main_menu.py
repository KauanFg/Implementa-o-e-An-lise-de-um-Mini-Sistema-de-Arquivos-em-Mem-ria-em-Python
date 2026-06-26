import unittest
from unittest.mock import patch

import main
from minifs.filesystem import FileSystem
from minifs.shell import Shell


class TestMainMenu(unittest.TestCase):
    def test_parse_cli_args(self) -> None:
        self.assertEqual(main.get_start_mode(["--demo"]), "demo")
        self.assertEqual(main.get_start_mode(["--tests"]), "tests")
        self.assertEqual(main.get_start_mode(["--shell"]), "shell")

    def test_menu_selection(self) -> None:
        with patch("builtins.input", return_value="2"):
            with patch("sys.stdin.isatty", return_value=True):
                self.assertEqual(main.get_start_mode([]), "demo")

    def test_shell_executes_py_command(self) -> None:
        shell = Shell(FileSystem(), echo_prompt=False)
        with patch("minifs.shell.subprocess.run") as mock_run:
            shell.execute_line("py main.py --tests")
        self.assertTrue(mock_run.called)


if __name__ == "__main__":
    unittest.main()
