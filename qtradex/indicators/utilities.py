"""
PURE PYTHON REPLACEMENT FOR utilities.pyx (Cython)
--------------------------------------------------
This file replaces the original `utilities.pyx` Cython module.
Reason: To eliminate the dependency on Microsoft Visual C++ Build Tools during installation on Windows.
Functionality: Implements the same logic (float_period, derivative, lag) in pure Python.
"""
import math
import numpy as np

def float_period(func, args, indices):
    """
    Executes func(args) handling floating point periods specified by indices.
    """
    current_sets = [list(args)]
    current_weights = [1.0]
    
    # Check if indices is a tuple of tuples? Or just tuple of ints?
    # In cache_decorator.py: periods is *periods from @float_period(*periods).
    # So periods is a tuple of ints, e.g. (1,).
    # Passed to here as indices.
    
    # Handle indices structure compatibility
    valid_indices = []
    if indices:
         # indices might be a tuple of ints
         for i in indices:
             if isinstance(i, int):
                 valid_indices.append(i)
             elif isinstance(i, (list, tuple)):
                 # recursive? Or just flattening?
                 valid_indices.extend(i)
    
    did_split = False
    
    # We iterate over indices (which are indices into args)
    for idx in valid_indices:
        if idx >= len(args): continue
        val = args[idx]
        
        # Check for floatiness
        if isinstance(val, (float, np.floating)) and not float(val).is_integer():
            did_split = True
            fl = math.floor(val)
            cl = math.ceil(val)
            frac = val - fl
            
            new_sets = []
            new_weights = []
            
            for s, w in zip(current_sets, current_weights):
                # Floor case
                s_fl = list(s)
                s_fl[idx] = int(fl) # Cast to int for the function call
                new_sets.append(s_fl)
                new_weights.append(w * (1.0 - frac))
                
                # Ceil case
                s_cl = list(s)
                s_cl[idx] = int(cl)
                new_sets.append(s_cl)
                new_weights.append(w * frac)
            
            current_sets = new_sets
            current_weights = new_weights
        else:
            # Cast to int if it's an integer-float (e.g. 14.0 -> 14) 
            # because some libs might complain about float
            # But we only modify the sets we use.
            # Update all current sets
             for s in current_sets:
                # We should cast to int if it is effectively an int, 
                # because tulipy/pandas-ta often prefer ints.
                # But don't break if it's supposed to be float (like stddev?)
                # Usually "period" implies int.
                try:
                    if isinstance(val, (int, float, np.number)):
                         s[idx] = int(val)
                except:
                    pass

    # Execute
    if not did_split:
        # Just run once with args (casted to int where referenced? No, just run)
        # But wait, original wrapper casted to int in tulipy_wrapped.py?
        # In my rewrite of tulipy_wrapped.py: `length=int(period)`.
        # So passing float is fine, it handles it.
        # So just call it.
        return func(*args)

    # If split, we have multiple calls
    results = []
    for s in current_sets:
        results.append(func(*s))
    
    # Combine results
    # Assume results are numpy arrays or tuples of arrays
    res0 = results[0]
    scale = current_weights[0]
    
    if isinstance(res0, tuple):
         # Tuple of arrays
         accumulators = [np.nan_to_num(r) * scale for r in res0]
         
         for i in range(1, len(results)):
             res = results[i]
             w = current_weights[i]
             for j, r in enumerate(res):
                 accumulators[j] += np.nan_to_num(r) * w
         return tuple(accumulators)
    
    elif isinstance(res0, (np.ndarray, list)):
        final_res = np.nan_to_num(res0) * scale
        for i in range(1, len(results)):
             res = results[i]
             w = current_weights[i]
             final_res += np.nan_to_num(res) * w
        return final_res
    else:
        # Scalar or other? 
        final_res = res0 * scale
        for i in range(1, len(results)):
             final_res += results[i] * current_weights[i]
        return final_res

def derivative(ma_array, period=1):
    if period == 1:
        return np.diff(ma_array, prepend=ma_array[0])
    
    n = len(ma_array)
    out = np.empty_like(ma_array)
    out[:period] = 0 
    out[period:] = ma_array[period:] - ma_array[:-period]
    return out

def lag(array, amount):
    if amount == 0:
        return array
    return np.roll(array, int(amount)) 

def truncate(data, depth):
    # Stub if needed
    pass
