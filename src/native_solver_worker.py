"""Optional offline native solver process, independent of engine ML imports.

Run with a separately configured Python 3.14 environment. External source is
verified before execution. This is a rule-adapted core, not an original manager.
"""
import argparse
import ast
import contextlib
import hashlib
import json
import math
import socket
import sys
import time
import types
from collections import Counter
from datetime import datetime
from pathlib import Path

MAX_MESSAGE=8*1024**2
RESOURCES=Path(__file__).parent/'fpl_predict_resources'


def read_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate JSON key')
            result[key]=value
        return result
    def invalid(value):raise ValueError('Nonfinite JSON number')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)


def verified_sources(root,expected):
    root=Path(root).resolve();result={}
    for name,digest in expected.items():
        path=(root/name).resolve()
        if not path.is_relative_to(root):raise ValueError('External source escapes root')
        with path.open('rb') as stream:raw=stream.read(1024**2+1)
        if len(raw)>1024**2 or hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('External source checksum mismatch')
        result[name]=raw.decode('utf-8')
    return result


def patched_tree(source):
    """Replace two hash-admitted expressions, not a downloaded install script."""
    class Rules(ast.NodeTransformer):
        resets=0;budgets=0
        def visit_Assign(self,node):
            if any(isinstance(t,ast.Name) and t.id=='raw_gw_ft' for t in node.targets):
                self.resets+=1
                node.value=ast.parse("{w: data.get('free_transfer_resets', {}).get(w+1, fts[w]-transfer_count[w]+1-use_wc[w]-use_fh[w]) for w in gws}",mode='eval').body
            return self.generic_visit(node)
        def visit_Expr(self,node):
            names={n.id for n in ast.walk(node) if isinstance(n,ast.Name)}
            if isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and node.value.func.attr=='addConstrs' and {'fh_sell_price','squad_fh','in_the_bank'}<=names:
                self.budgets+=1
                return ast.copy_location(ast.parse('native_fh_budget(m, players, gws, buy_price, sell_price, price_modified_players, squad, squad_fh, in_the_bank, transfer_out_first)').body[0],node)
            return self.generic_visit(node)
    rules=Rules();tree=rules.visit(ast.parse(source))
    if (rules.resets,rules.budgets)!=(1,1):raise ValueError('Pinned source adaptation structure differs')
    ast.fix_missing_locations(tree)
    return tree,hashlib.sha256(ast.dump(tree,include_attributes=False).encode()).hexdigest()


def integer(value,minimum=0,maximum=None):
    if type(value) is not int or value<minimum or maximum is not None and value>maximum:raise ValueError('Invalid bounded integer')
    return value


def validate_request(q,recipe):
    if set(q)!={'schema_version','market','state','xp','through','chip_schedule','opening_ids','seconds'} or q['schema_version']!=1:raise ValueError('Unknown native request fields')
    m=q['market'];s=q['state']
    if set(m)!={'season','gameweek','deadline','as_of','rows'} or set(s)!={'season','gameweek','holdings','bank','free_transfers','used_chips','previous_chip'}:raise ValueError('Unknown native context fields')
    g=integer(m['gameweek'],1,38);end=integer(q['through'],g,min(38,g+7))
    if m['season']!=recipe['season'] or s['season']!=m['season'] or s['gameweek']!=g:raise ValueError('Unaudited native season/origin')
    before=datetime.fromisoformat(m['as_of'].replace('Z','+00:00'));deadline=datetime.fromisoformat(m['deadline'].replace('Z','+00:00'))
    if before.tzinfo is None or deadline.tzinfo is None or before>=deadline:raise ValueError('Native origin must precede deadline')
    integer(s['bank']);integer(s['free_transfers'],0,5)
    if not 15<=len(m['rows'])<=1500:raise ValueError('Invalid candidate count')
    players={}
    for p in m['rows']:
        if set(p)!={'id','position','team','price_tenths','can_buy'}:raise ValueError('Unknown/outcome player fields')
        i=integer(p['id'],1);integer(p['position'],1,4);integer(p['price_tenths'],1)
        if i in players or not isinstance(p['team'],str) or not p['team'].strip() or type(p['can_buy']) is not bool:raise ValueError('Invalid player context')
        players[i]=p
    old={}
    for i,price in s['holdings']:
        integer(i,1);integer(price,1)
        if i in old or i not in players:raise ValueError('Invalid held identity')
        old[i]=price
    if len(old)!=15 and not (g==1 and not old):raise ValueError('Invalid held roster')
    xp={}
    for week,i,value in q['xp']:
        integer(week,g,end);integer(i,1)
        if i not in players or (week,i) in xp or type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Invalid forecast cells')
        xp[week,i]=value
    if set(xp)!={(week,i) for week in range(g,end+1) for i in players}:raise ValueError('Incomplete forecast cells')
    rules=read_json((RESOURCES/'season_rules.json').read_bytes())['seasons'][m['season']]
    if s['previous_chip'] not in (None,'wildcard','freehit','bboost','3xc'):raise ValueError('Unknown previous chip')
    used=set()
    for name,start in s['used_chips']:
        if type(start) is not int or start>g or (name,start) in used or not any(w['name']==name and w['start']==start for w in rules['chip_windows']):raise ValueError('Invalid used-chip ledger')
        used.add((name,start))
    chips={}
    for week,name in q['chip_schedule'].items():
        week=int(week);integer(week,g,end)
        if week in chips:raise ValueError('Multiple chips at one deadline')
        windows=[w for w in rules['chip_windows'] if w['name']==name and w['start']<=week<=w['stop']]
        if len(windows)!=1 or (name,windows[0]['start']) in used:raise ValueError('Illegal chip schedule')
        used.add((name,windows[0]['start']));chips[week]=name
    if any(name=='freehit' and (chips.get(week-1)=='freehit' or week==g and s['previous_chip']=='freehit') for week,name in chips.items()):raise ValueError('Consecutive Free Hits')
    opening=q['opening_ids']
    if opening is not None and (g!=1 or old or len(opening)!=15 or len(set(opening))!=15 or not all(type(i) is int and i in players and players[i]['can_buy'] for i in opening)):raise ValueError('Invalid common opening')
    if type(q['seconds']) not in (int,float) or not math.isfinite(q['seconds']) or not .001<=q['seconds']<=120:raise ValueError('Invalid solver time limit')
    return players,old,xp,chips,rules


