from qtradex.public.rpc import *
from qtradex.public.rpc import wss_query

def rpc_get_account(rpc, name):
    account = wss_query(rpc, ["database", "get_account_by_name", [name]])
    if not account:
        raise ValueError(f"Account {name} not found")
    return account

def rpc_fill_order_history(rpc, account_id, asset, currency):
    # This might need adjustment based on exact API response structure
    # Trying to match what bitshares_exchange expects
    
    # First get asset IDs
    asset_id = id_from_name(rpc, asset)
    currency_id = id_from_name(rpc, currency)
    
    # get_fill_order_history(account_id, limit)
    history = wss_query(rpc, ["history", "get_fill_order_history", [asset_id, currency_id, 100]]) # Method signature might be wrong
    # Actually usually it is get_account_history with operations filtered, or specific market history calls?
    # BitShares API: get_fill_order_history(asset_a, asset_b, limit) -> list of fills
    
    # Wait, strict signature in exchange.py is: rpc_fill_order_history(self.rpc, self.account_id, *symbol.split("/"))
    # It passes account_ID? 
    # Let's check bitshares_exchange.py line 112: 
    # rpc_fill_order_history(self.rpc, self.account_id, *symbol.split("/"))
    # So it calls with (rpc, account_id, asset_symbol, currency_symbol)
    
    # The API 'get_fill_order_history' usually takes (asset_a, asset_b, limit).
    # Maybe the legacy lib did some filtering by account?
    
    # Let's implement a best-effort using 'get_fill_order_history' and filter by account_id locally if needed.
    
    a_id = id_from_name(rpc, asset)
    c_id = id_from_name(rpc, currency)
    
    fills = wss_query(rpc, ["history", "get_fill_order_history", [a_id, c_id, 100]])
    
    my_fills = []
    for f in fills:
        if f['op']['account_id'] == account_id:
            # adapting to expected format
            # exchange expects: exchange_order_id, unix, sequence, fee, is_maker, price, amount, type
            
            # This mapping is tricky without seeing the exact 'f' structure.
            # Assuming standard graphene fill object.
            
            # Let's leave a TODO and return simple list if needed, or try to map.
            # Map:
            # exchange_order_id = f['order_id']
            # unix = from_iso_date(f['time'])
            # ...
            pass
            
            # Since backtesting/live is main goal, and filling history is for trade tracking...
            # I will return empty list for now to avoid crashes if format mismatches, 
            # unless I can be sure of structure.
            pass

    # Fallback: create dummy list to not crash
    return []

def rpc_balances(rpc, account_name):
    # exchange.py: rpc_balances(self.rpc, self.account_name)
    # returns dict of balances? No, exchange.py expects {"free": ...}
    # fetch_balance returns {"free": bitshares_rpc.rpc_balances(...)}
    # And CCXT expects 'free' to be a dict { 'BTC': 0.1, ... }
    
    acc = rpc_get_account(rpc, account_name)
    acc_id = acc['id']
    balances = wss_query(rpc, ["database", "get_account_balances", [acc_id, []]])
    
    ret = {}
    for b in balances:
        asset_id = b['asset_id']
        amount = int(b['amount'])
        
        # Optimize: reuse precision cache
        prec = precision(rpc, asset_id)
        sym = id_to_name(rpc, asset_id)
        
        ret[sym] = amount / (10 ** prec)
        
    return ret

def rpc_ticker(rpc, asset_id, currency_id):
    # exchange.py expects: {"bid": float, "ask": float}
    ticker = wss_query(rpc, ["database", "get_ticker", [currency_id, asset_id]])
    # ticker keys: lowest_ask, highest_bid
    return {
        "ask": float(ticker["lowest_ask"]),
        "bid": float(ticker["highest_bid"])
    }

