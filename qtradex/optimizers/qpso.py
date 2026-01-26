r"""
     ________ __________  _________________   
      \_____  \\______   \/   _____/\_____  \  
       /  / \  \|     ___/\_____  \  /   |   \ 
      /   \_/.  \    |    /        \/    |    \
      \_____\ \_/____|   /_______  /\_______  /
             \__>                \/         \/   
                   
    ╔═╗ ┬ ┬┌─┐┌┐┌┌┬┐┬ ┬┌┬┐  ╔═╗┌─┐┬─┐┌┬┐┬┌─┐┬  ┌─┐
    ║═╬╗│ │├─┤│││ │ │ ││││  ╠═╝├─┤├┬┘ │ ││  │  ├┤ 
    ╚═╝╚└─┘┴ ┴┘└┘ ┴ └─┘┴ ┴  ╩  ┴ ┴┴└─ ┴ ┴└─┘┴─┘└─┘
      ╔═╗┬ ┬┌─┐┬─┐┌┬┐  ╔═╗┌─┐┌┬┐┬┌┬┐┬┌─┐┌─┐┬─┐    
      ╚═╗│││├─┤├┬┘│││  ║ ║├─┘ │ │││││┌─┘├┤ ├┬┘    
      ╚═╝└┴┘┴ ┴┴└─┴ ┴  ╚═╝┴   ┴ ┴┴ ┴┴└─┘└─┘┴└─    


github.com/litepresence & github.com/SquidKid-deluxe present:

Quantum Particle Swarm Optimization (QPSO) Script for Trading Strategy Optimization.

This module performs parameter tuning for algorithmic trading strategies using a
sophisticated optimization technique. It implements a variant of Quantum Particle
Swarm Optimization enhanced with:

- N-Dimensional Coordinate Gradient Ascent
- Cyclic Simulated Annealing
- Neuroplastic Synaptic Learning
- Fitness Inversion
- Eroding Score Dynamics

Features:
- Live performance tracking and plotting.
- Customizable tuning via QPSOoptions.
- Modular design for use in backtesting frameworks.

Note: Press Ctrl+C during runtime to terminate optimization gracefully
      and print the best tuning dictionary.
"""
# STANDARD MODULES
import getopt
import itertools
import json
import math
import shutil
import time
from copy import deepcopy
from json import dumps as json_dumps
from multiprocessing import Process
from random import choice, choices, randint, random, sample
from statistics import median
from typing import Any, Dict, List

# 3RD PARTY MODULES
import matplotlib.pyplot as plt
import numpy as np
# QTRADEX MODULES
from qtradex.common.json_ipc import json_ipc
from qtradex.common.utilities import NonceSafe, it, print_table, sigfig
from qtradex.core import backtest
from qtradex.core.base_bot import Info
from qtradex.optimizers.utilities import (bound_neurons, end_optimization,
                                          plot_scores, print_tune)
from qtradex.private.wallet import PaperWallet

NIL = 10 / 10**10


class QPSOoptions:
    def __init__(self):
        self.lag = 0.5
        # plot this top percent of candidates
        self.top_percent = 0.9
        self.plot_period = 100
        self.fitness_ratios = None
        self.fitness_period = 200
        self.fitness_inversion = lambda x: dict(
            zip(x.keys(), [list(x.values())[-1]] + list(list(x.values())[:-1]))
        )
        self.cyclic_amplitude = 3
        self.cyclic_freq = 1000
        self.digress = 0.99
        self.digress_freq = 2500
        self.temperature = 2  # 10 (coarse) to 0.0001 (fine)
        self.epochs = math.inf
        self.improvements = 100000
        self.cooldown = 0
        self.synapses = 50
        self.neurons = []
        self.show_terminal = True
        self.print_tune = True


