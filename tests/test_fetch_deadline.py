"""A stalled Herbie fetch must cost one slice, not the whole GEFS run."""
import datetime
import signal
import socket
import threading
import time

import pytest

pytest.importorskip("herbie")
xr = pytest.importorskip("xarray")

from nwp import download_funcs
from nwp.download_funcs import _fetch_deadline


@pytest.fixture
def stalled_socket():
    """A connected socket whose peer accepts and never sends a byte."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    client = socket.create_connection(server.getsockname())
    peer, _ = server.accept()
    yield client
    for s in (client, peer, server):
        s.close()


def test_fetch_deadline_interrupts_blocking_read(stalled_socket):
    """The production failure: a read with no timeout that never returns."""
    start = time.monotonic()
    with pytest.raises(TimeoutError):
        with _fetch_deadline(0.2):
            stalled_socket.recv(1)
    assert time.monotonic() - start < 2


def test_fetch_deadline_refires_after_swallowed_timeout(stalled_socket):
    """Herbie catches Exception while probing sources; the deadline must survive that."""
    with pytest.raises(TimeoutError):
        with _fetch_deadline(0.2, refire_s=0.1):
            try:
                stalled_socket.recv(1)
            except Exception:
                pass
            stalled_socket.recv(1)


def test_fetch_deadline_restores_handler_and_disarms():
    """Nothing outlives the block: prior handler back, no timer left running."""
    before = signal.getsignal(signal.SIGALRM)
    with _fetch_deadline(5):
        pass
    assert signal.getsignal(signal.SIGALRM) is before
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)


def test_fetch_deadline_is_noop_off_main_thread():
    """Signals only reach the main thread, so elsewhere it must not raise or arm."""
    errors = []

    def body():
        try:
            with _fetch_deadline(0.05):
                time.sleep(0.2)
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    t = threading.Thread(target=body)
    t.start()
    t.join()
    assert errors == []


def test_herbie_load_variable_skips_stalled_slice(monkeypatch):
    """One hung slice is dropped; the member keeps every other forecast hour."""
    def fake_fetch(init_dt, fxx, product, member, query, remove_grib):
        if fxx == 3:
            time.sleep(30)
        return xr.Dataset(
            {"t2m": (("latitude", "longitude"), [[float(fxx)]])},
            coords={"latitude": [40.0], "longitude": [250.0]},
        )

    monkeypatch.setattr(download_funcs, "_herbie_fetch_slice", fake_fetch)
    monkeypatch.setattr(download_funcs, "FETCH_DEADLINE_S", 0.2)
    monkeypatch.setattr(download_funcs.GEFSData, "crop_to_UB", staticmethod(lambda ds: ds))

    start = time.monotonic()
    ds = download_funcs.herbie_load_variable(
        init_dt=datetime.datetime(2026, 9, 27, 0),
        start_h=0, max_h=9, delta_h=3,
        vrbl="TMP:2 m above", product="atmos.25", member="p25",
    )
    assert time.monotonic() - start < 5
    assert ds["t2m"].values.ravel().tolist() == [0.0, 6.0, 9.0]
