"""The fraud bench as a regression test: all 20 synthetic attempts (honest cleanups and tricks)
go through the real API and verification chain, and each must still get the verdict and reason
it expects. A change to a threshold or to the chain that lets a trick through, or stops an
honest cleanup, fails here with the bench's own table row."""
from werkzeug.security import generate_password_hash

from app import auth
from conftest import TEST_DB
from tools import fraud_bench


def test_every_bench_attempt_gets_the_expected_result(capsys, monkeypatch):
    # The bench signs up 40 people; scrypt would be a third of the run and is not under test here.
    monkeypatch.setattr(auth, "generate_password_hash",
                        lambda password: generate_password_hash(password, "pbkdf2:sha256:1"))
    ok = fraud_bench.synthetic_bench(TEST_DB, force=False)
    out = capsys.readouterr().out
    rows = [line for line in out.splitlines() if line.startswith("| ") and not line.startswith("| #")]

    assert len(fraud_bench.SCENARIOS) == 20
    assert len(rows) == 20, out
    wrong = [row for row in rows if "| ✗ |" in row]
    assert not wrong, "attempts that did not get the expected result:\n" + "\n".join(wrong)
    assert ok
    assert "Matched the expected result: 20/20" in out
    assert "Tricks paid automatically: 0/" in out
