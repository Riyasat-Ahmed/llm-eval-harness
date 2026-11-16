import threading

from evalh import store


def test_check_same_thread_false_allows_cross_thread_use(tmp_path):
    """Regression test: the Streamlit dashboard caches one connection via
    st.cache_resource, which can hand it to a different thread on a rerun.
    sqlite3 raises ProgrammingError in that case unless opened with
    check_same_thread=False."""
    conn = store.connect(tmp_path / "t.db", check_same_thread=False)

    errors = []

    def touch_from_other_thread():
        try:
            conn.execute("SELECT 1").fetchone()
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    t = threading.Thread(target=touch_from_other_thread)
    t.start()
    t.join()

    assert errors == []


def test_default_connection_is_still_same_thread_only(tmp_path):
    """The CLI/runner path keeps the default (safer) behavior."""
    conn = store.connect(tmp_path / "t2.db")

    errors = []

    def touch_from_other_thread():
        try:
            conn.execute("SELECT 1").fetchone()
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    t = threading.Thread(target=touch_from_other_thread)
    t.start()
    t.join()

    assert len(errors) == 1
    assert "thread" in str(errors[0]).lower()
