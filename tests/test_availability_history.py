import csv
import hashlib
import io

import pytest

from availability_history import admit_prefix, read_archive


def inputs():
    stream=io.StringIO(newline="");writer=csv.writer(stream)
    writer.writerow(["timestamp","season","gameweek","player_id","opta_code","position","news",
                     "chance_of_playing_next_round","return_gameweek"])
    writer.writerow(["2026-01-02T09:10:00","2526",20,1,"p123","DEF","Injury - unknown return date",0,""])
    writer.writerow(["2026-01-02T09:10:00","2526",20,2,"p456","FWD","", "", ""])
    raw=stream.getvalue().encode();n=len(raw)
    record=dict(gameweek=20,deadline="2026-01-03T11:00:00Z",published_at="2026-01-02T09:11:00Z",
                size=n,commit="a"*40,git_blob_sha1=hashlib.sha1(b"blob "+str(n).encode()+b"\0"+raw).hexdigest())
    bootstrap=dict(events=[dict(id=20,deadline_time=record["deadline"])],elements=[
        dict(id=1,code=123,element_type=2),dict(id=2,code=456,element_type=4)])
    return raw,record,bootstrap


def test_exact_historical_prefix_is_admitted_without_guessing_naive_clock():
    raw,record,b=inputs()
    report,observations=admit_prefix(raw+b"future changed history after deadline",record,b)
    assert report["rows"]==report["bootstrap_known"]==2
    assert not report["source_clock_has_timezone"] and not report["model_admitted"]
    assert observations[0]["available_by"]=="2026-01-02T09:11:00+00:00"
    assert observations[0]["chance_label"]==0 and observations[1]["chance_label"] is None
    assert observations[1]["news"]==""  # empty captured news is not a healthy probability


@pytest.mark.parametrize("problem",["publication","naive_publication","checksum","deadline","identity","position","extent"])
def test_bad_timing_integrity_or_identity_fails_closed(problem):
    raw,r,b=inputs()
    if problem=="publication":r["published_at"]=r["deadline"]
    if problem=="naive_publication":r["published_at"]="2026-01-02T09:11:00"
    if problem=="checksum":raw=raw.replace(b"Injury",b"Changed")
    if problem=="deadline":b["events"][0]["deadline_time"]="2026-01-04T11:00:00Z"
    if problem=="identity":b["elements"][0]["id"]=99
    if problem=="position":b["elements"][0]["element_type"]=3
    if problem=="extent":r["size"]=len(raw)+1
    with pytest.raises(ValueError):admit_prefix(raw,r,b)


def test_player_added_after_earlier_bootstrap_is_explicitly_unknown():
    raw,r,b=inputs();b["elements"]=b["elements"][:1]
    report,observations=admit_prefix(raw,r,b)
    assert report["bootstrap_known"]==1 and report["absent_at_other_capture"]==1
    assert len(observations)==2  # no outcome-based or missing-snapshot row drop


def test_archive_expansion_is_bounded(tmp_path,monkeypatch):
    import gzip
    import availability_history
    path=tmp_path/"source.csv.gz";path.write_bytes(gzip.compress(b"a"*1000))
    monkeypatch.setattr(availability_history,"MAX_BYTES",200)
    with pytest.raises(ValueError,match="Expanded"):read_archive(path)