class Runtime:
    def __init__(self,root):
        self.recipe=read_json((RESOURCES/'native_solver_recipe.json').read_bytes())
        sources=verified_sources(root,self.recipe['source_sha256'])
        if list(sys.version_info[:2])!=self.recipe['python_minor']:raise ValueError('Use the declared optional Python runtime')
        import numpy as np
        import pandas as pd
        import highspy
        self.np=np;self.pd=pd;self.hs=highspy;self.original=highspy.Highs
        if self.original().version()!=self.recipe['highspy_version']:raise ValueError('Optional HiGHS version differs')
        def deny(*a,**k):raise RuntimeError('Network disabled in offline native worker')
        socket.socket.connect=deny;socket.create_connection=deny
        def load(name,path):
            module=types.ModuleType(name);module.__file__=str(Path(root)/path);sys.modules[name]=module
            exec(compile(sources[path],module.__file__,'exec'),module.__dict__);return module
        load('paths','paths.py');utils=load('utils','utils.py');utils.cached_request=deny
        dev=types.ModuleType('dev');dev.__path__=[];sys.modules['dev']=dev
        load('dev.data_parser','dev/data_parser.py')
        self.solver=types.ModuleType('native_rule_adapted');self.solver.__file__=str(Path(root)/'dev/solver.py')
        tree,self.patch_hash=patched_tree(sources['dev/solver.py']);self.solver.native_fh_budget=self.fh_budget
        exec(compile(tree,self.solver.__file__,'exec'),self.solver.__dict__);self.solver.cached_request=deny

    def metadata(self):
        return dict(status='ready',revision=self.recipe['revision'],source_sha256=self.recipe['source_sha256'],patched_ast_sha256=self.patch_hash,python=sys.version.split()[0],numpy=self.np.__version__,pandas=self.pd.__version__,highspy=self.recipe['highspy_version'],threads=2,network_disabled=True)

    def fh_budget(self,m,players,gws,buy,sell,modified,squad,temporary,bank,first_sale):
        retained=m.addVariables(modified,gws,lb=0,ub=1,type=self.hs.HighsVarType.kInteger,name_prefix='fh_original_retained')
        discount={i:buy[i]-sell[i] for i in modified}
        for g in gws:
            unsold={i:1-m.qsum(first_sale[i,t] for t in gws if t<g) for i in modified}
            for i in modified:
                m.addConstr(retained[i,g]<=temporary[i,g]);m.addConstr(retained[i,g]<=unsold[i]);m.addConstr(retained[i,g]>=temporary[i,g]+unsold[i]-1)
            funds=m.qsum(buy[i]*squad[i,g-1] for i in players)+bank[g-1]-m.qsum(discount[i]*unsold[i] for i in modified)
            cost=m.qsum(buy[i]*temporary[i,g] for i in players)-m.qsum(discount[i]*retained[i,g] for i in modified)
            m.addConstr(funds>=cost)

    def solve(self,q):
        tick=time.monotonic();players,old,xp,chips,rules=validate_request(q,self.recipe);g=q['market']['gameweek'];end=q['through'];models=[];base=self.original
        class Limited(base):
            def __init__(m,*a,**k):
                super().__init__(*a,**k);m.setOptionValue('threads',2);m.maps={};m.injected=False;models.append(m)
            def setOptionValue(m,name,value):
                if name=='time_limit':value=max(.001,value-(time.monotonic()-tick));m.actual_time_limit=value
                return super().setOptionValue(name,value)
            def addVariables(m,*a,**k):
                values=super().addVariables(*a,**k)
                if k.get('name_prefix') in ('squad','squad_fh','transfer_in'):m.maps[k['name_prefix']]=values
                return values
            def run(m):
                if not m.injected:
                    for (i,w),v in m.maps['transfer_in'].items():
                        if not players[i]['can_buy']:m.changeColBounds(v.index,0.,0.)
                    for (i,w),v in m.maps['squad_fh'].items():
                        if not players[i]['can_buy']:m.addConstr(v<=m.maps['squad'][i,w-1])
                    m.injected=True
                result=super().run()
                if not m.getSolution().value_valid:raise ValueError('No feasible native incumbent')
                return result
        self.hs.Highs=Limited
        try:
            pd=self.pd
            rows=[dict(id=i,element_type=p['position'],Pos={1:'G',2:'D',3:'M',4:'F'}[p['position']],name=p['team'],web_name=str(i),now_cost=p['price_tenths'],**{key:value for w in range(g,end+1) for key,value in [(f'{w}_Pts',xp[w,i]),(f'{w}_xMins',0.)]}) for i,p in players.items()]
            frame=pd.DataFrame(rows).set_index('id');types_frame=pd.DataFrame([dict(id=p,squad_min_play={1:1,2:3,3:2,4:1}[p],squad_max_play={1:1,2:5,3:5,4:3}[p],squad_select={1:2,2:5,3:5,4:3}[p],singular_name_short={1:'GKP',2:'DEF',3:'MID',4:'FWD'}[p]) for p in range(1,5)]).set_index('id')
            sell=lambda i:min(old[i],players[i]['price_tenths'])+max(0,players[i]['price_tenths']-old[i])//2
            ft=rules['ft_topups'].get(str(g),q['state']['free_transfers'])
            data=dict(merged_data=frame,team_data=pd.DataFrame(dict(name=sorted(frame.name.unique()))),type_data=types_frame,next_gw=g,initial_squad=list(old),itb=q['state']['bank']/10.,fixtures=[],price_modified_players=[i for i in old if sell(i)!=players[i]['price_tenths']],sell_price={i:sell(i)/10. for i in old},buy_price={i:p['price_tenths']/10. for i,p in players.items()},ft=ft,ft_base=ft,max_players_from_team=max(Counter(players[i]['team'] for i in old).values(),default=0),free_transfer_resets={int(w):v for w,v in rules['ft_topups'].items()})
            options=dict(horizon=end-g+1,objective='regular',bench_weights={i:.1 for i in range(4)},vcap_weight=0.,ft_value=0.,itb_value=0.,secs=q['seconds'],gap=0.,verbose=False,no_opposing_play=False,chip_limits={})
            for name,abbreviation in {'wildcard':'wc','freehit':'fh','bboost':'bb','3xc':'tc'}.items():options['use_'+abbreviation]=[w for w,c in chips.items() if c==name]
            if q['opening_ids'] is not None:options['locked_next_gw']=q['opening_ids']
            answer=self.solver.solve_multi_period_fpl(data,options)[0];info=models[-1].getInfo()
            finite=lambda x:float(x) if math.isfinite(x) else None
            return dict(status='completed',seconds=time.monotonic()-tick,solver_time_limit=models[-1].actual_time_limit,objective=answer['score'],native_status=str(models[-1].getModelStatus()),dual_bound=finite(info.mip_dual_bound),mip_gap=finite(info.mip_gap),statistics=answer['statistics'],picks=read_json(answer['picks'].to_json(orient='records')))
        finally:
            self.hs.Highs=base
            for model in models:model.clear()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,required=True);args=parser.parse_args()
    with contextlib.redirect_stdout(sys.stderr):runtime=Runtime(args.source_root)
    print(json.dumps(runtime.metadata(),allow_nan=False),flush=True)
    while raw:=sys.stdin.buffer.readline(MAX_MESSAGE+1):
        if len(raw)>MAX_MESSAGE:raise ValueError('Oversized native message')
        try:
            q=read_json(raw)
            with contextlib.redirect_stdout(sys.stderr):result=runtime.solve(q)
        except Exception as error:result=dict(status='failed',error_type=type(error).__name__,message=str(error)[:500])
        print(json.dumps(result,allow_nan=False),flush=True)


if __name__=='__main__':main()
