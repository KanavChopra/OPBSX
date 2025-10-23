import tkinter as tk
import matplotlib as mpl
from tkinter import messagebox
import numpy as np
try:
    from core.calculations import _read_float
except Exception as e:
    raise ImportError("Could not import _read_float from core/calculations.py. Ensure the core folder with calculations.py is present.") from e
try:
    from utils.black_scholes import BlackScholes
except Exception as e:
    raise ImportError("Could not import BlackScholes from utils/black_scholes.py. Ensure the utils folder with black_scholes.py is present.") from e
try:
    from core.db_setup import insert_heatmap_records
except Exception as e:
    raise ImportError("Could not import insert_heatmap_records from core/db_setup.py. Ensure the core folder with db_setup.py is present.") from e


def draw_placeholder(
        fig: mpl.figure.Figure, 
        canvas: mpl.backends.backend_tkagg.FigureCanvasTkAgg
    ) -> None:
    """
    Draw initial placeholder text in the plot area.
    Args:
        fig (matplotlib.figure.Figure): The figure object to draw on.
        canvas (matplotlib.backends.backend_tkagg.FigureCanvasTkAgg): The canvas to update.
    Returns:
        None
    """
    fig.clf()
    ax = fig.add_subplot(111)
    ax.text(0.5, 0.5, "Generate heatmap to visualize Call and Put prices\n(Spot vs Volatility)", ha="center", va="center", fontsize=12, color="gray")
    ax.set_xticks([])
    ax.set_yticks([])
    canvas.draw_idle()

