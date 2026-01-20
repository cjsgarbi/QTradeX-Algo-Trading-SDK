r"""
            ._____________  ____________________
            |   \______   \/   _____/\_   _____/
            |   ||     ___/\_____  \  |    __)_ 
            |   ||    |    /        \ |        \
            |___||____|   /_______  //_______  /
                                  \/         \/ 

    ╦┌┬┐┌─┐┬─┐┌─┐┌┬┐┬┬  ┬┌─┐  ╔═╗┌─┐┬─┐┌─┐┌┬┐┌─┐┌┬┐┬─┐┬┌─┐
    ║ │ ├┤ ├┬┘├─┤ │ │└┐┌┘├┤   ╠═╝├─┤├┬┘├─┤│││├┤  │ ├┬┘││  
    ╩ ┴ └─┘┴└─┴ ┴ ┴ ┴ └┘ └─┘  ╩  ┴ ┴┴└─┴ ┴┴ ┴└─┘ ┴ ┴└─┴└─┘
          ╔═╗┌─┐┌─┐┌─┐┌─┐  ╔═╗─┐ ┬┌─┐┌─┐┌┐┌┌─┐┬┌─┐┌┐┌     
          ╚═╗├─┘├─┤│  ├┤   ║╣ ┌┴┬┘├─┘├─┤│││└─┐││ ││││     
          ╚═╝┴  ┴ ┴└─┘└─┘  ╚═╝┴ └─┴  ┴ ┴┘└┘└─┘┴└─┘┘└┘     

This module performs parameter optimization using a custom implementation of the
Iterative Parametric Space Expansion (IPSE) algorithm. 

The algorithm iteratively backtests combinations of bot parameters, optimizing for
multiple objectives in parallel. 
It uses multiprocessing to evaluate candidate solutions concurrently and applies
space expansion to focus the search around promising regions.

Main Components:
- IPSE class: core of the optimization logic
- IPSEoptions: configuration for optimization
- printouts: live optimization update display
- retest_process: multiprocessing evaluation function

Dependencies include qtradex for bot logic, numpy for numerical operations, and
multiprocessing for parallelism.
"""

# STANDARD MODULES
import json
import math
import os
import time
from copy import deepcopy
from multiprocessing import Manager, Process

# 3RD PARTY MODULES
import numpy as np
# QTRADEX MODULES
from qtradex.common.utilities import NonceSafe, it, print_table, sigfig
from qtradex.core import backtest
from qtradex.core.base_bot import Info
from qtradex.optimizers.utilities import (bound_neurons, end_optimization,
                                          plot_scores, print_tune)
from qtradex.private.wallet import PaperWallet

# A small number treated as nearly zero
NIL = 10 / 10**10


class IPSEoptions:
    """Configuration class for IPSE optimization."""
    def __init__(self):
        self.acceleration = 0.8  # controls space shrinking factor
        self.space_size = 25  # number of candidate points in parameter space
        self.processes = os.cpu_count() or 3  # number of parallel processes
        self.show_terminal = True  # whether to print optimization stats
        self.print_tune = False  # whether to print final tuned parameters


def printouts(kwargs):
    """
    Print live updates and statistics during optimization.
    
    Args:
        kwargs (dict): Dictionary containing current optimization state and context.
    """
    params = list(kwargs["bot"].tune.keys())  # names of bot parameters
    coords = list(kwargs["score"].keys())  # objective names (e.g., profit, sharpe)

    table = [[""] + params + [""] + coords]  # header row

    # Build the table of best scores
    for n, (score, bot) in enumerate(kwargs["best_bots"].values()):
        table.append(
            [list(score.keys())[n]]
            + list(bot.tune.values())
            + [""]
            + list(score.values())
        )

    n_coords = len(kwargs["score"])
    eye = np.eye(n_coords).astype(int)

    # Color matrix for highlighting improved parameters
    colors = np.vstack(
        (
            np.zeros((len(list(kwargs["bot"].tune.values())) + 2, n_coords + 1)),
            np.hstack((np.zeros((n_coords, 1)), eye)),
        )
    )
    msg = "\033c\n"

    # Highlight current parameter/coordinate pair
    colors[params.index(kwargs["parameter"]) + 1][coords.index(kwargs["coordinate"]) + 1] = 2
    # Highlight improvements
    for i in kwargs["improved"]:
        colors[params.index(i[1]) + 1][coords.index(i[0]) + 1] = 3

    msg += f"{print_table(table, render=True, colors=colors, pallete=[15, 34, 33, 178])}\n"
    msg += f"\nexpansions - {kwargs['expansions']}"
    msg += f"\nepoch {kwargs['epoch']} - Optimized '{kwargs['parameter']}' by {kwargs['coordinate']}"
    msg += f"\n\n{((kwargs['idx'] or 1)/(time.time()-kwargs['ipse_start'])):.2f} Backtests / Second"
    msg += f"\nRunning on {kwargs['self'].data.days} days of data."
    msg += "\n\nCtrl+C to quit and save tune."
    print(msg)


