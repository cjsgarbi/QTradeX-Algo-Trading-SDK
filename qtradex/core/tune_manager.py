import ast
import hashlib
import inspect
import json
import os
import time
from datetime import datetime

from qtradex.common.utilities import (NdarrayDecoder, NdarrayEncoder, it,
                                      read_file, write_file)
from qtradex.core.ui_utilities import get_number, logo


def get_path(bot):
    """
    Get the directory path for storing tunes related to the bot.

    Parameters:
    - bot: The bot instance.

    Returns:
    - The path to the tunes directory.
    """
    cache_dir = os.path.dirname(inspect.getfile(type(bot)))
    cache_dir = os.path.join(cache_dir, "tunes")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def generate_filename(bot, asset=None, currency=None, timeframe=None):
    """
    Generate a unique filename for the bot's tune based on its code and name.

    Parameters:
    - bot: The bot instance.

    Returns:
    - A tuple containing the generated filename and the source code of the bot.
    """
    file = inspect.getfile(type(bot))
    source = read_file(file)
    hashed = ast_to_hash(bot)  # Hash the bot's tune for uniqueness
    module_name = os.path.split(os.path.splitext(file)[0])[1]
    filename = os.path.join(get_path(bot), f"{module_name}_{hashed}.json")
    return filename, source


