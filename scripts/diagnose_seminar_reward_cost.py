"""Frozen-history EI audit for the per-k constant control-cost term."""
from __future__ import annotations
import os
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"
from pathlib import Path
import sys
import json
import warnings
import numpy as np
from scipy.stats import norm
from sklearn.exceptions import ConvergenceWarning
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bogp.controller import BOControllerConfig, ContextualBayesianRateController
from bogp.types import ControlInput, GPStateSnapshot


class TracedController(ContextualBayesianRateController):
    def __init__(self,config):
        super().__init__(config)
        self.predictions={}

    def _model_for_k(self,k):
        is_new=k not in self._models
        model=super()._model_for_k(k)
        if is_new:
            predict=model.predict
            def traced(x,return_std=False):
                result=predict(x,return_std=return_std)
                if return_std:
                    self.predictions[k]=(x.copy(),result[0].copy(),result[1].copy())
                return result
            model.predict=traced
        return model


def main():
    warnings.filterwarnings('ignore',category=ConvergenceWarning)
    out=ROOT/'outputs/seminar_reward_ablation/20261001'
    full=json.loads((out/'full/seed_0.json').read_text())
    no_cost=json.loads((out/'no_control_cost/seed_0.json').read_text())
    c1=TracedController(BOControllerConfig(random_seed=0))
    c2=TracedController(BOControllerConfig(random_seed=0))
    divergence=next(i for i,(a,b) in enumerate(zip(full['records'],no_cost['records'])) if a['control']!=b['control'])
    for i in range(divergence):
        state=GPStateSnapshot(**full['states'][i]['start'])
        c1.propose(state);c2.propose(state)
        control=ControlInput(**full['records'][i]['control'])
        c1.register_observation(state,control,full['records'][i]['reward']['total'])
        c2.register_observation(state,control,no_cost['records'][i]['reward']['total'])
    state=GPStateSnapshot(**full['states'][divergence]['start'])
    u1=c1.propose(state);u2=c2.propose(state)
    rows={}
    for k in c1.predictions:
        x1,mu1,s1=c1.predictions[k];x2,mu2,s2=c2.predictions[k]
        assert np.array_equal(x1,x2)
        best1=max(c1._y_history_by_k[k]);best2=max(c2._y_history_by_k[k])
        def ei(mu,std,best):
            improvement=mu-best-.01
            z=np.divide(improvement,std,out=np.zeros_like(improvement),where=std>1e-12)
            return np.where(std>1e-12,improvement*norm.cdf(z)+std*norm.pdf(z),0.)
        e1=ei(mu1,s1,best1);e2=ei(mu2,s2,best2)
        shift=.05*(5-k)/4
        # Translation invariance without refitting: shifting both prediction
        # mean and incumbent by the same per-k cost leaves EI unchanged.
        translated=ei(mu1+shift,s1,best1+shift)
        assert float(abs(e1-translated).max()) < 1e-12
        assert float(np.max(abs(np.array(c2._y_history_by_k[k])-np.array(c1._y_history_by_k[k])-shift))) < 1e-12
        rows[k]={
            'reward_constant_shift':shift,
            'max_ei_diff_algebraic_translation':float(abs(e1-translated).max()),
            'max_ei_diff_refitted_models':float(abs(e1-e2).max()),
            'max_std_diff_refitted_models':float(abs(s1-s2).max()),
            'best_ei_full':float(e1.max()),'best_ei_no_cost':float(e2.max()),
            'kernel_full':str(c1._models[k].kernel_), 'kernel_no_cost':str(c2._models[k].kernel_),
            'reward_history_shift_error':float(np.max(abs(np.array(c2._y_history_by_k[k])-np.array(c1._y_history_by_k[k])-shift))),
        }
    result={'seed':0,'first_divergent_control_step':divergence,'generation':state.generation,
            'full_control':u1.as_tuple(),'no_cost_control':u2.as_tuple(),'per_k':rows,
            'interpretation':'Per-k EI cancels constant cost analytically. Refitting on shifted floating-point rewards can change kernel optimization and subsequent decisions.'}
    (out/'cost_invariance_diagnostic.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