def retest_process(bot, data, wallet, todo, done, **kwargs):
    """
    Worker process that pulls jobs from the todo queue, runs backtests, and saves results.
    
    Args:
        bot: Trading bot instance
        data: Historical data object
        wallet: Wallet instance for simulation
        todo: Shared list of jobs
        done: Shared dict for completed results
    """
    try:
        while True:
            try:
                work = todo.pop(0)  # Get work item
            except IndexError:
                time.sleep(0.02)  # Wait for work
                continue

            bot.tune = work["tune"]  # Set bot parameters

            # Run backtest and store result
            done[work["id"]] = backtest(bot, data, wallet.copy(), plot=False, **kwargs)
    except KeyboardInterrupt:
        print("Compute process ending...")


class IPSE:
    """
    Core optimizer class implementing the IPSE algorithm.

    Args:
        data: Historical data object used for backtesting
        wallet: Optional wallet object, defaults to PaperWallet
        options: IPSEoptions instance for tuning configuration
    """
    def __init__(self, data, wallet=None, options=None):
        if wallet is None:
            wallet = PaperWallet({data.asset: 0, data.currency: 1})
        self.options = options if options is not None else IPSEoptions()
        self.data = data
        self.wallet = wallet

    def retest(self, todo, done, bot, space, parameter):
        """
        Distributes backtests across worker processes and collects the results.

        Args:
            todo: Shared list of pending jobs
            done: Shared dictionary for completed results
            bot: Trading bot instance
            space: List of values to test for the given parameter
            parameter: Parameter name being optimized

        Returns:
            List of backtest result dictionaries in order of space
        """
        for bot_id, test in enumerate(space):
            # Enqueue jobs with modified tune value for parameter
            todo.append({"id": bot_id, "tune": {**bot.tune, parameter: test}})

        while len(done) < len(space):
            time.sleep(0.02)  # Wait for all results

        # Collect and sort results by original order
        new_scores = [(bot_id, result) for bot_id, result in done.items()]
        done.clear()  # Clear shared dictionary

        return [i[1] for i in sorted(new_scores, key=lambda x: x[0])]

    def optimize(self, bot, **kwargs):
        """
        Run the full IPSE optimization loop on a bot instance.

        Args:
            bot: The trading bot to be optimized

        Returns:
            Dictionary of best bots per objective
        """
        bot.info = Info({"mode": "optimize"})
        bot.reset()
        bot = bound_neurons(bot)  # Apply bounds to tune parameters

        coords = backtest(deepcopy(bot), self.data, deepcopy(self.wallet), plot=False, **kwargs)
        print("Initial Backtest:")
        print(json.dumps(coords, indent=4))

        # Setup ranges for all tunable parameters
        ranges = {parameter: [i[0], i[2]] for parameter, i in bot.clamps.items()}
        score = coords.copy()

        # Store best bots for each coordinate (objective)
        best_bots = {coord: [score.copy(), deepcopy(bot)] for coord in coords}

        ipse_start = time.time()
        idx = 0
        epoch = 0
        expansions = 0

        # Start multiprocessing manager for communication between processes
        with Manager() as manager:
            todo = manager.list()
            done = manager.dict()

            # Launch worker processes
            children = [
                Process(
                    target=retest_process,
                    args=(bot, self.data, self.wallet, todo, done),
                    kwargs=kwargs,
                )
                for _ in range(self.options.processes)
            ]
            for child in children:
                child.start()

            try:
                while True:
                    epoch += 1

                    # Loop over each objective coordinate
                    for coordinate in coords:
                        # Loop over each tunable parameter
                        for parameter in bot.tune:
                            if not bot.clamps[parameter][3]:
                                continue
                            # Build test space of values for current parameter
                            space = np.linspace(
                                *ranges[parameter], self.options.space_size
                            ).astype(type(bot.tune[parameter])).tolist() + [bot.tune[parameter]]  # Add current value


                            scores = self.retest(todo, done, bot, space, parameter)
                            idx += len(space)

                            improved = []

                            # Find best score for this coordinate
                            for check_coord in coords:
                                best_idx = np.argmax([i[check_coord] for i in scores])
                                score = scores[best_idx]
                                best = space[best_idx]

                                if best_bots[check_coord][0][check_coord] < score[check_coord]:
                                    improved.append([check_coord, parameter])
                                    best_bots[check_coord][1].tune[parameter] = best
                                    best_bots[check_coord][0] = score.copy()

                            # Print progress if enabled
                            if self.options.show_terminal:
                                printouts(locals())

                    # Expand search space toward best values
                    for parameter, value in bot.tune.items():
                        ranges[parameter][0] = (
                            ranges[parameter][0] * self.options.acceleration
                        ) + (value * (1 - self.options.acceleration))
                        ranges[parameter][1] = (
                            ranges[parameter][1] * self.options.acceleration
                        ) + (value * (1 - self.options.acceleration))

                    expansions += 1

            except KeyboardInterrupt:
                # Save best configurations and exit
                end_optimization(best_bots, self.options.print_tune, asset=self.data.asset, currency=self.data.currency)
                return best_bots
