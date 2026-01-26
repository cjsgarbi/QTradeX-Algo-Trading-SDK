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
    # AION v2025.16: Added 'promising_regions' for guided mutations
    __slots__ = ('iteration', 'improvements', 'stagnation', 'skips', 'evaluated',
                 'cache', 'gradients', 'elite', 'param_hist', 'synapses', 
                 'neuron_impacts', 'recent_impr', 'temperature', 'consecutive_skips',
                 'skip_history', 'last_skip_reason', 'best_trophy', 'promising_regions')
    
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
        self.best_trophy = None     # Best result with MDD < 25% (The Trophy)
        self.promising_regions = {} # AION v2025.16: {param: [values that gave ROI > 1.0]}
    
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
                 'bad_region_memory', 'pareto_mdd_threshold', 'hard_mdd_limit',
                 'quantum_pulse_intensity', 'memory_decay_rate')
    
    def __init__(self):
        self.epochs = math.inf
        self.improvements = 100000
        self.cooldown = 0
        self.show_terminal = True
        self.print_tune = True
        self.show_terminal = True
        self.print_tune = True
        self.plot_period = 200 # AION v2025.15: Reduced plotting freq to avoid UI freeze
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
        self.pareto_mdd_threshold = 0.20  # Início da penalidade (20%)
        self.hard_mdd_limit = 0.25       # Limite de ferro (25%)
        self.quantum_pulse_intensity = 1.5
        self.memory_decay_rate = 0.9     # Taxa de sobrevivência da memória


# ══════════════════════════════════════════════════════════════════════════════
# DISPLAY
# ══════════════════════════════════════════════════════════════════════════════

