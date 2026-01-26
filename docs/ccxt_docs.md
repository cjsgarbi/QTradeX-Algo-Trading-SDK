CCXT API CALLS
===========================================
---

### Limit Orders
--------------------------------

`createOrder(symbol, side, type, amount, price)`

**Parameters:**

- `symbol` (String, required): The Unified CCXT market symbol (e.g., "BTC/USDT").
- `side` (String, required): Direction of the order, either `"buy"` or `"sell"`.
- `type` (String, required): The type of order. For a limit order, use `"limit"`.
- `amount` (Float, required): The amount of the base currency to buy or sell.
- `price` (Float, required): The price at which the order should be filled, expressed in units of the quote currency.

**Returns:**

- An order structure, representing the details of the successfully placed order.

---

### Canceling Orders
--------------------------------

`cancelOrder(id, symbol)`

**Parameters:**

- `id` (String, required): The unique order ID (e.g., `"1645807945000"`).
- `symbol` (String, required): The Unified CCXT market symbol (e.g., `"BTC/USDT"`), required by some exchanges.

**Returns:**

- The order structure of the canceled order.

---

`cancelOrders(ids, symbol)`

**Parameters:**

- `ids` (Array of Strings, required): An array of order IDs (e.g., `["1645807945000"]`).
- `symbol` (String, required): The Unified CCXT market symbol (e.g., `"BTC/USDT"`), required by some exchanges.

**Returns:**

- An array of order structures representing the canceled orders.

---

`async cancelAllOrders(symbol)`

**Parameters:**

- `symbol` (String, required): The Unified CCXT market symbol (e.g., `"BTC/USDT"`).

**Returns:**

- An array of order structures representing all canceled orders.

---

### Exceptions Upon Canceling Orders
------------------------------------
- `cancelOrder()` is typically used on open orders. However, if an order has already been filled (executed and closed) before the cancel request is received, the request may attempt to cancel a non-existent order.
- The request may throw an `OperationFailed` exception, indicating that the order may or may not have been canceled successfully. In such cases, it may be necessary to retry the cancel request.
- Consecutive calls to `cancelOrder()` may target an already canceled order, potentially causing the `OrderNotFound` exception.

---

### Open Orders
--------------------------------

`fetchOpenOrder(id, symbol = undefined)`

`fetchOpenOrders(symbol = undefined)`

**Returns:**

- The order structure representing an open order, or an array of open orders if `fetchOpenOrders` is used.

---

### Balances
--------------------------------

`fetchBalance(params = {})`

**Parameters:**

- `params` (Dictionary, optional): A dictionary of optional parameters, such as `{"currency": "USDT"}` to specify a particular currency.

**Returns:**

- A balance structure, detailing the free, used, and total balances for various currencies.

---



### Price Tickers
--------------------------------
A price ticker contains statistical data for a particular market/symbol, usually representing the last 24 hours of trading activity. The methods for fetching tickers are described below.

---

#### A Single Ticker For One Symbol

`fetchTicker(symbol, params = {})`

**Example:**

```
fetchTicker('ETH/BTC')
fetchTicker('BTC/USDT')
```


CCXT RETURNED DATA STRUCTURE
===========================================


### Order Structure
-------------------------------------------

```json
{
    "id": "12345-67890:09876/54321",  // Order ID
    "clientOrderId": "abcdef-ghijklmnop-qrstuvwxyz",  // Optional client-defined order ID
    "datetime": "2017-08-17 12:42:48.000",  // ISO8601 timestamp of order creation
    "timestamp": 1502962946216,  // Unix timestamp (milliseconds)
    "lastTradeTimestamp": 1502962956216,  // Timestamp of the most recent trade on this order
    "status": "open",  // Status of the order: "open", "closed", "canceled", "expired", "rejected"
    "symbol": "ETH/BTC",  // Market symbol
    "type": "limit",  // Order type: "market" or "limit"
    "timeInForce": "GTC",  // Time-in-force: "GTC", "IOC", "FOK", "PO"
    "side": "buy",  // Order side: "buy" or "sell"
    "price": 0.06917684,  // Price in quote currency (for limit orders)
    "average": 0.06917684,  // Average fill price
    "amount": 1.5,  // Amount of base currency ordered
    "filled": 1.1,  // Amount of base currency filled
    "remaining": 0.4,  // Remaining amount to be filled
    "cost": 0.076094524,  // Total cost for filled amount: "filled" * "price"
    "trades": [ ],  // List of trades or executions related to the order
    "fee": {  // Fee details
        "currency": "BTC",  // Fee currency (usually quote currency)
        "cost": 0.0009,  // Fee amount in the fee currency
        "rate": 0.002  // Fee rate (if available)
    },
    "info": { }  // The original unparsed order response
}
```

---

### Balance Structure
-------------------------------------------

```json
{
    "info": { },  // The original unmodified response with full details
    "timestamp": 1499280391811,  // Unix timestamp (milliseconds)
    "datetime": "2017-07-05T18:47:14.692Z",  // ISO8601 datetime with milliseconds

    "free": {  // Available funds for trading, by currency
        "BTC": 321.00,  // Amount of BTC available for trading
        "USD": 123.00,  // Amount of USD available for trading
       
    },

    "used": { },  // Funds locked or on hold, by currency

    "total": { },  // Total balance (free + used), by currency

    "debt": { },  // Debt, if any, by currency

    "BTC": {  // Balance details for individual currency (e.g., BTC)
        "free": 321.00,  // Available BTC for trading
        "used": 234.00,  // BTC on hold or pending
        "total": 555.00  // Total BTC (free + used)
    },

    "USD": {  // Balance details for USD
        "free": 123.00,  // Available USD for trading
        "used": 456.00,  // USD on hold or pending
        "total": 579.00  // Total USD (free + used)
    },
}
```





### Ticker Structure
A ticker contains statistical calculations based on the market's performance over the past 24 hours.

The structure of a ticker is as follows:

```json
{
    "symbol": "BTC/USD",         // The symbol representing the market (e.g., "BTC/USDT", "ETH/BTC")
    "info": {},             // The original, unmodified, unparsed reply from the exchange API
    "timestamp": 1618393445000,  // Unix timestamp in milliseconds (since Epoch: 1 Jan 1970)
    "datetime": "2021-04-14T18:24:05.000Z",  // ISO8601 datetime string with milliseconds
    "high": 60000.00,            // Highest price during the 24-hour period
    "low": 55000.00,             // Lowest price during the 24-hour period
    "bid": 59500.00,             // Current best bid (buy) price
    "bidVolume": 1.5,            // Current best bid (buy) amount (may be missing or undefined)
    "ask": 59550.00,             // Current best ask (sell) price
    "askVolume": 1.0,            // Current best ask (sell) amount (may be missing or undefined)
    "vwap": 59000.00,            // Volume-weighted average price
    "open": 57000.00,            // Opening price at the start of the 24-hour period
    "close": 59500.00,           // Price of the last trade (closing price for the current period)
    "last": 59500.00,            // Same as `close`, included for convenience
    "previousClose": 58000.00,   // Closing price of the previous period (previous 24 hours)
    "change": 2500.00,           // Absolute change (e.g., `last - open`)
    "percentage": 4.39,          // Relative change as a percentage: `(change/open) * 100`
    "average": 58500.00,         // Average price: `(last + open) / 2`
    "baseVolume": 1000.0,        // Volume of the base currency traded in the last 24 hours
    "quoteVolume": 59000000.0   // Volume of the quote currency traded in the last 24 hours
}
```
