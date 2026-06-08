"""Guards for the deploy trigger script.

These don't run the script (it needs a live PAT + network); they lock in the
behaviour that turns a silent failure into a visible one — the recurring
"trigger not firing" incident was an *expired token* returning HTTP 401 that
only showed up because the script logs and exits non-zero on any non-204.
"""
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _trigger_script():
    with open(os.path.join(_ROOT, 'deploy', 'trigger_github.sh'), encoding='utf-8') as f:
        return f.read()


def _crontab():
    with open(os.path.join(_ROOT, 'deploy', 'crontab.txt'), encoding='utf-8') as f:
        return f.read()


def test_trigger_targets_workflow_dispatch():
    script = _trigger_script()
    assert 'workflows/' in script and '/dispatches' in script


def test_trigger_checks_for_204():
    # The success contract is HTTP 204; anything else must be treated as failure.
    assert '204' in _trigger_script()


def test_trigger_fails_loud_on_non_204():
    # Must exit non-zero so cron logs / monitoring catch an expired token (401).
    script = _trigger_script()
    assert 'exit 1' in script
    assert 'ERROR' in script


def test_trigger_errors_when_pat_file_missing():
    script = _trigger_script()
    assert '.github_pat' in script
    assert 'not found' in script.lower()


def test_trigger_logs_timestamp_for_every_run():
    # Each invocation must leave a dated line so "did it fire?" is answerable.
    assert 'date' in _trigger_script()


def test_crontab_pins_prague_timezone():
    # Menus must be fresh by Prague lunchtime regardless of the VM's system TZ.
    assert 'CRON_TZ=Europe/Prague' in _crontab()


def test_crontab_uses_correct_home_path():
    # Regression guard: the cron once pointed at /home/opc instead of the ubuntu user.
    crontab = _crontab()
    assert '/opc/' not in crontab
    assert 'trigger_github.sh' in crontab


def test_crontab_runs_only_on_weekdays():
    # Restaurants are closed on weekends — don't trigger Sat/Sun.
    assert '1-5' in _crontab()
