"""
Full listing of QPSO Fitness Cost Functions:

Fitness:
- The fitness function calculates various performance metrics based on the bot's balance history and trade states:
  - **ROI (Return on Investment)**: Measures the profitability of the strategy.
  - **CAGR (Compound Annual Growth Rate)**: The annual growth rate of the investment.
  - **Sharpe Ratio**: Measures the risk-adjusted return.
  - **Sortino Ratio**: Similar to the Sharpe ratio, but focuses on downside risk.
  - **Maximum Drawdown**: The largest drop in account balance from a peak to a trough.
  - **Calmar Ratio**: The ratio of CAGR to maximum drawdown.
  - **Omega Ratio**: The ratio of profits to losses.
  - **Beta**: Measures the volatility of the bot relative to the market.
  - **Alpha**: The excess return over the market return.
  - **Information Ratio**: Measures the risk-adjusted performance relative to a benchmark.
  - **Profit Factor**: The ratio of total profits to total losses.
  - **Trade Win Rate**: The percentage of profitable trades.
  - **Payoff Ratio**: The ratio of wins to losses in terms of value.
  - **Skewness and Kurtosis**: Statistical measures of the distribution of returns.
  - **Efficiency Ratio**: Measures how efficiently the bot is trading.
  - **Drawdown Duration**: The length of time it takes to recover from a drawdown.
  - **Hurst Exponent**: Measures the long-term memory of the
"""
import functools
import itertools
import math

import numpy as np
import scipy.stats


def roi_assets(balances, prices, pair):
    initial_balance = balances[0][pair[1]] + balances[0][pair[0]] * prices[0]
    final_balance = balances[-1][pair[1]] + balances[-1][pair[0]] * prices[-1]

    # Calculate ROI as percent increase
    # add one because we want "X" i.e. 1 is break even 2 is 100% gain
    return ((final_balance - initial_balance) / initial_balance) + 1


def roi_currency(balances, prices, pair):
    initial_balance = balances[0][pair[0]] + balances[0][pair[1]] / prices[0]
    final_balance = balances[-1][pair[0]] + balances[-1][pair[1]] / prices[-1]

    # Calculate ROI as percent increase
    # add one because we want "X" i.e. 1 is break even 2 is 100% gain
    return ((final_balance - initial_balance) / initial_balance) + 1


def roi_static(balances, prices, pair):
    return (
        roi_assets([balances[0], balances[0]], prices, pair)
        * roi_currency([balances[0], balances[0]], prices, pair)
    ) ** 0.5


def roi_gross(balances, prices, pair, percent_cheats):
    """
    # Calculate the geometric mean of the return on investment
    sqrt(roi_assets*roi_currency)
    """
    return (
        ((roi_assets(balances, prices, pair) * roi_currency(balances, prices, pair)) ** 0.5)
        / roi_static(balances, prices, pair)
    ) * (1 + (percent_cheats / 100))


def cagr(balances, unix_timestamps):
    """
    Calculate the Compound Annual Growth Rate (CAGR).

    Parameters:
    balances (list): List of balance values over time.
    unix_timestamps (list): List of corresponding Unix timestamps.

    Returns:
    float: The CAGR as a decimal.
    """
    ending_value = balances[-1]
    beginning_value = balances[0]
    years = (unix_timestamps[-1] - unix_timestamps[0]) / (60 * 60 * 24 * 365)
    return (ending_value / beginning_value) ** (1 / years) - 1


def sharpe_ratio(roi, wins=[], losses=[], risk_free_rate=1.05):
    """
    Calculate the Sharpe Ratio.

    Parameters:
    roi (float): The average return of the portfolio.
    risk_free_rate (float): The return on a risk-free investment (default is 1.05).
    wins (list): List of winning trades.
    losses (list): List of losing trades.

    Returns:
    float: The Sharpe Ratio.
    """
    portfolio_std_dev = np.std(wins + losses)
    return (roi - risk_free_rate) / (portfolio_std_dev or 1)


