from qtradex.private.wallet import PaperWallet
from qtradex.core.backtest import perform_trade, Buy, Sell

def roi_quote_currency(balances, prices, pair):
    initial_val = balances[0][pair[1]] + balances[0][pair[0]] * prices[0]
    final_val = balances[-1][pair[1]] + balances[-1][pair[0]] * prices[-1]
    return (final_val / initial_val) if initial_val > 0 else 1.0

def test_linear_vs_compound():
    print("=== TESTE: COMPUROS VS LINEAR ===")
    
    # 1. Configurar carteira inicial
    capital = 10000
    wallet = PaperWallet({"BTC": 0, "USDT": capital}, fee=0.0) # Sem taxa para facilitar conta
    wallet.initial_capital = capital
    
    # Simular dois trades de 10% de lucro cada
    
    # TRADE 1: Preço sobe de 100 para 110 (+10%)
    price1_start = 100
    price1_end = 110
    
    print(f"\nTrade 1: Preço {price1_start} -> {price1_end} (+10%)")
    
    # Compra (Usa o capital inicial fixo de 10000)
    buy1 = Buy()
    wallet, op1 = perform_trade(buy1, wallet, "BTC", "USDT", price1_start)
    print(f"Depois da Compra 1 : {dict(wallet.items())}")
    
    # Venda
    sell1 = Sell()
    wallet, op1_s = perform_trade(sell1, wallet, "BTC", "USDT", price1_end)
    print(f"Depois da Venda 1  : {dict(wallet.items())} (Lucro: {wallet['USDT'] - capital})")
    
    # TRADE 2: Preço sobe de 110 para 121 (+10%)
    price2_start = 110
    price2_end = 121
    
    print(f"\nTrade 2: Preço {price2_start} -> {price2_end} (+10%)")
    
    # Compra (Deve usar apenas 10000, mesmo tendo 11000)
    buy2 = Buy()
    wallet, op2 = perform_trade(buy2, wallet, "BTC", "USDT", price2_start)
    print(f"Depois da Compra 2 : {dict(wallet.items())} <-- Deve ter sobrado 1000 USDT 'em caixa'")
    
    # Venda
    sell2 = Sell()
    wallet, op2_s = perform_trade(sell2, wallet, "BTC", "USDT", price2_end)
    print(f"Depois da Venda 2  : {dict(wallet.items())} (Lucro Total: {wallet['USDT'] - capital})")
    
    # RESULTADO ESPERADO:
    # Trade 1: 10% de 10000 = 1000 lucro. Novo Saldo = 11000.
    # Trade 2: 10% de 10000 = 1000 lucro. Novo Saldo = 12000.
    # ROI Total esperado = 20% (12000 / 10000)
    # Se fosse composto: 1.10 * 1.10 = 1.21 (21%)
    
    final_roi = roi_quote_currency([{"BTC": 0, "USDT": capital}, dict(wallet.items())], [100, 121], ("BTC", "USDT"))
    print(f"\nROI Final Calculado: {(final_roi - 1.0) * 100:.2f}%")
    
    if round(final_roi, 2) == 1.20:
        print("\n✅ SUCESSO: O sistema está usando JUROS SIMPLES (Capital Fixo)!")
    else:
        print(f"\n❌ ERRO: O sistema parece estar compondo. ROI: {final_roi}")

if __name__ == "__main__":
    test_linear_vs_compound()
