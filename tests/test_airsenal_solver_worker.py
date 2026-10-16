"""Tests do not install or execute optional upstream dependencies."""
import sys
from types import SimpleNamespace

import pytest
import airsenal_solver_worker as worker


class Move:
    def __init__(self,label):self.value=label
    def label(self):return self.value


def node(move,labels=None):
    prior=None if labels is None else Plan(labels)
    return Move(move),1,0,0,None,prior


class Plan:
    def __init__(self,labels):
        self.outcomes=[SimpleNamespace(move=Move(label)) for label in labels]
    def __len__(self):return len(self.outcomes)


def test_families_get_complete_paths_before_repeating_first_family():
    seen=[]
    queue=worker.FairQueue(node('root'),float('inf'),lambda n:seen.append(n[0].label()))
    queue.get()
    for move in ['0','1','2']:queue.put(node(move,[]))
    queue.task_done()
    assert queue.get()[0].label()=='0'
    queue.put(node('0',['0']));queue.put(node('1',['0']));queue.task_done()
    assert queue.get()[0].label()=='0'  # descend, rather than skip to a short prefix
    queue.completed_plan();queue.task_done()
    assert queue.get()[0].label()=='1'  # a different immediate-action family
    queue.completed_plan();queue.task_done()
    assert queue.get()[0].label()=='2'
    queue.completed_plan();queue.task_done()
    assert queue.get()[0].label()=='1'  # resume the first family's alternatives
    assert seen==['root','0','0','1','2','1']
    assert queue.finished_families==['0','1','2']


def test_deadline_returns_no_node_and_marks_unfinished_search():
    queue=worker.FairQueue(node('root'),0.,lambda _:pytest.fail('expired node executed'))
    assert queue.get() is None and queue.truncated


def test_import_does_not_load_upstream_and_source_rejection_creates_no_home(tmp_path):
    assert not any(n=='airsenal' or n.startswith('airsenal.') for n in sys.modules)
    home=tmp_path/'runtime'
    with pytest.raises(FileNotFoundError):worker.bootstrap(tmp_path/'absent-source',home)
    assert not home.exists()