def plot_heatmaps(
        db: any,
        calc_id: int,
        resolution_var: tk.StringVar,
        current_price_var: tk.StringVar,
        strike_var: tk.StringVar,
        ttm_var: tk.StringVar,
        vol_var: tk.StringVar,
        rate_var: tk.StringVar,
        spot_min_var: tk.StringVar,
        spot_max_var: tk.StringVar,
        vol_min_var: tk.StringVar,
        vol_max_var: tk.StringVar,
        fig: mpl.figure.Figure,
        canvas: mpl.backends.backend_tkagg.FigureCanvasTkAgg,
        log_message: any
    ) -> None:
    """
    Plot heatmaps for Call and Put option prices.
    """
    if calc_id is None:
        messagebox.showwarning("No Calculation ID", "Please calculate option prices first to generate heatmap.")
        return
    
    try:
        log_message("Starting heatmap generation...")
        n = int(resolution_var.get())
        if n < 2:
            raise ValueError("Resolution must be at least 2")

        # Read required pricing inputs as base
        base_spot = _read_float(current_price_var, "Current Asset Price", required=True)
        base_vol = _read_float(vol_var, "Volatility", required=True)
        strike = _read_float(strike_var, "Strike Price", required=True)
        ttm = _read_float(ttm_var, "Time to Maturity", required=True)
        rate = _read_float(rate_var, "Risk-Free Rate", required=True)

        # Heatmap ranges (allow empty -> fallback to base-based defaults)
        spot_min = _read_float(spot_min_var, "Min Spot", required=False, default=base_spot * 0.8)
        spot_max = _read_float(spot_max_var, "Max Spot", required=False, default=base_spot * 1.2)
        vol_min = _read_float(vol_min_var, "Min Volatility", required=False, default=max(0.01, base_vol * 0.5))
        vol_max = _read_float(vol_max_var, "Max Volatility", required=False, default=min(5.0, base_vol * 1.5))

        # Validations
        if spot_min <= 0 or spot_max <= 0:
            raise ValueError("Spot ranges must be > 0")
        if spot_max <= spot_min:
            raise ValueError("Max Spot must be greater than Min Spot")
        if vol_min <= 0 or vol_max <= 0:
            raise ValueError("Vol ranges must be > 0")
        if vol_max <= vol_min:
            raise ValueError("Max Vol must be greater than Min Vol")

        log_message(f"Using spot range [{spot_min:.4f}, {spot_max:.4f}] and vol range [{vol_min:.4f}, {vol_max:.4f}] with resolution {n}")

        spot_range = np.linspace(spot_min, spot_max, n)
        vol_range = np.linspace(vol_min, vol_max, n)

        call_prices = np.zeros((n, n))
        put_prices = np.zeros((n, n))

        # To store heatmap data for database insertion
        save_records = []

        # Compute matrices - rows -> vol, cols -> spot
        for i, vol in enumerate(vol_range):
            for j, spot in enumerate(spot_range):
                bs_temp = BlackScholes(
                    time_to_maturity=ttm,
                    strike=strike,
                    current_price=float(spot),
                    volatility=float(vol),
                    interest_rate=rate,
                )
                if hasattr(bs_temp, "run"):
                    bs_temp.run()
                elif hasattr(bs_temp, "calculate_prices"):
                    bs_temp.calculate_prices()
                else:
                    raise AttributeError("BlackScholes class has no 'run' or 'calculate_prices' method.")

                call_prices[i, j] = getattr(bs_temp, "call_price", np.nan)
                put_prices[i, j] = getattr(bs_temp, "put_price", np.nan)
                save_records.append((spot, vol, call_prices[i, j], put_prices[i, j])) # for DB

        # Insert heatmap data into database
        insert_heatmap_records(db, calc_id, save_records, log_message)

        # Plot into the existing figure (clear previous)
        fig.clf()
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        # --- Colormap: red (low) -> white (mid) -> green (high)
        # create a diverging-like colormap with red->white->green
        # cmap = mpl.colors.LinearSegmentedColormap.from_list("red_white_green", ["red", "white", "green"])
        cmap = mpl.colors.LinearSegmentedColormap.from_list("red_green", ["#ff4d4d", "#00b050"])

        # Plot Call Price Heatmap
        im1 = ax1.imshow(call_prices, origin="lower", aspect="auto",extent=[spot_range[0], spot_range[-1], vol_range[0], vol_range[-1]], cmap=cmap)
        ax1.set_title("Call Price")
        ax1.set_xlabel("Spot Price")
        ax1.set_ylabel("Volatility")
        # self.fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)
        fig.colorbar(im1, ax=ax1)

        # Annotate Call Price Heatmap
        # Get the number of row(n) and cols(m) in the put_prices matrix
        n_rows, n_cols = call_prices.shape

        # Get boundries for x and y axes
        left, right = spot_range[0], spot_range[-1]
        bottom, top = vol_range[0], vol_range[-1]

        # Calculate width and height of each cell
        cell_width = (right - left) / n_cols
        cell_height = (top - bottom) / n_rows

        # Loop through each cell to place the text annotation
        for i in range(n_rows):
            for j in range(n_cols):
                # Calculate the (x, y) center of ach cell [i, j]
                x_center = left + (j + 0.5) * cell_width
                y_center = bottom + (i + 0.5) * cell_height
                price = call_prices[i, j]

                # Set the text color based on the background intensity
                threshold = (np.nanmax(call_prices) + np.nanmin(call_prices)) / 2.0
                text_color = "white" if price > threshold else "black"
                ax1.text(
                    x_center, 
                    y_center, 
                    f"{call_prices[i, j]:.2f}",
                    ha="center", 
                    va="center", 
                    color=text_color,
                    fontsize=6
                )

        # Plot Put Price Heatmap
        im2 = ax2.imshow(put_prices, origin="lower", aspect="auto", extent=[spot_range[0], spot_range[-1], vol_range[0], vol_range[-1]], cmap=cmap)
        ax2.set_title("Put Price")
        ax2.set_xlabel("Spot Price")
        ax2.set_ylabel("Volatility")
        # self.fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
        fig.colorbar(im2, ax=ax2)

        # Annotate Put Price Heatmap
        # Get the number of row(n) and cols(m) in the put_prices matrix
        n_rows, n_cols = put_prices.shape

        # Get boundries for x and y axes
        left, right = spot_range[0], spot_range[-1]
        bottom, top = vol_range[0], vol_range[-1]

        # Calculate width and height of each cell
        cell_width = (right - left) / n_cols
        cell_height = (top - bottom) / n_rows

        # Loop through each cell to place the text annotation
        for i in range(n_rows):
            for j in range(n_cols):
                # Calculate the (x, y) center of ach cell [i, j]
                x_center = left + (j + 0.5) * cell_width
                y_center = bottom + (i + 0.5) * cell_height
                price = put_prices[i, j]

                # Set the text color based on the background intensity
                threshold = (np.nanmax(put_prices) + np.nanmin(put_prices)) / 2.0
                text_color = "white" if price > threshold else "black"
                ax2.text(
                    x_center, 
                    y_center, 
                    f"{put_prices[i, j]:.2f}",
                    ha="center", 
                    va="center", 
                    color=text_color,
                    fontsize=6
                )

        fig.tight_layout()
        canvas.draw_idle()

        log_message("Heatmap generation completed.")
        messagebox.showinfo("Heatmaps Generated", "Heatmaps generated and saved to database successfully.")
    except Exception as e:
        messagebox.showerror("Heatmap error", str(e))
        log_message(f"Error while generating heatmap: {e}")