def sortino_ratio(roi, losses=[], risk_free_rate=1.05):
    """
    Calculate the Sortino Ratio.

    Parameters:
    roi (float): The average return of the portfolio.
    risk_free_rate (float): The return on a risk-free investment (default is 1.05).
    losses (list): List of losing trades.

    Returns:
    float: The Sortino Ratio.
    """
    downside_deviation = np.std(functools.reduce(lambda x, y: x * y, losses)) if losses else 1

    if downside_deviation == 0:
        downside_deviation = 1

    return (roi - risk_free_rate) / downside_deviation


def maximum_drawdown(balances):
    """
    Calculate the Maximum Drawdown (MDD).

    Parameters:
    balances (list): List of balance values over time.

    Returns:
    float: The Maximum Drawdown as a decimal.
    """
    peak = max(balances)
    trough = min(balances)
    return (peak - trough) / peak


def calmar_ratio(cagr_value, maximum_drawdown_value):
    """
    Calculate the Calmar Ratio.

    Parameters:
    cagr_value (float): The Compound Annual Growth Rate.
    maximum_drawdown_value (float): The Maximum Drawdown.

    Returns:
    float: The Calmar Ratio.
    """
    return cagr_value / -maximum_drawdown_value


def omega_ratio(wins, losses):
    """
    Calculate the Omega Ratio.

    Parameters:
    wins (list): List of winning trades.
    losses (list): List of losing trades.

    Returns:
    float: The Omega Ratio.
    """
    return sum(wins) / (sum(losses) or 1)


def beta(tick_roi, tick_hold):
    """
    Calculate the Beta of a portfolio.

    Parameters:
    tick_roi (list): List of returns of the portfolio.
    tick_hold (list): List of market returns.

    Returns:
    float: The Beta value.
    """
    return np.cov(tick_roi, tick_hold)[0][1] / np.var(tick_hold)


def alpha(roi, beta, market_return, risk_free_rate=1.05):
    """
    Calculate Jensen's Alpha.

    Parameters:
    roi (float): The actual return of the portfolio.
    beta (float): The portfolio's sensitivity to the market.
    market_return (float): The return of the market or benchmark.
    risk_free_rate (float): The return on a risk-free investment (default is 1.05).

    Returns:
    float: The Alpha value.
    """
    return roi - (risk_free_rate + beta * (market_return - risk_free_rate))


def information_ratio(roi, alpha, tracking_error):
    """
    Calculate the Information Ratio (IR).

    Parameters:
    roi (float): The average return of the portfolio.
    alpha (float): The excess return of the portfolio over the benchmark's expected return.
    tracking_error (float): The standard deviation of the difference between the portfolio's returns and the benchmark's returns.

    Returns:
    float: The Information Ratio.
    """
    return (roi - alpha) / tracking_error


def profit_factor(wins, losses):
    """
    Calculate the Profit Factor.

    Parameters:
    wins (list): List of winning trades.
    losses (list): List of losing trades.

    Returns:
    float: The Profit Factor.
    """
    total_profit = sum(wins)
    total_loss = sum(losses)
    return total_profit / (total_loss or 1)


def trade_win_rate(wins, total_trades):
    """
    Calculate the Trade Win Rate.

    Parameters:
    wins (list): List of winning trades.
    total_trades (int): Total number of trades executed.

    Returns:
    float: The Win Rate as a decimal.
    """
    return (len(wins) / total_trades) if total_trades > 0 else 0


def payoff_ratio(wins, losses):
    """
    Calculate the Payoff Ratio.

    Parameters:
    wins (list): List of winning trades.
    losses (list): List of losing trades.

    Returns:
    float: The Payoff Ratio.
    """
    avg_profit = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 1  # Avoid division by zero
    return avg_profit / avg_loss


def skewness(data):
    """
    Calculate the Skewness of a dataset.

    Parameters:
    data (list): List of data points.

    Returns:
    float: The Skewness value.
    """
    return -abs(scipy.stats.skew(data))


