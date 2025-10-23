import tkinter as tk
from tkinter import messagebox
try:
    from utils.black_scholes import BlackScholes
except Exception as e:
    raise ImportError("Could not import BlackScholes from utils/black_scholes.py. Ensure the utils folder with black_scholes.py is present.") from e
try:
    from core.db_setup import insert_input_record
except Exception as e:
    raise ImportError("Could not import insert_input_record from core/db_setup.py. Ensure the core folder with db_setup.py is present.") from e


def _read_float(
        var: tk.StringVar, 
        name: str, 
        required: bool = False, 
        default=None
    ) -> float:
    """
    Read and convert a Tkinter StringVar to float, with error handling.
    Args:
        var (tk.StringVar): The StringVar to read from.
        name (str): The name of the variable (for error messages).
        required (bool): Whether the variable is required. Defaults to False.
        default: The default value to return if not required and empty. Defaults to None.
    Returns:
        float: The converted float value.
    Raises:
        ValueError: If the value is required but missing, or if conversion fails.
    """
    s = var.get().strip()
    if s == "":
        if required:
            raise ValueError(f"'{name}' is required.")
        return default
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"Invalid number for '{name}': {s!r}")
    
def calculate_option_prices(
        db: any, 
        current_price_var: tk.StringVar, 
        strike_var: tk.StringVar, 
        ttm_var: tk.StringVar, 
        vol_var: tk.StringVar, 
        rate_var: tk.StringVar, 
        last_calc_id: int, 
        call_val_label: tk.Label, 
        put_val_label: tk.Label, 
        delta_call_label: tk.Label, 
        delta_put_label: tk.Label, 
        gamma_label: tk.Label, 
        log_message: any
    ) -> int:
    """
    Calculate the Black-Scholes price for a European Call or Put option.
    Args:
        spot (float): Current price of the underlying asset.
        strike (float): Strike price of the option.
        volatility (float): Volatility of the underlying asset (as a decimal).
        rate (float): Risk-free interest rate (as a decimal).
        time (float): Time to expiration in years.
        option_type (str): 'call' for Call option, 'put' for Put option.
    Returns:
        int: The calculation ID from the database insertion.
    Raises:
        ValueError: If an invalid option type is provided.
    """
    try:
        log_message("Calculating prices...")
        current_price = _read_float(current_price_var, "Current Asset Price", required=True)
        strike = _read_float(strike_var, "Strike Price", required=True)
        ttm = _read_float(ttm_var, "Time to Maturity", required=True)
        vol = _read_float(vol_var, "Volatility", required=True)
        rate = _read_float(rate_var, "Risk-Free Rate", required=True)

        if ttm <= 0:
            raise ValueError("Time to maturity must be > 0")
        if vol <= 0:
            raise ValueError("Volatility must be > 0")

        # Insert input record into database
        calc_id = insert_input_record(
            db=db,
            current_price=current_price,
            strike_price=strike,
            time_to_maturity=ttm,
            volatility=vol,
            risk_free_interest_rate=rate,
            log_message=log_message
        )

        last_calc_id = calc_id

        # Black-Scholes calculation
        bs = BlackScholes(
            time_to_maturity=ttm,
            strike=strike,
            current_price=current_price,
            volatility=vol,
            interest_rate=rate,
        )

        # Support both run() and calculate_prices()
        if hasattr(bs, "run"):
            bs.run()
        elif hasattr(bs, "calculate_prices"):
            bs.calculate_prices()
        else:
            raise AttributeError("BlackScholes class has no 'run' or 'calculate_prices' method.")

        call_price = getattr(bs, "call_price", None)
        put_price = getattr(bs, "put_price", None)
        call_delta = getattr(bs, "call_delta", None)
        put_delta = getattr(bs, "put_delta", None)
        gamma = getattr(bs, "call_gamma", None) or getattr(bs, "gamma", None)

        # Update UI
        call_val_label.config(text=f"${call_price:.6f}" if call_price is not None else "—")
        put_val_label.config(text=f"${put_price:.6f}" if put_price is not None else "—")
        delta_call_label.config(text=f"Δ (Call): {call_delta:.6f}" if call_delta is not None else "Δ (Call): —")
        delta_put_label.config(text=f"Δ (Put): {put_delta:.6f}" if put_delta is not None else "Δ (Put): —")
        gamma_label.config(text=f"Γ: {gamma:.6f}" if gamma is not None else "Γ: —")

        log_message("Price calculation completed.")
        messagebox.showinfo("Price Calculation Complete", "Option prices and Greeks calculated successfully.")
        return last_calc_id
    except Exception as e:
        messagebox.showerror("Calculation error", str(e))
        log_message(f"Error while calculating prices: {e}")