import tkinter as tk
from tkinter import messagebox, ttk
import numpy as np
import matplotlib as mpl
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def _on_history_load(
        db: any, 
        tree: ttk.Treeview, 
        win: tk.Toplevel, 
        fig: mpl.figure.Figure, 
        canvas: FigureCanvasTkAgg, 
        log_message: callable
    ) -> None:
    """
    Load the selected history item from the database and re-plot the heatmap.
    Args:
        db: Database connection object with an 'execute' method.
        tree: Tkinter Treeview widget containing history records.
        win: The history window to be closed after loading.
        fig: Matplotlib Figure object for plotting.
        canvas: Matplotlib FigureCanvasTkAgg object for rendering.
        log_message: Callable to log messages to the application log.
    Raises:
        Exception: If there is an error during loading or plotting.
    Returns:
        None
    """
    try:
        sel = tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select a row to load.")
            return
        item = tree.item(sel[0])
        calc_id = item["values"][0]

        # Fetch heatmap rows
        query = """
            SELECT 
                spot, 
                volatility, 
                call_price, 
                put_price 
            FROM 
                heatmap_data
            WHERE calc_id = %s 
            ORDER BY heatmap_id ASC
        """
        rows = db.execute(query, (calc_id,), fetch=True)
        if not rows:
            messagebox.showinfo("No data", f"No heatmap rows found for calc_id={calc_id}")
            return
        
        spots = sorted(set([float(r[0]) for r in rows]))
        vols = sorted(set([float(r[1]) for r in rows]))
        n_spot = len(spots)
        n_vol = len(vols)

        call_prices = np.full((n_vol, n_spot), np.nan)
        put_prices = np.full((n_vol, n_spot), np.nan)

        spot_to_idx = {s: j for j, s in enumerate(spots)}
        vol_to_idx = {v: i for i, v in enumerate(vols)}

        for r in rows:
            s, v, c, p = float(r[0]), float(r[1]), float(r[2]), float(r[3])
            i = vol_to_idx[v]
            j = spot_to_idx[s]
            call_prices[i, j] = c
            put_prices[i, j] = p

        fig.clf()
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        # cmap = mpl.colors.LinearSegmentedColormap.from_list("red_green", ["red", "green"])
        cmap = mpl.colors.LinearSegmentedColormap.from_list("red_green", ["#ff4d4d", "#00b050"])

        # Call plot
        im1 = ax1.imshow(call_prices, origin="lower", aspect="auto",
                         extent=[spots[0], spots[-1], vols[0], vols[-1]], cmap=cmap)
        ax1.set_title(f"Call Price (calc_id={calc_id})")
        ax1.set_xlabel("Spot")
        ax1.set_ylabel("Volatility")
        fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)

        # Annotate max call price
        # Get the number of row(n) and cols(m) in the put_prices matrix
        n_rows, n_cols = call_prices.shape

        # Get boundries for x and y axes
        left, right = spots[0], spots[-1]
        bottom, top = vols[0], vols[-1]

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
        im2 = ax2.imshow(put_prices, origin="lower", aspect="auto", extent=[spots[0], spots[-1], vols[0], vols[-1]], cmap=cmap)
        ax2.set_title(f"Put Price (calc_id={calc_id})")
        ax2.set_xlabel("Spot Price")
        ax2.set_ylabel("Volatility")
        # self.fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
        fig.colorbar(im2, ax=ax2)

        # Annotate Put Price Heatmap
        # Get the number of row(n) and cols(m) in the put_prices matrix
        n_rows, n_cols = put_prices.shape

        # Get boundries for x and y axes
        left, right = spots[0], spots[-1]
        bottom, top = vols[0], vols[-1]

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

        log_message(f"Loaded calc_id={calc_id} from DB and re-plotted with enhanced visuals.")
        messagebox.showinfo("Heatmap Loaded", f"Heatmap for calc_id={calc_id} loaded successfully.")
        win.destroy()

    except Exception as e:
        messagebox.showerror("Load error", str(e))
        log_message(f"Error loading history item: {e}")


def open_history_window(
        db: any, 
        root: tk.Tk, 
        fig: mpl.figure.Figure, 
        canvas: FigureCanvasTkAgg, 
        log_message: callable
    ) -> None:
    """
    Open a window displaying calculation history from the database.
    Allows selection of a record to load its parameters and re-plot the heatmap.
    Args:
        db: Database connection object with an 'execute' method.
        root: The main Tkinter application window.
        fig: Matplotlib Figure object for plotting.
        canvas: Matplotlib FigureCanvasTkAgg object for rendering.
        log_message: Callable to log messages to the application log.
    Raises:
        Exception: If there is an error fetching data from the database.
    Returns:
        None
    """
    try:
        hist_win = tk.Toplevel(root)
        hist_win.title("Calculation History")
        hist_win.geometry("900x500")
        hist_win.transient(root)

        frame = ttk.Frame(hist_win, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        # Treeview
        cols = ("calc_id", "created_at", "current_price", "strike_price", "time_to_maturity", "volatility", "risk_free_interest_rate")
        tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=100, anchor="center")
        tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        # Fetch history
        query = """
            SELECT 
                calc_id, 
                DATE_FORMAT(timestamp, '%Y-%m-%d') AS created_at, 
                current_price, 
                strike_price, 
                time_to_maturity, 
                volatility, 
                risk_free_interest_rate 
            FROM option_pricing 
            ORDER BY timestamp
        """
        rows = db.execute(query, fetch=True)
        for r in rows:
            tree.insert("", tk.END, values=r)

        # Buttons
        btn_frame = ttk.Frame(hist_win, padding=6)
        btn_frame.pack(fill=tk.X)
        load_btn = ttk.Button(btn_frame, text="Load Selected & Plot Heatmap", command=lambda: _on_history_load(db, tree, hist_win, fig, canvas, log_message))
        load_btn.pack(side=tk.LEFT, padx=6)
        close_btn = ttk.Button(btn_frame, text="Close", command=hist_win.destroy)
        close_btn.pack(side=tk.RIGHT, padx=6)

    except Exception as e:
        messagebox.showerror("History error", str(e))
        log_message(f"Error opening history window: {e}")
