import mock


def test_serialized(db_session):
    from dallinger.db import serialized
    from dallinger.models import Participant

    counts = []

    # Define a function which adds a new participant
    # with an id based on a database query.
    def add_participant(session, interruptor=None):
        count = session.query(Participant).count()
        counts.append(count)

        # This is for the sake of the test,
        # to let us change the count from a different session
        # on the first try.
        if interruptor:
            interruptor()

        session.add(Participant(
            worker_id='serialized_{}'.format(count + 1),
            assignment_id='test',
            hit_id='test',
            mode='test',
        ))

    # Define a function to get in the way of our transaction
    # by changing the participant count from another db session
    # the first time that our serialized transaction is called.
    interrupted = []
    def interruptor():
        if not interrupted:
            session2 = db_session.session_factory()
            session2.connection(execution_options={'isolation_level': 'SERIALIZABLE'})
            add_participant(session2)
            session2.commit()
            interrupted.append(True)

    # Now define the test function which will try to add
    # a participant using the scoped db session,
    # but will fail the first time due to the interruption.
    @serialized
    def serialized_write():
        add_participant(db_session, interruptor)

    # Now run the serialized write.
    # It should succeed, but only after retrying the transaction.
    serialized_write()

    # Which we can check by making sure that `add_participant`
    # calculated the count at least 3 times
    assert counts == [0, 0, 1]


def test_after_commit_hook(db_session):
    with mock.patch('dallinger.heroku.worker.conn') as redis:
        from dallinger.db import queue_message
        queue_message('test', 'test')
        db_session.commit()

        assert redis.called_once_with('test', 'test')