def kurtosis(data):
    """
    Calculate the Kurtosis of a dataset.

    Parameters:
    data (list): List of data points.

    Returns:
    float: The Kurtosis value.
    """
    return -scipy.stats.kurtosis(data)


def efficiency_ratio(roi, wins, losses):
    """
    Calculate the Efficiency Ratio (ER).

    Parameters:
    roi (float): The average return of the portfolio.
    wins (list): List of winning trades.
    losses (list): List of losing trades.

    Returns:
    float: The Efficiency Ratio.
    """
    mean_return = roi
    mean_absolute_deviation = np.mean(np.abs(wins + losses))  # Mean of absolute deviations
    return mean_return / mean_absolute_deviation if mean_absolute_deviation != 0 else 0


def drawdown_duration(trades):
    """
    Calculate the duration of drawdowns.

    Parameters:
    trades (list): List of trades with profit and timestamp.

    Returns:
    float: The total duration of drawdowns.
    """
    if not trades:
        return 0
    drawdown_duration = 0
    p_time = trades[0]["unix"]
    for trade in trades[1:]:
        if trade["roi"] < 1:
            drawdown_duration += trade["unix"] - p_time  # Continue adding duration
        p_time = trade["unix"]
    return -drawdown_duration


def hurst_exponent(trades):
    """
    Calculate the Hurst Exponent.

    Parameters:
    trades (list): List of trade values.

    Returns:
    float: The Hurst Exponent.
    """
    if not trades:
        return 0
    R = max(trades) - min(trades)
    S = np.std(trades)
    n = len(trades)
    return np.log(R / S) / np.log(n) if n > 0 else 0


