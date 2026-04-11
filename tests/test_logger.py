import json
import pytest

import tacek.logger as logger_mod
from tacek.logger import RunLogger, init_logger, get_logger, log


# ── RunLogger ─────────────────────────────────────────────────────────────────

def test_log_appends_entries(tmp_path):
    l = RunLogger(str(tmp_path))
    l.log('first')
    l.log('second')
    assert len(l.logs) == 2
    assert l.logs[0]['message'] == 'first'
    assert l.logs[1]['message'] == 'second'


def test_log_entries_have_iso_timestamps(tmp_path):
    l = RunLogger(str(tmp_path))
    l.log('msg')
    ts = l.logs[0]['time']
    assert 'T' in ts  # ISO 8601 separator


def test_save_writes_valid_json(tmp_path):
    l = RunLogger(str(tmp_path))
    l.log('entry one')
    l.save()
    data = json.loads((tmp_path / 'run_log.json').read_text(encoding='utf-8'))
    assert 'start_time' in data
    assert 'end_time' in data
    assert len(data['logs']) == 1
    assert data['logs'][0]['message'] == 'entry one'


def test_save_end_time_after_start_time(tmp_path):
    l = RunLogger(str(tmp_path))
    l.log('x')
    l.save()
    data = json.loads((tmp_path / 'run_log.json').read_text())
    assert data['end_time'] >= data['start_time']


def test_save_preserves_all_entries(tmp_path):
    l = RunLogger(str(tmp_path))
    for i in range(5):
        l.log(f'entry {i}')
    l.save()
    data = json.loads((tmp_path / 'run_log.json').read_text())
    assert len(data['logs']) == 5


# ── global helpers ────────────────────────────────────────────────────────────

def test_global_log_without_init_prints(capsys, tmp_path):
    old = logger_mod._logger_instance
    logger_mod._logger_instance = None
    try:
        log('orphan message')
        assert 'orphan message' in capsys.readouterr().out
    finally:
        logger_mod._logger_instance = old


def test_init_logger_sets_instance(tmp_path):
    logger = init_logger(str(tmp_path))
    assert get_logger() is logger


def test_global_log_routes_to_instance(tmp_path):
    logger = init_logger(str(tmp_path))
    log('routed message')
    assert any(e['message'] == 'routed message' for e in logger.logs)


def test_get_logger_returns_none_before_init():
    old = logger_mod._logger_instance
    logger_mod._logger_instance = None
    try:
        assert get_logger() is None
    finally:
        logger_mod._logger_instance = old