def printouts(kwargs):
    """
    Print live updates and statistics during a Quantum Particle Swarm Optimization (QPSO) session.
    """
    # Print statistics for solitary QPSO

    table = []
    table.append([""] + kwargs["parameters"] + [""] + kwargs["coords"] + [""])
    table.append(
        ["current test"]
        + list(kwargs["bot"].tune.values())
        + [""]
        + list(kwargs["new_score"].values())
        + [""]
    )
    for coord, (score, bot) in kwargs["best_bots"].items():
        table.append(
            [coord] + list(bot.tune.values()) + [""] + list(score.values()) + ["###"]
        )

    n_coords = len(kwargs["coords"])

    eye = np.eye(n_coords).astype(int)

    colors = np.vstack(
        (
            np.zeros((len(kwargs["parameters"]) + 2, n_coords + 2)),
            np.hstack(
                (
                    np.zeros((n_coords, 2)),
                    eye,
                )
            ),
            np.array(
                [
                    [0, 0]
                    + [
                        2 if i else 0
                        for i in kwargs["self"].options.fitness_ratios.values()
                    ]
                ]
            ),
        )
    )

    for coord in kwargs["boom"]:
        cdx = kwargs["coords"].index(coord)
        colors[len(kwargs["parameters"]) + 2 + cdx, cdx + 2] = 3

    msg = "\033c"
    msg += it(
        "green",
        f"Stochastic {len(kwargs['parameters'])}-Dimensional {n_coords} Coordinate "
        "Ascent with Pruned Neuroplasticity in Eroding Quantum Particle Swarm "
        "Optimization, Enhanced by Cyclic Simulated Annealing",
    )
    msg += "\n\n"
    msg += f"\n{print_table(table, render=True, colors=colors, pallete=[0, 34, 33, 178])}\n"
    msg += f"\n{kwargs['boom']}"
    msg += (
        f"\ntest {kwargs['iteration']} improvements {kwargs['improvements']} synapses"
        f" {len(kwargs['synapses'])}"
    )
    msg += f"\npath {kwargs['path']} aegir {kwargs['aegir']}"
    msg += f"\n{kwargs['synapse_msg']} {it('yellow', kwargs['neurons'])}"
    msg += f"\n\n{((kwargs['idx'] or 1)/(time.time()-kwargs['qpso_start'])):.2f} Backtests / Second"
    msg += f"\nRunning on {kwargs['self'].data.days} days of data."
    msg += "\n\nCtrl+C to quit and show final tune as copyable dictionary."
    print(msg)