def days_per_trade(states, target, roi):
    trades = states["detailed_trades"]
    begin = states["begin"]
    end = states["end"]
    if len(trades) < 2:
        return float("-inf")

    elapseds = [
        (t1 - t2) / 86400
        for t2, t1 in itertools.pairwise([begin, *[i["unix"] for i in trades], end])
    ]
    raw_dpt = sorted(elapseds)[(len(trades) - 1) // 2]

    # raw_dpt = (days / len(trades))
    ret = -abs(target - raw_dpt) - abs(target - min(elapseds)) - abs(target - max(elapseds))

    return ret / roi


def percent_cheats(states):
    trades = states["detailed_trades"]
    begin = states["begin"]
    end = states["end"]
    elapseds = [
        (t1 - t2) for t2, t1 in itertools.pairwise([begin, *[i["unix"] for i in trades], end])
    ]

    return ((
        sum([1 if elap < states["candle_size"] * 3 else 0 for elap in elapseds]) / len(trades)
    ) * -100) if trades else 0


def close_to(array, lower_bound, upper_bound):
    # Initialize a score array
    scores = np.zeros(array.shape)

    # Calculate individual scores
    scores[array < lower_bound] = lower_bound - array[array < lower_bound]
    scores[array > upper_bound] = array[array > upper_bound] - upper_bound
    # Calculate overall score (sum of individual scores)
    overall_score = -np.mean(scores)
    return overall_score


def fitness(keys, states, raw_states, asset, currency):
    # Initialize a dictionary to hold the results
    results = {}
    keys.append("roi")

    target_dpt = 0
    if any(target := [key.startswith("dpt_") for key in keys]):
        target_dpt = float(keys[target.index(True)].rsplit("_", 1)[1])
        keys.pop(target.index(True))
        keys.append("dpt")

    # Define a mapping of keys to their corresponding functions and parameters
    # fmt: off
    calculations = {
        "percent_cheats": (percent_cheats, (states,)),
        "roi_assets": (roi_assets, (raw_states["balances"], raw_states["close"], (asset, currency))),
        "roi_currency": (roi_currency, (raw_states["balances"], raw_states["close"], (asset, currency))),
        "roi": (roi_gross, (raw_states["balances"], raw_states["close"], (asset, currency), None)),
        "cagr": (cagr, (states["balance_values"], raw_states["unix"])),
        "sharpe_ratio": (sharpe_ratio, (None, states["wins"], states["losses"])),
        "sortino_ratio": (sortino_ratio, (None, states["losses"])),
        "maximum_drawdown": (maximum_drawdown, (states["balance_values"],)),
        "calmar_ratio": (calmar_ratio, (None, None)),
        "omega_ratio": (omega_ratio, (states["wins"], states["losses"])),
        "beta": (beta, (states["balance_values"], states["hold_states"])),
        "alpha": (alpha, (None, None, states["hold"])),
        "info_ratio": (information_ratio, (None, None, None)),
        "profit_factor": (profit_factor, (states["wins"], states["losses"])),
        "trade_win_rate": (trade_win_rate, (states["wins"], len(states["trades"]))),
        "payoff_ratio": (payoff_ratio, (states["wins"], states["losses"])),
        "skewness": (skewness, (states["trades"],)),
        "kurtosis": (kurtosis, (states["trades"],)),
        "efficiency_ratio": (efficiency_ratio, (None, states["wins"], states["losses"])),
        "drawdown_duration": (drawdown_duration, (states["detailed_trades"],)),
        "hurst_exponent": (hurst_exponent, (states["trades"],)),
        "dpt": (days_per_trade, (states, target_dpt, None)),
    }
    # fmt: on

    added = []

    # Ensure dependencies are calculated
    for key in keys:
        added.extend({
            "roi": ["percent_cheats"],
            "sharpe_ratio": ["roi"],
            "sortino_ratio": ["roi"],
            "calmar_ratio": ["cagr", "maximum_drawdown"],
            "alpha": ["roi", "beta"],
            "info_ratio": ["roi", "alpha"],
            "efficiency_ratio": ["roi"],
            "dpt": ["roi"],
        }.get(key, []))

    added = [i for i in added if i not in keys]

    keys.extend(added)
    keys = list(set(keys))

    # and ensure they are calculated first
    keys.sort(
        key=lambda x: {
            "percent_cheats": 0,
            "roi": 1,
            "cagr": 2,
            "maximum_drawdown": 3,
            "beta": 4,
            "alpha": 5,
        }.get(x, float("inf"))
    )
    # Calculate the values based on the keys provided
    for key, (func, params) in calculations.items():
        if key in keys:
            # Handle cases where some parameters depend on previous calculations
            # the order of keys ensures they already exist
            if key == "roi":
                params = (
                    raw_states["balances"],
                    raw_states["close"],
                    (asset, currency),
                    results["percent_cheats"],
                )
            elif key == "sharpe_ratio":
                params = (results["roi"], states["wins"], states["losses"])
            elif key == "sortino_ratio":
                params = (results["roi"], states["losses"])
            elif key == "calmar_ratio":
                params = (results["cagr"], results["maximum_drawdown"])
            elif key == "alpha":
                params = (results["roi"], results["beta"], states["hold"])
            elif key == "info_ratio":
                params = (
                    results["roi"],
                    results["alpha"],
                    results["beta"],
                    np.std(np.subtract(states["balance_values"], states["hold_states"])),
                )
            elif key == "efficiency_ratio":
                params = (results["roi"], states["wins"], states["losses"])
            elif key == "dpt":
                params = (
                    states,
                    target_dpt,
                    results["roi"],
                )

            # Call the function and store the result
            results[key] = func(*params)

    for key in keys:
        if key.startswith("ind:"):
            name = key.split("ind:", 1)[1].rsplit(":", 1)[0]
            intended_range = [
                float(i) for i in key.split("ind:", 1)[1].rsplit(":", 1)[1].split("~")
            ]
            results["ind:" + name] = (
                close_to(raw_states["indicator_states"][name].flatten(), *intended_range)
                / results["roi"]
            )

    results = {k:v for k, v in results.items() if k not in added}

    return results