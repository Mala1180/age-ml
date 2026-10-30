"""Exercise real process isolation and shutdown without model API calls."""

import multiprocessing
import os
import time

import pytest


def worker_identity():
    return os.getpid(), multiprocessing.get_start_method()


def test_spawn_pool_returns_results_and_cancels_running_work():
    from ageml.app import Pool

    with Pool(processes=1) as pool:
        child_pid, start_method = pool.apply_async(worker_identity).get(timeout=45)
        assert child_pid != os.getpid()
        assert start_method == "spawn"
        sleeping = pool.apply_async(time.sleep, (60,))
        with pytest.raises(multiprocessing.TimeoutError):
            sleeping.get(timeout=0.05)
        started = time.monotonic()
    assert time.monotonic() - started < 10


@pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(), reason="requires fork"
)
def test_model_client_is_recreated_after_fork(monkeypatch):
    import langchain_ollama
    from ageml.common import model as backend
    from ageml.common.llm_config import resolve_llm_config

    monkeypatch.setattr(langchain_ollama, "ChatOllama", lambda **kwargs: os.getpid())
    config = resolve_llm_config("test-model", "ollama", "http://localhost:11434", "")
    backend._build_model.cache_clear()
    monkeypatch.setattr(backend, "current_llm_config", lambda: config)
    assert backend.get_model() == os.getpid()
    ctx = multiprocessing.get_context("fork")
    parent, child = ctx.Pipe(duplex=False)

    def probe():
        child.send((os.getpid(), backend.get_model()))
        child.close()

    process = ctx.Process(target=probe)
    process.start()
    child.close()
    try:
        assert parent.poll(10), "child did not return a client"
        child_pid, client_pid = parent.recv()
        assert child_pid == client_pid
    finally:
        process.join(timeout=10)
        if process.is_alive():
            process.terminate()
            process.join(timeout=10)
        parent.close()
        backend._build_model.cache_clear()
    assert process.exitcode == 0
