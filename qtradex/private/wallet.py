from copy import deepcopy

import ccxt


BASE_FEE = 1 # in percent

class WalletBase:
    def __init__(self):
        self.balances = {}
        self._readonly = True
        self.fee = BASE_FEE

    def __repr__(self):
        return f"{type(self)}{self.balances}"

    def __getitem__(self, index):
        return self.balances[index]

    def __setitem__(self, index, item):
        if not self._readonly:
            self.balances[index] = item

    def items(self):
        return self.balances.items()

    def keys(self):
        return self.balances.keys()

    def values(self):
        return self.balances.values()

    def copy(self):
        # Create a new instance of the same class
        new_wallet = type(self)(fee=self.fee)
        new_wallet._readonly = self._readonly
        new_wallet.balances = self.balances.copy()
        if hasattr(self, 'price'):
            new_wallet.price = self.price
        return new_wallet

    def value(self, pair, price=None):
        # if this is a live wallet, refresh before taking the wallet value
        if hasattr(self, "refresh"):
            self.refresh()
        if price is None:
            price = self.price
        else:
            self.price = price
        # return (
        #     (self.balances[pair[0]] + self.balances[pair[1]] / price)
        #     * (self.balances[pair[0]] * price + self.balances[pair[1]])
        # ) ** 0.5
        # wolfram alpha simplified:
        return (
            (self.balances[pair[0]] * price + self.balances[pair[1]]) ** 2 / price
        ) ** 0.5


class PaperWallet(WalletBase):
    def __init__(self, balances=None, fee=BASE_FEE):
        super().__init__()
        self.balances = balances if balances is not None else {}
        self._readonly = False
        self.fee = fee

    def _protect(self):
        self._readonly = True

    def _release(self):
        self._readonly = False


class Wallet(WalletBase):
    def __init__(self, exchange):
        super().__init__()
        self._readonly = True
        self.exchange = exchange
        self.refresh()

    def __setitem__(self, *args):
        """
        Live wallet is always read-only
        """

    def refresh(self):
        self.balances = self.exchange.fetch_balance()["free"]
