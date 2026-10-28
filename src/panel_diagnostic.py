"""Exact fixed-panel comparison, independent of predictions or model fitting."""
import hashlib
import json
import math
from numbers import Real

FIELDS = ('id', 'position', 'team', 'price_tenths', 'weight')
MISSING = object()


def canonical_bytes(panels):
    return json.dumps(panels, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')


def panel_hash(panels):
    return hashlib.sha256(canonical_bytes(panels)).hexdigest()


def display(value):
    return dict(repr=repr(value) if value is not MISSING else '<missing>',
                type=type(value).__name__ if value is not MISSING else 'missing')


def weight_delta(original, regenerated):
    if not isinstance(original, Real) or not isinstance(regenerated, Real):
        return dict(valid=False, unequal=True, absolute=None, relative='Infinity'), math.inf
    a, b = float(original), float(regenerated)
    if not math.isfinite(a) or not math.isfinite(b):
        return dict(valid=False, unequal=True, absolute=None, relative='Infinity'), math.inf
    absolute = abs(b-a)
    relative = absolute/abs(a) if a else (0. if b==0 else math.inf)
    return dict(valid=True, unequal=bool(a!=b), absolute=absolute,
                relative=relative if math.isfinite(relative) else 'Infinity'), relative


def roster_sets(squads):
    return {frozenset(p.get('id', '<missing>') for p in squad) for squad in squads}


def compare_panels(original, regenerated, relative_tolerance=1e-9):
    """Class A/B exactly as declared; full repr preserves small float differences.

    Relative differences use the ORIGINAL value as denominator. Prices are
    exact regardless of their magnitude; only weight has a diagnostic tolerance.
    This tolerance is never used by the frozen Stage-C build.
    """
    first = None; structural = False; too_large = False; type_differences = 0
    all_weights = []; folds = {}; field_counts = dict.fromkeys(FIELDS, 0)

    def difference(fold, squad, member, field, left, right, kind='value'):
        nonlocal first
        d = dict(fold=fold, squad=squad, member=member, field=field, kind=kind,
                 original=display(left), regenerated=display(right))
        if first is None: first = d
        return d

    fold_keys_equal = set(original)==set(regenerated)
    if not fold_keys_equal: structural = True
    for fold in sorted(set(original)|set(regenerated)):
        if fold not in original or fold not in regenerated:
            d=difference(fold,None,None,'fold_present',fold in original,fold in regenerated)
            folds[fold]=dict(present_original=fold in original,present_regenerated=fold in regenerated,differences=[d])
            continue
        old, new = original[fold], regenerated[fold]; differences=[]
        if set(old)!=set(new) or set(old)!={'first_gw','squads'}:
            structural=True;differences.append(difference(fold,None,None,'panel_fields',sorted(old),sorted(new)))
        a,b=old.get('first_gw',MISSING),new.get('first_gw',MISSING)
        if a!=b or type(a)!=type(b):
            differences.append(difference(fold,None,None,'first_gw',a,b,'value' if a!=b else 'type_only'))
            if a!=b:structural=True
            if type(a)!=type(b):type_differences+=1
        left,right=old.get('squads',[]),new.get('squads',[])
        if len(left)!=len(right):
            structural=True;differences.append(difference(fold,None,None,'squad_count',len(left),len(right)))
        squads=[];weights=[];ordered_rosters_equal=True;ordered_members_equal=True
        for i in range(max(len(left),len(right))):
            if i>=len(left) or i>=len(right):
                squads.append(dict(index=i,present_original=i<len(left),present_regenerated=i<len(right)))
                ordered_rosters_equal=False;ordered_members_equal=False
                continue
            x,y=left[i],right[i];sd=[];members=[]
            if len(x)!=len(y):
                structural=True;sd.append(difference(fold,i,None,'member_count',len(x),len(y)))
            ids_x=[m.get('id',MISSING) for m in x];ids_y=[m.get('id',MISSING) for m in y]
            id_list_equal=ids_x==ids_y;id_set_equal=set(ids_x)==set(ids_y)
            ordered_rosters_equal &= id_set_equal;ordered_members_equal &= id_list_equal
            for j in range(max(len(x),len(y))):
                if j>=len(x) or j>=len(y):
                    members.append(dict(index=j,present_original=j<len(x),present_regenerated=j<len(y)))
                    continue
                a,b=x[j],y[j];md=[];equal={}
                if set(a)!=set(b) or set(a)!=set(FIELDS):
                    structural=True;md.append(difference(fold,i,j,'member_fields',sorted(a),sorted(b)))
                for field in FIELDS:
                    v,w=a.get(field,MISSING),b.get(field,MISSING)
                    same=bool(v==w);equal[field]=same
                    if not same or type(v)!=type(w):
                        md.append(difference(fold,i,j,field,v,w,'value' if not same else 'type_only'))
                        if not same:field_counts[field]+=1
                        if type(v)!=type(w):type_differences+=1
                    if field!='weight':
                        if not same or v is MISSING:structural=True
                    else:
                        delta,relative=weight_delta(v,w);weights.append(delta);all_weights.append(delta)
                        if relative>relative_tolerance:too_large=True
                members.append(dict(index=j,fields_equal=equal,differences=md,weight=weights[-1]))
            squads.append(dict(index=i,member_count_original=len(x),member_count_regenerated=len(y),
                ordered_member_ids_equal=id_list_equal,member_id_set_ignoring_order_equal=id_set_equal,
                identity_and_price_equal=all(all(m.get('fields_equal',{}).get(k,False) for k in FIELDS[:-1]) for m in members),
                differences=sd,members=members))
        if not ordered_rosters_equal or not ordered_members_equal:structural=True
        sets_left,sets_right=roster_sets(left),roster_sets(right)
        folds[fold]=dict(first_gw_original=old.get('first_gw'),first_gw_regenerated=new.get('first_gw'),
            squad_count_original=len(left),squad_count_regenerated=len(right),
            squad_order_ignoring_member_order_equal=ordered_rosters_equal,ordered_members_equal=ordered_members_equal,
            squad_id_set_ignoring_order_equal=sets_left==sets_right,
            unique_squad_id_sets_original=len(sets_left),unique_squad_id_sets_regenerated=len(sets_right),
            original_only_squad_id_sets=[sorted(v,key=repr) for v in sorted(sets_left-sets_right,key=repr)],
            regenerated_only_squad_id_sets=[sorted(v,key=repr) for v in sorted(sets_right-sets_left,key=repr)],
            weight=weight_summary(weights),differences=differences,squads=squads)
    try:hashes=dict(original=panel_hash(original),regenerated=panel_hash(regenerated))
    except (ValueError,TypeError):hashes=dict(original=None,regenerated=None)
    return dict(classification='B' if structural or too_large else 'A',fold_keys_equal=fold_keys_equal,
        original_fold_keys=sorted(original),regenerated_fold_keys=sorted(regenerated),
        exact_object_equal=bool(original==regenerated),canonical_hashes=hashes,
        canonical_hash_equal=hashes['original']==hashes['regenerated'] if hashes['original'] is not None else False,
        structural_difference=bool(structural),weight_over_relative_tolerance=bool(too_large),
        relative_tolerance=relative_tolerance,field_unequal_counts=field_counts,type_difference_count=type_differences,
        weight=weight_summary(all_weights),first_difference=first,folds=folds)


def weight_summary(values):
    infinite=any(v['relative']=='Infinity' for v in values)
    return dict(compared=len(values),unequal_count=sum(v['unequal'] for v in values),
        invalid_count=sum(not v['valid'] for v in values),
        maximum_absolute_difference=max((v['absolute'] for v in values if v['absolute'] is not None),default=0.),
        maximum_relative_difference='Infinity' if infinite else max((v['relative'] for v in values),default=0.))