class QPSO:
    def __init__(self, data, wallet=None, options=None):
        if wallet is None:
            wallet = PaperWallet({data.asset: 0, data.currency: 1})
        self.options = options if options is not None else QPSOoptions()
        self.data = data
        self.wallet = wallet

    def check_improved(self, new_score, best_bots, improvements):
        """
        Check for improvement upon dual gradient ascent and note the improvement.

        Parameters:
        - improvements (int): Number of improvements made during the session.

        Returns:
        - tuple: Tuple containing updated backup storage, storage, number of improvements,
        boom message, and improvement status.
        """

        improved = False
        boom = ""

        value = random()

        # Stochastic N-Coordinate Gradient Ascent
        for coordinate, (score, _) in enumerate(best_bots):
            key = list(score.keys())[coordinate]
            if new_score[0][key] > score[key]:
                if value < self.options.fitness_ratios[coordinate]:
                    improved = True
                boom += f"!!! BOOM {key.upper()} !!!\n"
                old = best_bots[coordinate][0].copy()

                best_bots[coordinate] = deepcopy(new_score)
                best_bots[coordinate][0][key] = (old[key] * self.options.lag) + (
                    best_bots[coordinate][0][key] * (1 - self.options.lag)
                )

        if improved:
            improvements += 1

        return best_bots, improvements, it("green", boom), improved

    def entheogen(self, i, j, shape=None, min_val=0, max_val=1, is_integer=False):
        """
        Somnambulism induces altered states of consciousness for n-dimensional arrays.
        The update equation guides particles through discrete integer or continuous float
        spaces, respecting given bounds, with a random walk inspired by cyclic annealing
        and quantum PSO. Supports negative ranges and crossing zero.
        Args:
            i (int): The iteration number.
            j (float): Offset for cyclic annealing.
            shape (Union[int | tuple]): The shape of the neuron to be altered.
            min_val (Union[int | float | np.ndarray]): Minimum value(s) for the space.
            max_val (Union[int | float | np.ndarray]): Maximum value(s) for the space.
        Returns:
            Tuple[float, np.ndarray]: A tuple containing the calculated `aegir` and `steps` values.
        """
        # Cyclic simulated annealing
        aegir = (
            self.options.cyclic_amplitude
            * math.sin(((i / self.options.cyclic_freq) + j) * math.pi * 2)
            + 1
            + self.options.cyclic_amplitude
        )

        # Ensure min_val and max_val are arrays matching the shape
        if isinstance(min_val, (int, float)):
            min_val = np.full(
                shape, min_val, dtype=np.int64 if is_integer else np.float64
            )
        if isinstance(max_val, (int, float)):
            max_val = np.full(
                shape, max_val, dtype=np.int64 if is_integer else np.float64
            )
        range_size = max_val - min_val + 1

        # Simple scalar case
        if shape is None:
            if is_integer:
                # Base step size modulated by temperature and aegir
                step_magnitude = max(
                    1, int((self.options.temperature * aegir) ** 0.5 / 50.0) * range_size
                )
                # Random step within [-step_magnitude, step_magnitude]
                steps = randint(-step_magnitude, step_magnitude + 1)
                # Brownian iterator: occasionally invert step direction
                if randint(0, 1) == 0:
                    steps = -steps
            else:
                # Quantum orbital pulse (float)
                path = random() * (self.options.temperature * aegir) / 100.0 * range_size
                # Randomly choose direction to allow crossing zero
                steps = path if randint(0, 1) == 0 else -path
        # N-Dimensional case
        else:
            if is_integer:
                # Base step size modulated by temperature and aegir
                step_magnitude = np.maximum(
                    1, (self.options.temperature * aegir) ** 0.5 / 50.0
                ) * range_size
                # Random steps within [-step_magnitude, step_magnitude] for each element
                steps = np.random.randint(
                    -step_magnitude, step_magnitude + 1, size=shape, dtype=np.int64
                )
                # Brownian iterator: invert steps for half the elements
                mask = np.random.uniform(size=shape) > 0.5
                steps[mask] = -steps[mask]
            else:
                # Quantum orbital pulse (float)
                path = (
                    np.random.uniform(size=shape)
                    * (self.options.temperature * aegir)# ** 0.5
                    / 100.0
                )
                # Randomly choose direction to allow crossing zero
                direction = np.where(np.random.uniform(size=shape) > 0.5, 1, -1)
                steps = path * direction * range_size
                steps = steps.astype(np.float64)

        # Stumbling, yet remarkably determined
        return aegir, steps

    def optimize(self, bot, **kwargs):
        """
        Perform Quantum Particle Swarm Optimization (QPSO) to optimize trading strategies.

        This method iteratively adjusts the bot's parameters using probabilistic and evolutionary
        techniques to discover improved configurations. It maintains historical performance,
        periodically alters exploration dynamics, and adapts based on recent successes (synapses).

        Parameters:
        bot (Bot): The trading bot instance with strategy parameters to optimize.

        Returns:
        dict: Dictionary of the best bots found per evaluation coordinate.
        """
        bot.info = Info({"mode": "optimize"})
        improvements = 0
        iteration = 0  # Tracks exploration loop; decremented on improvements to allow more trials
        idx = 0  # Tracks total iterations, always incremented
        synapses = (
            []
        )  # Stores tuples of past successful neuron groups (parameter names)

        bot.reset()  # Reset bot state before optimization
        bot = bound_neurons(bot)  # Constrain parameters within valid range

        # Initial evaluation and score setup
        initial_result = backtest(
            deepcopy(bot), self.data, deepcopy(self.wallet), plot=False, **kwargs
        )
        print("Initial Backtest:")
        print(json.dumps(initial_result, indent=4))

        coords = list(initial_result.keys())  # Evaluation metrics (e.g., ROI, Sharpe)
        parameters = list(bot.tune.keys())  # Parameters to optimize

        best_bots = {coord: [initial_result.copy(), deepcopy(bot)] for coord in coords}

        # Initialize fitness ratio weights for exploration
        if self.options.fitness_ratios is None:
            self.options.fitness_ratios = {coord: 0 for coord in coords}
            self.options.fitness_ratios[
                coords[0]
            ] = 1  # Default to first metric if not set

        historical = []  # Stores improvement snapshots
        historical_tests = []  # Stores near-optimal attempts

        if self.options.plot_period:
            plt.ion()  # Enable interactive plotting

        try:
            qpso_start = time.time()
            while True:
                if self.options.cooldown:
                    time.sleep(
                        self.options.cooldown
                    )  # Optional delay to reduce CPU load

                iteration += 1
                idx += 1

                # Plot score evolution periodically
                if self.options.plot_period and not idx % self.options.plot_period:
                    plot_scores(historical, historical_tests, idx)

                # Periodically invert fitness preferences (for diversity)
                if not idx % self.options.fitness_period:
                    self.options.fitness_ratios = self.options.fitness_inversion(
                        self.options.fitness_ratios
                    )

                # Allow exploration in suboptimal directions
                if iteration % self.options.digress_freq == 0:
                    best_bots = {
                        coord: [
                            {k: v * self.options.digress for k, v in score.items()},
                            bot,
                        ]
                        for coord, (score, bot) in best_bots.items()
                    }

                # Choose neurons to mutate
                neurons = self.options.neurons or [
                    i for i in parameters if bot.clamps[i][3]
                ]
                for _ in range(3):
                    neurons = sample(population=neurons, k=randint(1, len(neurons)))
                neurons.sort()

                # If past synapses exist, reuse them occasionally (mimics synaptic memory)
                synapse_msg = ""
                if randint(0, 2):
                    if len(synapses) > 2:
                        synapse_msg = it("red", "synapse")
                        neurons = choice(synapses)

                # Limit memory size of synapses (synaptic pruning)
                synapses = (
                    list(set(synapses))[-self.options.synapses :]
                    if self.options.synapses
                    else []
                )

                # Select which coordinate to optimize
                coord = choices(
                    population=list(self.options.fitness_ratios.keys()),
                    weights=list(self.options.fitness_ratios.values()),
                    k=1,
                )[0]
                bot = deepcopy(
                    best_bots[coord][1]
                )  # Start from best bot in selected coordinate

                # Mutate parameters using QPSO mechanisms
                for neuron in neurons:
                    if not bot.clamps[neuron][3]:
                        continue
                    aegir, path = self.entheogen(
                        iteration,
                        parameters.index(neuron) / len(parameters),
                        bot.tune[neuron].shape
                        if isinstance(bot.tune[neuron], np.ndarray)
                        else 1,
                        bot.clamps[neuron][0],  # min
                        bot.clamps[neuron][2],  # max
                        # is it a numpy array of ints?
                        np.issubdtype(bot.tune[neuron].dtype, np.integer)
                        # if it is a numpy array,
                        if isinstance(bot.tune[neuron], np.ndarray)
                        # else is it a single int?
                        else isinstance(bot.tune[neuron], int),
                    )
                    bot.tune[neuron] += path

                bot = bound_neurons(bot)  # Ensure parameter validity

                # Evaluate new configuration
                new_score = backtest(
                    bot, self.data, self.wallet.copy(), plot=False, **kwargs
                )

                boom = []
                improved = False
                for coord, (check_score, _) in best_bots.copy().items():
                    if new_score[coord] > check_score[coord]:
                        best_bots[coord] = (new_score, bot)
                        boom.append(coord)
                        improved = True

                # Optional terminal printout
                if self.options.show_terminal and not idx % 10:
                    printouts(locals())

                # Record successful synapse and save snapshot
                if improved:
                    synapses.append(tuple(neurons))
                    historical.append((idx, deepcopy(best_bots)))
                    iteration -= 1  # Grant extra iterations for progress

                # Log near-optimal scores
                for coord, (score, _) in best_bots.items():
                    if new_score[coord] >= score[coord] * self.options.top_percent:
                        historical_tests.append((idx, new_score.copy()))
                        break

                # Exit if iteration or improvement limits are reached
                if idx > self.options.epochs or iteration > self.options.improvements:
                    raise KeyboardInterrupt

        except KeyboardInterrupt:
            end_optimization(best_bots, self.options.print_tune, asset=self.data.asset, currency=self.data.currency, begin_ts=self.data.begin, end_ts=self.data.end)
            return best_bots