def printouts(ctx):
    """Compact display of optimization status."""
    def fmt(v):
        """Safe decimal formatter to avoid scientific notation in table."""
        try:
            val = float(v.item()) if hasattr(v, 'item') else float(v)
            if 0 < abs(val) < 0.0001: return f"{val:.4f}"
            return val
        except: return v

    table = [[""] + ctx["params"] + [""] + ctx["coords"] + [""]]
    
    # Safe fetch for current
    curr_row = ["current"] + [fmt(v) for v in ctx["bot"].tune.values()] + [""]
    curr_row += [fmt(ctx["score"].get(c, 0)) for c in ctx["coords"]] + [""]
    table.append(curr_row)
    
    for c, (s, b) in ctx["best"].items():
        row = [c] + [fmt(v) for v in b.tune.values()] + [""]
        row += [fmt(s.get(coord, 0)) for coord in ctx["coords"]] + ["###"]
        table.append(row)
    
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
    
    if st.best_trophy:
        score_t = st.best_trophy['score']
        # Safe float conversion
        def sf(v):
            try: return float(v.item()) if hasattr(v, 'item') else float(v)
            except: return 0.0
        
        # User Preference: ROI as direct percentage of capital
        # ROI is a multiplier: 1.92 = +92% gain, 0.85 = -15% loss
        roi_t = (sf(score_t.get('roi', 1.0)) - 1.0) * 100
        mdd_t = sf(score_t.get('maximum_drawdown', 0.1)) * 100
        wr_t = sf(score_t.get('trade_win_rate', 0.0)) * 100
        msg += it("green", f"🏆 BEST ROI MEMORY (MDD < 25%): ROI={roi_t:.2f}%  MDD={mdd_t:.2f}%  WR={wr_t:.2f}%\n")
    
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
        if st.synapses and len(st.synapses) > 2 and randint(0, 2):
            neurons = list(choice(st.synapses))
            
        # HEAT-MAP SELECTION (Intelligence Boost)
        # 60% chance to focus on impactful neurons, 40% chance for randomness to avoid stagnation
        if st.neuron_impacts and random() < 0.6:
             impactful = sorted(st.neuron_impacts, key=st.neuron_impacts.get, reverse=True)
             candidates = [n for n in impactful if n in (self.options.neurons or params)]
             if candidates:
                 neurons = candidates[:max(1, len(candidates)//2)]
        else:
             neurons = sample(params, k=randint(1, len(params)))
        
        old_tune = bot.tune.copy()
        
        # Crossover with elite (10% chance)
        if st.elite and random() < 0.1:
            bot.tune = self._crossover(bot.tune, bot.clamps)
        
        # Phase-based boost (from state)
        boost = 1.5 + st.stagnation * 0.01 if st.phase == 'exploration' else 1.0
        boost = min(3.0, boost)
        
        # Mutate loop
        success = False
        for _ in range(5):
            temp_tune = bot.tune.copy()
            for n in neurons:
                if not bot.clamps[n][3]: continue
                is_int = isinstance(bot.tune[n], (int, np.integer))
                
                # AION v2025.16: GUIDED MUTATION - Jump TO promising regions
                # 50% chance to target a known profitable region
                if st.promising_regions.get(n) and random() < 0.50:
                    target_value = choice(st.promising_regions[n])
                    step = target_value - bot.tune[n]  # DIRECTED jump
                    # Add small noise to avoid exact duplicates
                    step += (random() - 0.5) * (bot.clamps[n][2] - bot.clamps[n][0]) * 0.05
                else:
                    step = self._levy_step(bot.clamps[n][0], bot.clamps[n][2], boost, n, bot.tune[n])
                
                if is_int: step = int(step) or (1 if random() > 0.5 else -1)
                temp_tune[n] += step
            
            best_roi = self._scalar(self.state.elite[0][0]) if self.state.elite else 0.01
            if not self._should_skip(temp_tune, best_roi, bot.clamps):
                bot.tune = temp_tune
                success = True
                break
            boost *= 1.5 # Quantum Aggression: increase boost to escape bad region
            
        # Emergency Escape: If still failing, force a huge leap
        if not success:
            for n in neurons:
                if not bot.clamps[n][3]: continue
                rng = bot.clamps[n][2] - bot.clamps[n][0]
                bot.tune[n] += (random() - 0.5) * rng * 0.5
        
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
            # SOFT DECAY: Instead of resetting to {}, we decay the impact of old memory
            if isinstance(st.param_hist, dict):
                for p in st.param_hist:
                    if len(st.param_hist[p]) > 5:
                        st.param_hist[p] = st.param_hist[p][int(len(st.param_hist[p]) * 0.5):]
            st.temperature = min(3.0, st.temperature * self.options.quantum_pulse_intensity)
            st.last_skip_reason = 'soft_memory_decay'
            return False
        
        # ═══ BAD REGION ANALYSIS (using param_hist from LEARNER) ═══
        
        bad_params, total_analyzed = 0, 0
        
        # AION v2025.15: Stricter Intelligence (Avoid "Results Ruins")
        # If we have a profitable config (>1.0), we aggressively skip losing regions (<1.0)
        # We also increased the requirement relative to best_roi (30% -> 60%)
        if best_roi > 1.0:
            threshold = max(0.98, best_roi * 0.60)
        else:
            threshold = best_roi * 0.90 # If failing, only accept things near the "best failure"

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
        
        # Skip if >50% (was 70%) of parameters are in bad regions
        # We want to exit bad paths faster.
        if total_analyzed > 0 and bad_params / total_analyzed > 0.50:
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
        
        # ═══ ALWAYS UPDATE HISTORY (using Balanced Score for Smart Skip) ═══
        for param, value in new_tune.items():
            hist = st.param_hist.setdefault(param, [])
            try:
                hist.append((float(value), roi)) # Note: Using passed roi/balanced score
            except (ValueError, TypeError):
                hist.append((value, roi))
            
            # Synaptic Interaction Memory: Learn which pairs are bad
            if len(new_tune) > 1:
                for other_p, other_v in new_tune.items():
                    if other_p == param: continue
                    pair_key = tuple(sorted([param, other_p]))
                    pair_hist = st.param_hist.setdefault(pair_key, [])
                    try:
                        pair_hist.append(((float(value), float(other_v)), roi))
                    except:
                        pass
                    if len(pair_hist) > opts.bad_region_memory:
                        st.param_hist[pair_key] = pair_hist[-opts.bad_region_memory:]

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
            
            # AION v2025.16: Learn PROMISING REGIONS for guided mutations
            # Only save regions that actually made money (ROI > 1.0)
            if roi > 1.0:
                for param, value in new_tune.items():
                    regions = st.promising_regions.setdefault(param, [])
                    try:
                        regions.append(float(value))
                    except (ValueError, TypeError):
                        regions.append(value)
                    # Keep only top 20 best values per parameter
                    if len(regions) > 20:
                        regions.pop(0)
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
        
        # 🏆 Initialize Trophy with initial result if it qualifies
        # CRITÉRIO: ROI > 1.0 (lucro positivo) E MDD < 25%
        init_roi = self._scalar(initial.get('roi', 1.0))
        init_mdd = self._scalar(initial.get('maximum_drawdown', 0.5))
        if init_mdd <= 0.25 and init_roi > 1.0:
            self.state.best_trophy = {'score': deepcopy(initial), 'bot': deepcopy(bot)}
        
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
                # Seed from Trophy (20% chance) to overcome records
                if st.best_trophy and random() < 0.20:
                    bot = deepcopy(st.best_trophy['bot'])
                else:
                    bot = deepcopy(best.get('roi', list(best.values())[0])[1])
                
                bot, old_tune, neurons = self._mutate(bot, params)
                
                # ═══ FILTER AGENT (Smart Skip) ═══
                # Uses state: param_hist, skip_rate, phase, consecutive_skips
                best_roi = self._scalar(best['roi'][0]['roi'])
                if self._should_skip(bot.tune, best_roi, bot.clamps):
                    # Skip recorded inside _should_skip via st.record_skip()
                    # Temperature already adjusted automatically
                    
                    # Micro-Reheat Pulse: If stuck, increase temperature instead
                    if st.consecutive_skips > 20:
                        st.temperature = min(self.options.max_temperature, 
                                            st.temperature * self.options.quantum_pulse_intensity)
                        
                    continue

                
                # ═══ EVALUATOR AGENT ═══
                h = self._hash_tune(bot.tune)
                if opts.enable_cache and h in st.cache:
                    score = st.cache[h]
                else:
                    score = backtest(bot, self.data, self.wallet.copy(), plot=False, **kwargs)
                    if opts.enable_cache:
                        st.cache[h] = score
                
                # Check for improvement using Balanced Score (ROI vs Risk vs WinRate)
                improved, boom = False, []
                new_roi = self._scalar(score.get('roi', 1.0))
                new_mdd = self._scalar(score.get('maximum_drawdown', 0.01))
                new_wr = self._scalar(score.get('trade_win_rate', 0.0))
                
                # ════════════════════════════════════════════════════════════════
                # 🛡️ BALANCED SCORE COM BARREIRA DUPLA (SUAVE + FERRO)
                # ════════════════════════════════════════════════════════════════
                
                # HARD LIMIT: Immediate rejection if MDD > Limit
                if new_mdd > opts.hard_mdd_limit:
                    new_balanced = -1.0
                    mdd_penalty = 0.0
                else:
                    # Sigmoidal MDD Penalty (Safe Barrier at pareto_mdd_threshold)
                    # 1.0 until threshold, then drops exponentially
                    mdd_penalty = 1.0 / (1.0 + math.exp(20.0 * (new_mdd - opts.pareto_mdd_threshold)))
                    
                    # WinRate Penalty (Threshold at 45%)
                    wr_penalty = 1.0
                    if new_wr < 0.45:
                        wr_penalty = 1.0 / (1.0 + math.exp(20.0 * (0.45 - new_wr)))
                    
                    # Balanced Score: ROI weighted by Risk/WR penalties (ROI is already Net Return)
                    new_balanced = (new_roi * (new_wr + 0.01) * mdd_penalty * wr_penalty)
                
                best_roi_val = self._scalar(best['roi'][0].get('roi', 1.0))
                best_mdd_val = self._scalar(best['roi'][0].get('maximum_drawdown', 0.1))
                best_wr_val = self._scalar(best['roi'][0].get('trade_win_rate', 0.0))
                
                # Same formula for the current best
                best_mdd_penalty = 1.0 / (1.0 + math.exp(20.0 * (best_mdd_val - opts.pareto_mdd_threshold)))
                best_wr_penalty = 1.0 / (1.0 + math.exp(20.0 * (0.45 - best_wr_val))) if best_wr_val < 0.45 else 1.0
                best_balanced = (best_roi_val * (best_wr_val + 0.01) * best_mdd_penalty * best_wr_penalty)
                
                # 🔒 ELITE PROTECTION: ROI can NEVER decrease unless MDD improved significantly
                roi_improved = new_roi > best_roi_val
                mdd_improved = new_mdd < (best_mdd_val * 0.90) # 10% relative improvement in risk
                balanced_improved = new_balanced > best_balanced
                
                # USER CONSTRAINT: "Dynamic ROI/WR evolution as long as MDD < 25%"
                # If we are in the SAFE ZONE (MDD < 25%), we accept ROI gains more aggressively.
                is_safe_zone = new_mdd <= 0.25
                
                # Risk Explosion only applies if we breach the hard limit
                # We relax the "relative increase" check if we are still safely under 25%
                risk_breach = new_mdd > 0.25
                
                if risk_breach:
                    # If we breach 25%, we only accept if it's a massive ROI gain that might justify it (rare)
                    # or if we are just moving from a huge breach to a smaller breach
                     accept_roi = False
                else:
                    # In Safe Zone: Accept if ROI improves, OR if Balanced Score improves (covers Win Rate)
                    # CRITICAL: ROI MUST BE POSITIVE. We do not accept improvements in "losing less".
                    accept_roi = (roi_improved or balanced_improved) and new_roi > 0

                # Special Case: Reducing Risk significantly while keeping similar ROI (must be positive)
                risk_optimization = mdd_improved and new_roi >= (best_roi_val * 0.95) and new_roi > 0

                if (accept_roi and not risk_breach) or risk_optimization:
                    best['roi'] = (score, deepcopy(bot))
                    boom.append('roi')
                    improved = True
                
                # 🏆 BEST ROI MEMORY (The Trophy - Glass Zone 0-25% MDD)
                # CRITÉRIO: ROI > 1.0 (lucro positivo) E MDD < 25%
                # NÃO aceita ROI negativo, apenas resultados com lucro real
                if new_mdd <= 0.25 and new_roi > 1.0:
                    if st.best_trophy is None:
                        st.best_trophy = {'score': deepcopy(score), 'bot': deepcopy(bot)}
                    else:
                        trophy_roi = self._scalar(st.best_trophy['score'].get('roi', 0))
                        trophy_mdd = self._scalar(st.best_trophy['score'].get('maximum_drawdown', 1.0))
                        
                        # Case 1: Better ROI (Primary goal)
                        if new_roi > (trophy_roi + 1e-6):
                            st.best_trophy = {'score': deepcopy(score), 'bot': deepcopy(bot)}
                        
                        # Case 2: Lower MDD (Better risk)
                        # If MDD is significantly better and ROI is not ruined, we update
                        elif new_mdd < (trophy_mdd - 0.001) and new_roi >= (trophy_roi - 0.001):
                            st.best_trophy = {'score': deepcopy(score), 'bot': deepcopy(bot)}

                # Other coords: Updated individually (preserve diversity)

                # Other coords: Updated individually (preserve diversity)
                for c, (s, _) in list(best.items()):
                    if c == 'roi':
                        continue  # Already handled above
                    try:
                        new_val = self._scalar(score.get(c, 0))
                        best_val = self._scalar(s.get(c, 0))
                        
                        # LOGIC FIX: Minimize Bad Metrics, Maximize Good Metrics
                        is_bad_metric = c in ['maximum_drawdown', 'drawdown_duration', 'risk', 'ulcer_index']
                        
                        improved_metric = False
                        if is_bad_metric:
                            # MINIMIZE (Lower is better)
                            # Must be > 0 to be valid risk metric usually, but let's assume raw value
                            if new_val < best_val:
                                improved_metric = True
                        else:
                            # MAXIMIZE (Higher is better)
                            if new_val > best_val:
                                improved_metric = True
                        
                        if improved_metric:
                            best[c] = (score, deepcopy(bot))
                            boom.append(c)
                            improved = True
                    except:
                        continue
                
                # ═══ LEARNER AGENT ═══
                # Updates: param_hist, gradients, elite, synapses, neuron_impacts, temperature
                # CRITICAL: We pass 'new_balanced' instead of 'new_roi'. 
                # If MDD > Limit, new_balanced is low/negative. This teaches AION that this region is BAD.
                self._learn(old_tune, bot.tune, new_balanced, improved, neurons)
                
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
                
                # AION v2025.15: Increased Convergence Limit (was 500)
                if st.stagnation > 1000:
                    print(it("cyan", f"\n🏁 CONVERGED (Stagnation Limit Reached > 1000)! Backtests:{st.evaluated} ROI:{self._scalar(best['roi'][0]['roi']):.4f}"))
                    break
                
                # AION v2025.15: Memory Leak Protection
                if len(st.cache) > 10000:
                    st.cache = {} # Flush cache to prevent RAM accumulation
                
                # Dynamic Reheat (Quantum Pulse) during exploitation if stagnant
                if st.stagnation > 20 and st.phase == 'exploitation':
                    st.temperature = min(opts.max_temperature, st.temperature * 1.1)
        
        except KeyboardInterrupt:
            print(it("yellow", f"\n⏹️ INTERRUPTED! Backtests:{st.evaluated} ROI:{self._scalar(best['roi'][0]['roi']):.4f}"))
        
        # 🏆 FINAL TROPHY CHECK: Use the Trophy as the ultimate winner for Export
        if st.best_trophy:
            t_score = st.best_trophy['score']
            t_roi = self._scalar(t_score.get('roi', 0))
            
            # Identify coordinates that should be replaced (roi, cagr)
            roi_coords = [c for c in best.keys() if any(k in c.lower() for k in ['roi', 'cagr'])]
            
            replaced = False
            for coord in roi_coords:
                current_val = self._scalar(best[coord][0].get('roi', 0))
                if t_roi > (current_val + 1e-6):
                    best[coord] = (deepcopy(t_score), deepcopy(st.best_trophy['bot']))
                    replaced = True
            
            if replaced:
                final_roi_pct = (t_roi - 1.0) * 100
                print(it("green", f"🏆 Replacing Output with BEST ROI MEMORY (Trophy ROI: {final_roi_pct:.2f}%)"))

        end_optimization(best, opts.print_tune, asset=self.data.asset, currency=self.data.currency, begin_ts=self.data.begin, end_ts=self.data.end)
        return best
