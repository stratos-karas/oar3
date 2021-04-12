# coding: utf-8
import pytest

from oar.kao.platform import Platform
from oar.kao.walltime_change import process_walltime_change_requests
from oar.lib import EventLog, WalltimeChange, config, db, get_logger
from oar.lib.job_handling import insert_job

from ..helpers import insert_running_jobs

logger = get_logger("oar.kao.walltime_change")


@pytest.yield_fixture(scope="function", autouse=True)
def minimal_db_initialization(request):
    with db.session(ephemeral=True):
        # add some resources
        for i in range(5):
            db["Resource"].create(network_address="localhost")
        db["Queue"].create(name="default")
        yield


def test_process_walltime_change_requests_void():
    plt = Platform()
    process_walltime_change_requests(plt)
    assert not db.query(WalltimeChange).all()  # of course remains void


def test_process_walltime_change_requests_job_not_running():
    plt = Platform()
    job_id = insert_job(res=[(60, [("resource_id=4", "")])], properties="")
    db["WalltimeChange"].create(job_id=job_id, pending=3663)

    process_walltime_change_requests(plt)

    walltime_changes = db.query(WalltimeChange).one()
    print(walltime_changes.pending, walltime_changes.granted)
    assert walltime_changes.granted == 0


@pytest.mark.skipif(
    "os.environ.get('DB_TYPE', '') != 'postgresql'",
    reason="bug raises with sqlite database",
)
def test_process_walltime_change_requests():
    plt = Platform()
    job_id = insert_running_jobs(1)[0]
    db["WalltimeChange"].create(job_id=job_id, pending=3663)

    process_walltime_change_requests(plt)
    event = db.query(EventLog).filter(EventLog.job_id == job_id).one()

    walltime_change = (
        db.query(WalltimeChange).filter(WalltimeChange.job_id == job_id).one()
    )

    print(walltime_change.job_id, walltime_change.pending, walltime_change.granted)
    assert walltime_change.granted == 3663
    assert walltime_change.pending == 0
    assert (
        event.description == "walltime changed: 1:2:3 (granted: +1:1:3/pending: 0:0:0)"
    )