def save_tune(bot, identifier=None):
    """
    Save the current tune of the bot to a JSON file.
    
    Formato simplificado:
    {
        "asset"    : "BTC",
        "currency" : "USDT", 
        "timeframe": 900,
        "tune"     : {...},
        "results"  : {...}
    }

    Parameters:
    - bot: The bot instance.
    - identifier: Optional identifier for the tune (não usado no novo formato).
    """
    filename, source = generate_filename(bot)

    # Extrai asset/currency do bot (passado pelo otimizador)
    asset = getattr(bot, '_tune_asset', None) or getattr(bot, 'asset', 'UNKNOWN')
    currency = getattr(bot, '_tune_currency', None) or getattr(bot, 'currency', 'UNKNOWN')
    timeframe = getattr(bot, 'timeframe', 900)
    
    # Adiciona timestamp ao identifier
    if identifier:
        identifier = f"{identifier}_{time.ctime()}"
    else:
        identifier = f"BEST TUNE_{time.ctime()}"
    
    # Separa tune e results se estiverem juntos
    if isinstance(bot.tune, dict) and 'tune' in bot.tune and 'results' in bot.tune:
        tune_data = bot.tune['tune']
        results_data = bot.tune['results']
    else:
        tune_data = bot.tune
        results_data = {}
    
    # Tenta ler conteúdo existente
    try:
        existing_contents = json.loads(read_file(filename), cls=NdarrayDecoder)
    except FileNotFoundError:
        existing_contents = {"source": source}

    # Gera identificador único com contexto
    identifier_base = identifier or "BEST TUNE"
    identifier_full = f"{identifier_base}_{asset}_{currency}_{timeframe}_{time.ctime()}"
    
    # Formato limpo e simples do novo registro
    # Pega informações de período do bot (passadas pelo otimizador)
    begin_ts = getattr(bot, '_tune_begin', None)
    end_ts = getattr(bot, '_tune_end', None)
    
    # Calcula datas formatadas e duração
    begin_date = None
    end_date = None
    duration = None
    
    if begin_ts and end_ts:
        begin_date = time.strftime("%d/%m/%Y", time.localtime(begin_ts))
        end_date = time.strftime("%d/%m/%Y", time.localtime(end_ts))
        total_days = (end_ts - begin_ts) / 86400
        months = int(total_days // 30)
        days_rem = int(total_days % 30)
        if months > 0:
            duration = f"{months} Meses e {days_rem} Dias"
            if months == 1: duration = duration.replace("Meses", "Mês")
            if days_rem == 1: duration = duration.replace("Dias", "Dia")
        else:
            duration = f"{days_rem} Dias" if days_rem != 1 else "1 Dia"
    
    new_record = {
        "identifier": identifier_full,
        "begin_date": begin_date,
        "end_date"  : end_date,
        "duration"  : duration,
        "asset"     : asset,
        "currency"  : currency,
        "timeframe" : timeframe,
        "tune"      : tune_data,
        "results"   : results_data
    }
    
    # Adiciona ao conteúdo existente usando identifier único como chave
    existing_contents[identifier_full] = new_record
    
    write_file(filename, existing_contents)


def from_iso_date(iso):
    """
    Convert an ISO date string to a UNIX timestamp.

    Parameters:
    - iso: The ISO date string.

    Returns:
    - The corresponding UNIX timestamp.
    """
    return datetime.strptime(iso, "%a %b %d %H:%M:%S %Y").timestamp()


def load_tune(bot, key=None, sort="roi"):
    """
    Load a specific tune for the bot from the saved tunes.

    Parameters:
    - bot: The bot instance or its identifier.
    - key: Optional key to specify which tune to load.
    - sort: The sorting criteria for selecting the tune.

    Returns:
    - The loaded tune.
    """
    if isinstance(bot, str):
        path = get_path(bot)
        listdir = os.listdir(path)
        if bot not in listdir:
            raise KeyError("Unknown bot id. Try using `get_bots()` to find stored ids.")
        filename = os.path.join(path, bot)
    else:
        filename = generate_filename(bot)[0]

    try:
        contents = json.loads(read_file(filename), cls=NdarrayDecoder)
    except FileNotFoundError:
        raise FileNotFoundError("The given bot has no saved tunes.")

    # NOVO FORMATO FLAT: {identifier, asset, currency, timeframe, tune, results}
    # Verifica se o conteúdo é um único registro (formato antigo que criamos brevemente) ou dicionário de registros
    if "tune" in contents and "results" in contents:
         # Arquivo com um único registro (retrocompatibilidade temporária)
        return contents["tune"]
    
    # FORMATO CENTRALIZADO: {key1: {tune, results, asset, ...}, key2: {...}, ...}
    # Filtra apenas os tunes que correspondem ao asset/currency/timeframe do bot atual (se disponíveis)
    
    # helper para checar compatibilidade
    def is_compatible(record, bot):
        # Se o registro tem metadados extendidos, verifica compatibilidade
        if isinstance(record, dict) and "asset" in record:
             # Pega dados do bot
            bot_asset = getattr(bot, 'asset', None)
            bot_curr = getattr(bot, 'currency', None)
            bot_tf = getattr(bot, 'timeframe', None)
            
            # Se bot não tem dados definidos, aceita tudo (fallback)
            if not bot_asset or not bot_curr:
                return True
                
            # Verifica match exato
            return (record.get("asset") == bot_asset and 
                    record.get("currency") == bot_curr and 
                    str(record.get("timeframe")) == str(bot_tf))
        return True # Registros antigos sem metadados são considerados compatíveis

    # Filtra candidatos
    candidates = {k: v for k, v in contents.items() if k != "source" and is_compatible(v, bot)}
    
    if not candidates:
        # Se não achou nenhum compatível, avisa e usa o padrão
        print(it("yellow", f"\n  [!] Tuner não encontrado para {getattr(bot, 'asset', '?')}/{getattr(bot, 'currency', '?')} {getattr(bot, 'timeframe', '?')}s"))
        print(it("yellow", "  [!] Por favor, faça a otimização. Usando valores padrão do bot por enquanto...\n"))
        time.sleep(2)
        return bot.tune if hasattr(bot, 'tune') else {}

    # Determine the key to load based on sorting criteria
    if key is None:
        if sort == "roi":
            key = max(
                candidates.items(),
                key=lambda x: x[1]["results"]["roi"] if isinstance(x[1], dict) and "results" in x[1] else 0,
            )[0]
        else:
            # Para outros sorts, mantemos lógica similar
             key = max(
                candidates.items(),
                key=lambda x: from_iso_date(x[0].rsplit("_", 1)[1]) if "_" in x[0] else 0,
            )[0]

    if key not in contents:
         # Logica de busca por sulfixo (mantida, mas agora buscando em candidates se possível ou contents geral)
        # Simplificação: se a chave exata não tá, tenta achar
         raise KeyError(f"Tune key {key} not found.")

    return contents[key]["tune"]  # Return the loaded tune


def get_bots(bot):
    """
    Get a sorted list of bot identifiers.

    Parameters:
    - bot: The bot instance or its identifier.

    Returns:
    - A sorted list of bot identifiers.
    """
    return sorted(os.listdir(bot if isinstance(bot, str) else get_path(bot)))


def get_tunes(bot):
    """
    Retrieve all tunes associated with a specific bot.

    Parameters:
    - bot: The bot instance or its identifier.

    Returns:
    - A list of tunes associated with the bot.
    """
    if isinstance(bot, str):
        path = get_path(bot)
        listdir = os.listdir(path)
        if bot not in listdir:
            raise KeyError("Unknown bot id. Try using `get_bots()` to find stored ids.")
        filename = os.path.join(path, bot)
    else:
        filename = generate_filename(bot)[0]

    try:
        contents = json.loads(read_file(filename))
    except FileNotFoundError:
        return []  # Return an empty list if no tunes are found

    return contents  # Return the contents of the tunes


def ast_to_hash(instance):
    """
    Generate a hash based on the bot's tune.

    Parameters:
    - instance: The bot instance.

    Returns:
    - A hash value representing the tune.
    """
    return len(instance.__class__().tune)  # Use the length of the tune as a simple hash


def choose_tune(bot, kind="any"):
    """
    Allow the user to choose a tune from the available options.

    Parameters:
    - bot: The bot instance or the path to a tune file.
    - kind: The type of choice to return (either "tune" or "any").

    Returns:
    - The chosen tune or choice based on the specified kind.
    """
    # Allow bot to be both a filepath to a bot tune file or the bot itself
    if not isinstance(bot, str):
        bot = generate_filename(bot)[0]

    try:
        contents = json.loads(read_file(bot), cls=NdarrayDecoder)
    except FileNotFoundError:
        raise FileNotFoundError("This bot has no saved tunes!")

    if kind == "tune":
        contents.pop("source")  # Remove source if only tunes are needed

    # Create a dispatch dictionary for user selection
    best_key = max(
        {k: v for k, v in contents.items() if k != "source"}.items(),
        key=lambda x: x[1]["results"]["roi"],
    )[0]
    dispatch = {
        0: (best_key, contents[best_key]),
    }
    dispatch.update(enumerate(list(contents.items()), start=1))

    logo()  # Display logo
    for num, (k, v) in dispatch.items():
        if k == "source":
            print(f"  {num}: {k}")
        else:
            print(
                f"  {num}: {v['results']['roi']:.2f} ROI - {k}"
            )  # Print available options

    option = dispatch[get_number(dispatch)][0]  # Get user choice
    choice = contents[option]  # Retrieve the chosen tune

    return choice["tune"] if kind == "tune" else choice  # Return the appropriate choice


def main():
    """
    Main function to run the tune management interface.
    """
    logo(animate=True)
    path = os.path.join(os.getcwd(), "tunes")

    # Sort saved tunes by modified time
    algorithms = sorted(
        [os.path.join(path, i) for i in os.listdir(path)],
        key=os.path.getmtime,
        reverse=True,
    )

    if not algorithms:
        print("No saved tunes found!")
        return

    while True:
        logo()  # Display logo
        dispatch = dict(enumerate(algorithms + ["Exit"], start=1))
        print(it("yellow", "Bot save states, most recent first:"))
        for k, v in dispatch.items():
            print(
                f"  {k}: {os.path.splitext(os.path.split(v)[1])[0]}"
            )  # Display saved tunes

        choice = get_number(dispatch)  # Get user choice

        if dispatch[choice] == "Exit":
            return  # Exit the loop if the user chooses to exit

        tune = choose_tune(dispatch[choice])  # Choose a tune based on user selection

        logo()  # Display logo again
        if isinstance(tune, str):
            print(tune)  # Print the tune if it's a string
        else:
            print(json.dumps(tune, indent=4))  # Print the tune in JSON format

        input("\n\nPress Enter to continue.")  # Wait for user input before continuing


if __name__ == "__main__":
    main()  # Run the main function when the script is executed
