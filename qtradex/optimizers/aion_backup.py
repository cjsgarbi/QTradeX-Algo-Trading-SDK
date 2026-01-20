"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          ADAPTIVE INTELLIGENT OPTIMIZATION NETWORK (AION) v2025.14           ║
║                   QTradeX SDK - Intelligent Pipeline                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║            Agent Communication via Shared State (OptState):                  ║
║                                                                              ║
║      ┌─────────────────────────────────────────────────────────────┐         ║
║      │   STATE ──► MUTATOR ──► FILTER ──► EVALUATOR ──► LEARNER    │         ║
║      │     │          │          │            │            │       │         ║
║      │     │   (elite,grad)  (param_hist)  (backtest)  (update)    │         ║
║      │     └──────────┴──────────┴────────────┴────────────┘       │         ║
║      │                   (continuous feedback loop)                │         ║
║      └─────────────────────────────────────────────────────────────┘         ║
║                                                                              ║
║  Integrated Smart Skip: FILTER uses param_hist from LEARNER                  ║
║  Adaptive Temperature: Adjusts based on phase and skips                      ║
║                                                                              ║
║  Contributed by https://github.com/cjsgarbi                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
import json
import math
import time
from copy import deepcopy
from random import choice, randint, random, sample

import matplotlib.pyplot as plt
import numpy as np

from qtradex.common.utilities import it, print_table
from qtradex.core import backtest
from qtradex.core.base_bot import Info
from qtradex.optimizers.utilities import bound_neurons, end_optimization, plot_scores


# ══════════════════════════════════════════════════════════════════════════════
# SHARED STATE - Communication hub between agents
# ══════════════════════════════════════════════════════════════════════════════

class OptState:
    """Centralized state. All agents read/write here."""
    __slots__ = ('iteration', 'improvements', 'stagnation', 'skips', 'evaluated',
                 'cache', 'gradients', 'elite', 'param_hist', 'synapses', 
                 'neuron_impacts', 'recent_impr', 'temperature', 'consecutive_skips',
                 'skip_history', 'last_skip_reason')
    
    def __init__(self, initial_temp=1.0):
        self.iteration = 0
        self.improvements = 0
        self.stagnation = 0
        self.skips = 0
        self.evaluated = 0
        self.consecutive_skips = 0
        self.cache = {}
        self.gradients = {}
        self.elite = []
        self.param_hist = {}
        self.synapses = []
        self.neuron_impacts = {}
        self.recent_impr = []
        self.temperature = initial_temp
        self.skip_history = []      # History of skipped tunes for learning
        self.last_skip_reason = ''  # Debug: reason for last skip
    
    @property
    def phase(self):
        """Current phase inferred from state (includes skip_rate)."""
        # Very high skip rate = needs more exploration
        if self.skip_rate > 0.50:
            return 'exploration'
        if self.stagnation > 100:
            return 'exploration'
        if len(self.recent_impr) >= 5:
            gaps = [self.recent_impr[i] - self.recent_impr[i-1] for i in range(1, len(self.recent_impr))]
            if sum(gaps) / len(gaps) < 30:
                return 'exploitation'
        return 'balanced'
    
    @property
    def skip_rate(self):
        total = self.evaluated + self.skips
        return (self.skips / total) if total > 0 else 0
    
    def record_skip(self, tune, reason='bad_region'):
        """Records a skip for other agents to learn from."""
        self.skips += 1
        self.consecutive_skips += 1
        self.last_skip_reason = reason
        # Keep last 20 skips for analysis
        self.skip_history.append(tuple(sorted(tune.items())))
        if len(self.skip_history) > 20:
            self.skip_history.pop(0)
        # Adjust temperature based on skips
        if self.consecutive_skips > 10:
            self.temperature = min(3.0, self.temperature * 1.1)
    
    def reset_skip_streak(self):
        """Called when a backtest is executed."""
        self.consecutive_skips = 0


