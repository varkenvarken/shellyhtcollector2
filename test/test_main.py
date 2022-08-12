import pytest

from htcollector.__main__ import get_args

help_msg = """usage: pytest [-h] [--database DATABASE] [--dbhost DBHOST] [--dbport DBPORT]
              [-p PORT] [-b BIND] [-x]

optional arguments:
  -h, --help            show this help message and exit
  --database DATABASE   database schema
  --dbhost DBHOST       database host
  --dbport DBPORT       database port
  -p PORT, --port PORT  port to listen on
  -b BIND, --bind BIND  address to bind to
  -x, --ping            ping database end exit
"""


class TestMain:
    def test_get_args_help(self, capsys):
        with pytest.raises(SystemExit):
            args = get_args(["--help"])
        captured = capsys.readouterr()
        out = captured.out
        #assert out == help_msg
