"""Tests do not install or execute optional upstream dependencies."""
import sys
import os
import subprocess
from pathlib import Path
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


def test_population_seed_is_affordable_legal_and_does_not_fix_other_individuals():
    positions=['GK']*2+['DEF']*5+['MID']*5+['FWD']*3+['FWD']
    players=[]
    for i,pos in enumerate(positions,1):
        players.append(SimpleNamespace(player_id=i,position=lambda season,p=pos:p,
            team=lambda gw,season,i=i:'T'+str((i-1)//3),price=lambda gw,season,i=i:1 if i==16 else 50))
    optimizer=SimpleNamespace(players=players,root_gameweek=1,season='2526',scoring=SimpleNamespace(budget=750))
    population=[[99]*15,[77]*15]
    assert worker.seed_population(optimizer,population,lambda i:i!=16)
    assert {players[i].player_id for i in population[0]}==set(range(1,16))
    assert population[1]==[77]*15
    optimizer.scoring.budget=749
    original=[row[:] for row in population]
    assert not worker.seed_population(optimizer,population,lambda i:i!=16)
    assert population==original


def test_cold_optional_import_keeps_feasibility_helper_free_of_ml_imports():
    env=dict(os.environ,PYTHONPATH=str(Path(worker.__file__).parent))
    result=subprocess.run([sys.executable,'-c',"import airsenal_solver_worker,sys; assert not {'numpy','pandas','scipy','sklearn','airsenal'} & sys.modules.keys()"],env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