class AIONoptions:
    """AION Configuration."""
    __slots__ = ('epochs', 'improvements', 'cooldown', 'show_terminal', 'print_tune',
                 'plot_period', 'quantum_tunneling_prob', 'min_temperature', 
                 'max_temperature', 'synapses', 'neurons', 'fitness_ratios',
                 'enable_cache', 'elite_preservation', 'smart_skip_threshold',
                 'bad_region_memory')
    
    def __init__(self):
        self.epochs = math.inf
        self.improvements = 100000
        self.cooldown = 0
        self.show_terminal = True
        self.print_tune = True
        self.plot_period = 100
        self.quantum_tunneling_prob = 0.05
        self.min_temperature = 0.05
        self.max_temperature = 3.0
        self.synapses = 50
        self.neurons = []
        self.fitness_ratios = None
        self.enable_cache = True
        self.elite_preservation = 3
        self.smart_skip_threshold = 10
        self.bad_region_memory = 50


# ══════════════════════════════════════════════════════════════════════════════
# DISPLAY
# ══════════════════════════════════════════════════════════════════════════════

def printouts(ctx):
    """Compact display of optimization status."""
    table = [[""] + ctx["params"] + [""] + ctx["coords"] + [""]]
    table.append(["current"] + list(ctx["bot"].tune.values()) + [""] + list(ctx["score"].values()) + [""])
    
    for c, (s, b) in ctx["best"].items():
        table.append([c] + list(b.tune.values()) + [""] + list(s.values()) + ["###"])
    
    n = len(ctx["coords"])
    eye = np.eye(n).astype(int)
    colors = np.vstack((
        np.zeros((len(ctx["params"]) + 2, n + 2)),
        np.hstack((np.zeros((n, 2)), eye)),
        np.array([[0, 0] + [2 if i else 0 for i in ctx["opts"].fitness_ratios.values()]])
    ))
    for c in ctx["boom"]:
        colors[len(ctx["params"]) + 2 + ctx["coords"].index(c), ctx["coords"].index(c) + 2] = 3
    
    st = ctx["state"]
    speed = max(1, st.evaluated) / (time.time() - ctx["start"])
    phase_map = {'exploration': '🔍 Exploring', 'exploitation': '🎯 Refining', 'balanced': '⚖️ Balanced'}
    temp_bar = "█" * int(st.temperature * 10) + "░" * (10 - int(st.temperature * 10))
    
    msg = "\033c"
    msg += it("cyan", f"🚀 AION v2025.13 | Intelligent Pipeline | {len(ctx['params'])}D | https://github.com/cjsgarbi\n\n")
    msg += print_table(table, render=True, colors=colors, pallete=[0, 34, 33, 178]) + "\n"
    msg += it("white", "═" * 60 + "\n")
    msg += it("white", f"• Backtests: {st.evaluated}  Improvements: {st.improvements}  Synapses: {len(st.synapses)}\n")
    msg += it("white", f"• Speed: {speed:.1f}/s  Cache: {len(st.cache)}  Skip: {st.skip_rate*100:.0f}%\n")
    msg += it("white", f"• Phase: {phase_map[st.phase]}  {temp_bar}  Stagnation: {st.stagnation}\n")
    msg += it("white", "═" * 60 + "\n")
    msg += it("yellow", "Ctrl+C to stop\n")
    print(msg)


# ══════════════════════════════════════════════════════════════════════════════
# AION - Integrated Pipeline with Shared State
# ══════════════════════════════════════════════════════════════════════════════

class AION:
    """AION with integrated pipeline. Agents communicate via OptState."""
    
    def __init__(self, data, wallet=None, options=None):
        if wallet is None:
            raise ValueError("Wallet required")
        self.options = options or AIONoptions()
        self.data = data
        self.wallet = wallet
        self.state = OptState(initial_temp=1.0)
        
        # Precomputed Lévy Flight
        beta = 1.5
        self._levy_sigma = (math.gamma(1+beta) * math.sin(math.pi*beta/2) / 
                           (math.gamma((1+beta)/2) * beta * 2**((beta-1)/2))) ** (1/beta)
    
    def _scalar(self, v):
        """Convert any value to a scalar."""
        if hasattr(v, 'size'):
            return 0.0 if v.size == 0 else float(v.item()) if v.size == 1 else float(v)
        if hasattr(v, '__len__'):
            return 0.0 if len(v) == 0 else float(v[0])
        return float(v)
    
    def _hash_tune(self, tune):
        """Numpy-safe hash for caching."""
        try:
            items = []
            for k, v in sorted(tune.items()):
                if isinstance(v, np.ndarray):
                    items.append((k, v.tobytes()))
                else:
                    items.append((k, v))
            return hash(tuple(items))
        except:
            return id(tune)

    # ══════════════════════════════════════════════════════════════════════
    # MUTATOR AGENT - Uses shared state to generate intelligent mutations
    # ══════════════════════════════════════════════════════════════════════
    
    def _mutate(self, bot, params):
        """Generates mutation using shared state."""
        st = self.state
        neurons = self.options.neurons or [p for p in params if bot.clamps[p][3]]
        
        # Favor impactful neurons (from state)
        if st.neuron_impacts and random() < 0.5:
            impactful = sorted(st.neuron_impacts, key=st.neuron_impacts.get, reverse=True)
            neurons = [n for n in impactful if n in neurons][:max(1, len(neurons)//2)] or neurons
        
        for _ in range(3):
            neurons = sample(neurons, k=randint(1, len(neurons)))
        
        if st.synapses and len(st.synapses) > 2 and randint(0, 2):
            neurons = list(choice(st.synapses))
        
        old_tune = bot.tune.copy()
        
        # Crossover with elite (10% chance)
        if st.elite and random() < 0.1:
            bot.tune = self._crossover(bot.tune, bot.clamps)
        
        # Phase-based boost (from state)
        boost = 1.5 + st.stagnation * 0.01 if st.phase == 'exploration' else 1.0
        boost = min(3.0, boost)
        
        # Mutate
        for n in neurons:
            if not bot.clamps[n][3]:
                continue
            is_int = isinstance(bot.tune[n], (int, np.integer))
            step = self._levy_step(bot.clamps[n][0], bot.clamps[n][2], boost, n, bot.tune[n])
            if is_int:
                step = int(step) or (1 if random() > 0.5 else -1)
            bot.tune[n] += step
        
        return bound_neurons(bot), old_tune, neurons
    
    def _levy_step(self, min_v, max_v, boost, param, current):
        """Generates step with intelligent direction from state."""
        st = self.state
        rng = max_v - min_v or 1
        
        u = np.random.normal(0, self._levy_sigma)
        v = np.random.normal(0, 1)
        step = (u / (abs(v) ** 0.667)) * st.temperature * 0.1 * rng * boost
        
        # Gradient memory direction (from state)
        if param in st.gradients and st.gradients[param]['successes'] >= 2:
            if random() < 0.7:
                step = abs(step) * st.gradients[param]['direction']
        
        # Quantum tunneling
        if random() < self.options.quantum_tunneling_prob:
            step *= 5.0
        
        return np.clip(step, -rng * 0.5, rng * 0.5)
    
    def _crossover(self, tune, clamps):
        """Genetic crossover using elite from state."""
        st = self.state
        if len(st.elite) < 2:
            return tune
        p1, p2 = st.elite[0][1], choice(st.elite[1:])[1]
        child = {}
        for k in tune:
            r = random()
            if r < 0.4:
                child[k] = p1.get(k, tune[k])
            elif r < 0.8:
                child[k] = p2.get(k, tune[k])
            else:
                avg = (p1.get(k, tune[k]) + p2.get(k, tune[k])) / 2
                child[k] = avg + (random()-0.5) * (clamps[k][2]-clamps[k][0]) * 0.1 if k in clamps else avg
        return child

    # ══════════════════════════════════════════════════════════════════════
    # FILTER AGENT - Smart Skip using shared state (INTEGRATED INTO PIPELINE)
    # ══════════════════════════════════════════════════════════════════════
    
    def _should_skip(self, tune, best_roi, clamps):
        """
        Decides whether to skip based on shared state.
        INTEGRATED: Communicates with MUTATOR via skip_history and temperature.
        """
        st = self.state
        
        # ═══ CONDITIONS TO NOT SKIP (communicated via state) ═══
        
        # Warm-up: need data in param_hist first
        if st.evaluated < self.options.smart_skip_threshold:
            st.last_skip_reason = 'warmup'
            return False
        
        # Invalid baseline ROI
        if best_roi <= 0:
            st.last_skip_reason = 'no_baseline'
            return False
        
        # Rate limit: never skip more than 60%
        if st.skip_rate >= 0.60:
            st.last_skip_reason = 'rate_limit'
            return False
        
        # Forced exploration: 20% always passes
        if random() < 0.20:
            st.last_skip_reason = 'forced_exploration'
            return False
        
        # Exploration phase: extra 50% chance not to skip
        if st.phase == 'exploration' and random() < 0.50:
            st.last_skip_reason = 'exploration_phase'
            return False
        
        # Too many consecutive skips: reset and do not skip
        if st.consecutive_skips > 50:
            st.consecutive_skips = 0
            st.param_hist = {}  # Reset problematic history
            st.temperature = min(3.0, st.temperature * 1.5)
            st.last_skip_reason = 'consecutive_reset'
            return False
        
        # ═══ BAD REGION ANALYSIS (using param_hist from LEARNER) ═══
        
        bad_params, total_analyzed = 0, 0
        threshold = best_roi * 0.30  # Region is bad if ROI < 30% of best
        
        for param, value in tune.items():
            hist = st.param_hist.get(param, [])
            if len(hist) < 5 or param not in clamps:
                continue
            
            total_analyzed += 1
            rng = clamps[param][2] - clamps[param][0]
            if rng <= 0:
                continue
            
            try:
                v_float = float(value)
                # Divide range into 4 bins
                bin_idx = min(3, max(0, int((v_float - clamps[param][0]) / rng * 4)))
                
                # Collect ROIs from this region
                bin_rois = []
                for hist_val, hist_roi in hist:
                    hist_bin = min(3, max(0, int((float(hist_val) - clamps[param][0]) / rng * 4)))
                    if hist_bin == bin_idx:
                        bin_rois.append(hist_roi)
                
                # Bad region: average < threshold
                if len(bin_rois) >= 3:
                    avg_roi = sum(bin_rois) / len(bin_rois)
                    if avg_roi < threshold:
                        bad_params += 1
            except (ValueError, TypeError):
                continue
        
        # ═══ FINAL DECISION ═══
        
        # Skip if >70% of parameters are in bad regions
        if total_analyzed > 0 and bad_params / total_analyzed > 0.70:
            st.record_skip(tune, reason=f'bad_region:{bad_params}/{total_analyzed}')
            return True
        
        # Check if tune is similar to recent skips (avoid repeating mistakes)
        tune_tuple = tuple(sorted(tune.items()))
        if tune_tuple in st.skip_history:
            st.record_skip(tune, reason='repeated_skip')
            return True
        
        st.last_skip_reason = 'passed'
        return False

    # ══════════════════════════════════════════════════════════════════════
    # LEARNER AGENT - Updates state after each iteration
    # ══════════════════════════════════════════════════════════════════════
    
    def _learn(self, old_tune, new_tune, roi, improved, neurons, was_skipped=False):
        """
        Updates entire state based on the result.
        INTEGRATED: Feeds param_hist that FILTER uses for skipping.
        """
        st = self.state
        opts = self.options
        
        # ═══ ALWAYS UPDATE HISTORY (even if not improved) ═══
        for param, value in new_tune.items():
            hist = st.param_hist.setdefault(param, [])
            try:
                hist.append((float(value), roi))
            except (ValueError, TypeError):
                hist.append((value, roi))
            # Keep only last N records
            if len(hist) > opts.bad_region_memory:
                st.param_hist[param] = hist[-opts.bad_region_memory:]
        
        # Reset skip streak when backtest was executed
        if not was_skipped:
            st.reset_skip_streak()
        
        st.evaluated += 1
        
        # ═══ GRADIENTS (direction that worked) ═══
        for param in new_tune:
            if param not in old_tune:
                continue
            try:
                delta = float(new_tune[param]) - float(old_tune[param])
            except (ValueError, TypeError):
                continue
            if delta == 0:
                continue
            
            direction = 1 if delta > 0 else -1
            
            if param not in st.gradients:
                st.gradients[param] = {'direction': 0, 'successes': 0}
            
            if improved:
                if st.gradients[param]['direction'] == direction:
                    st.gradients[param]['successes'] += 1
                else:
                    st.gradients[param] = {'direction': direction, 'successes': 1}
            else:
                st.gradients[param]['successes'] = max(0, st.gradients[param]['successes'] - 0.5)
        
        # ═══ IF IMPROVED: Update elite, synapses, impacts ═══
        if improved:
            # Elite pool
            st.elite.append((roi, deepcopy(new_tune)))
            st.elite.sort(key=lambda x: x[0], reverse=True)
            st.elite = st.elite[:opts.elite_preservation]
            
            # Synapses (neuron combinations that worked)
            neurons_tuple = tuple(neurons) if isinstance(neurons, list) else (neurons,)
            if neurons_tuple not in st.synapses:
                st.synapses.append(neurons_tuple)
            if len(st.synapses) > opts.synapses:
                st.synapses = st.synapses[-opts.synapses:]
            
            # Neuron impact (for MUTATOR prioritization)
            for n in (neurons if isinstance(neurons, list) else [neurons]):
                st.neuron_impacts[n] = st.neuron_impacts.get(n, 0) + 1
            
            # Improvement history (for phase detection)
            st.recent_impr.append(st.iteration)
            if len(st.recent_impr) > 20:
                st.recent_impr.pop(0)
            
            # Temperature: reduce during exploitation
            if st.phase == 'exploitation':
                st.temperature = max(opts.min_temperature, st.temperature * 0.9)
            
            st.improvements += 1
            st.stagnation = 0
            
            # Clear skip_history when good solution found (regions may have changed)
            st.skip_history = []
        else:
            st.stagnation += 1
            # Temperature: increase during exploration
            if st.phase == 'exploration':
                st.temperature = min(opts.max_temperature, st.temperature * 1.05)

    # ══════════════════════════════════════════════════════════════════════
    # MAIN LOOP - Orchestrates the pipeline
    # ══════════════════════════════════════════════════════════════════════
    
    def optimize(self, bot, **kwargs):
        """
        Integrated Pipeline:
        
        ┌──────────────────────────────────────────────────────────────────┐
        │   STATE ──► MUTATOR ──► FILTER ──► EVALUATOR ──► LEARNER         │
        │     │          │          │            │            │            │
        │     │     (generates tune) (skip?)  (backtest)   (updates)       │
        │     │          │          │            │            │            │
        │     └──────────┴──────────┴────────────┴────────────┘            │
        │                      (feedback loop via OptState)                │
        └──────────────────────────────────────────────────────────────────┘
        """
        bot.info = Info({"mode": "optimize"})
        bot.reset()
        st = self.state
        opts = self.options
        
        # ═══ INITIAL BACKTEST ═══
        initial = backtest(deepcopy(bot), self.data, deepcopy(self.wallet), plot=False, **kwargs)
        print("Initial:", json.dumps(initial, indent=2))
        
        bot = bound_neurons(bot)
        coords = list(initial.keys())
        params = list(bot.tune.keys())
        best = {c: [initial.copy(), deepcopy(bot)] for c in coords}
        
        # Feed LEARNER with initial result
        self._learn(bot.tune, bot.tune, self._scalar(initial.get('roi', 0)), False, list(params))
        
        if opts.fitness_ratios is None:
            opts.fitness_ratios = {c: 0 for c in coords}
            opts.fitness_ratios['roi'] = 1
        
        if opts.plot_period:
            plt.ion()
        
        historical = []
        start = time.time()
        
        try:
            while True:
                st.iteration += 1
                
                # ═══ SAFEGUARDS ═══
                if st.iteration > 50000:
                    print(it("red", f"\n⚠️ 50k LIMIT! Backtests:{st.evaluated} ROI:{self._scalar(best['roi'][0]['roi']):.4f}"))
                    break
                
                if opts.cooldown:
                    time.sleep(opts.cooldown)
                
                # Periodic plotting
                if opts.plot_period and st.iteration % opts.plot_period == 0 and historical:
                    plot_scores(historical, [], st.iteration)
                
                # ═══ MUTATOR AGENT ═══
                # Uses state: elite, gradients, neuron_impacts, phase, temperature
                bot = deepcopy(best.get('roi', list(best.values())[0])[1])
                bot, old_tune, neurons = self._mutate(bot, params)
                
                # ═══ FILTER AGENT (Smart Skip) ═══
                # Uses state: param_hist, skip_rate, phase, consecutive_skips
                best_roi = self._scalar(best['roi'][0]['roi'])
                if self._should_skip(bot.tune, best_roi, bot.clamps):
                    # Skip recorded inside _should_skip via st.record_skip()
                    # Temperature already adjusted automatically
                    
                    # Emergency reset if too many consecutive skips
                    if st.consecutive_skips > 100:
                        st.consecutive_skips = 0
                        st.param_hist = {}  # Reset problematic data
                        st.skip_history = []
                        st.temperature = min(opts.max_temperature, st.temperature * 1.5)
                        print(it("yellow", f"⚠️ Reset: {st.evaluated} backtests, skip_rate={st.skip_rate:.0%}"))
                    continue
                
                # ═══ EVALUATOR AGENT ═══
                h = self._hash_tune(bot.tune)
                if opts.enable_cache and h in st.cache:
                    score = st.cache[h]
                else:
                    score = backtest(bot, self.data, self.wallet.copy(), plot=False, **kwargs)
                    if opts.enable_cache:
                        st.cache[h] = score
                
                # Check for improvement
                improved, boom = False, []
                new_roi = self._scalar(score.get('roi', 0))
                
                if new_roi > best_roi:
                    for c in coords:
                        best[c] = (score, deepcopy(bot))
                        boom.append(c)
                    improved = True
                else:
                    for c, (s, _) in list(best.items()):
                        try:
                            if self._scalar(score.get(c, 0)) > self._scalar(s.get(c, 0)):
                                best[c] = (score, deepcopy(bot))
                                boom.append(c)
                                improved = True
                        except:
                            continue
                
                # ═══ LEARNER AGENT ═══
                # Updates: param_hist, gradients, elite, synapses, neuron_impacts, temperature
                self._learn(old_tune, bot.tune, new_roi, improved, neurons)
                
                if improved:
                    historical.append((st.iteration, deepcopy(best)))
                
                # ═══ DISPLAY ═══
                if opts.show_terminal and st.iteration % 10 == 0:
                    printouts({"params": params, "coords": coords, "bot": bot, "score": score,
                               "best": best, "boom": boom, "opts": opts, "state": st, "start": start})
                
                # ═══ EXIT CONDITIONS ═══
                if st.evaluated > opts.epochs:
                    print(it("green", f"\n🎯 COMPLETED! Backtests:{st.evaluated} ROI:{self._scalar(best['roi'][0]['roi']):.4f}"))
                    break
                if st.stagnation > opts.improvements:
                    print(it("yellow", f"\n⚠️ STAGNATED! Backtests:{st.evaluated} Stag:{st.stagnation} ROI:{self._scalar(best['roi'][0]['roi']):.4f}"))
                    break
                if st.stagnation > 500 and st.skip_rate > 0.8:
                    print(it("cyan", f"\n🏁 CONVERGED! Backtests:{st.evaluated} ROI:{self._scalar(best['roi'][0]['roi']):.4f}"))
                    break
        
        except KeyboardInterrupt:
            print(it("yellow", f"\n⏹️ INTERRUPTED! Backtests:{st.evaluated} ROI:{self._scalar(best['roi'][0]['roi']):.4f}"))
        
        end_optimization(best, opts.print_tune)
        return best