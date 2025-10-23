import sys
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mysql.connector import Error
try:
    from utils.db import DBHandler
except Exception as e:
    raise ImportError(
        "Could not import DBHandler from utils/db.py. Ensure the utils folder with db.py is present.") from e
try:
    from core.db_setup import create_table_if_not_exists
except Exception as e:
    raise ImportError("Could not import create_table_if_not_exists from core/db_setup.py. Ensure the core folder with db_setup.py is present.") from e
try:
    from core.calculations import calculate_option_prices
except Exception as e:
    raise ImportError("Could not import calculate_option_prices from core/calculations.py. Ensure the core folder with calculations.py is present.") from e
try:
    from core.plotting import draw_placeholder, plot_heatmaps
except Exception as e:
    raise ImportError("Could not import plot_heatmaps from core/plotting.py. Ensure the core folder with plotting.py is present.") from e
try:
    from core.history import open_history_window
except Exception as e:
    raise ImportError("Could not import open_history_window from core/history.py. Ensure the core folder with history.py is present.") from e
try:
    from config.settings import DB_CONFIG
except Exception as e:
    raise ImportError("Could not import DB_CONFIG from config/settings.py. Ensure the config folder with settings.py is present.") from e


# Main Application Class
class BSApp:
    """
    Graphical Tkinter application for interactive Black–Scholes option pricing and visualization.

    This dashboard enables users to:
    - Input pricing parameters (Spot, Strike, Time-to-Maturity, Volatility, Risk-Free Rate)
    - Compute call/put prices and Greeks (Delta, Gamma)
    - Generate 2D heatmaps of option prices over ranges of Spot and Volatility
    - Log activities and errors
    - Store inputs and results in a MySQL database
    Attributes:
        root (tk.Tk): The main Tkinter window.
        style (ttk.Style): The styling object for the application.
        db (DBHandler): Database handler for MySQL interactions.
        last_calc_id (int): ID of the last calculation performed, used for heatmap generation.
    Methods:
        setup_ui(): Sets up the main UI components and layout.
        calculate_prices(): Calculate Call and Put option prices along with Greeks.
        generate_heatmap(): Generate and plot heatmaps for Call and Put option prices.
        log_message(message): Log a message with timestamp to the status text area.
    Returns:
        None
    """
    def __init__(self, root):
        # Main window setup
        self.root = root
        self.root.title("Black-Scholes Interactive Dashboard")
        self.root.geometry("1150x1000")
        self.root.minsize(1150, 1000)
        self.last_calc_id = None

        # Style
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Setup UI
        self.setup_ui()
        self.log_message("Application initialized successfully.")

        # Database connection
        try:
            self.db = DBHandler(DB_CONFIG)
            self.log_message("Database connected successfully.")
        except Error as e:
            messagebox.showerror("Database Connection Error", f"Could not connect to database: {e}")
            sys.exit(1)

        # Ensure necessary tables exist
        try:
            create_table_if_not_exists(self.db, self.log_message)
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not create necessary tables: {e}")
            sys.exit(1)

    def setup_ui(self):
        """
        Setup the main UI components and layout.
        Returns:
            None
        """
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)

        # -------------------------
        # Pricing parameters frame (single horizontal row)
        # -------------------------
        pricing_frame = ttk.LabelFrame(main_frame, text="PRICING PARAMETERS", padding="6")
        pricing_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        lbl_font = ("Segoe UI", 9)

        ttk.Label(pricing_frame, text="Current Asset Price:", font=lbl_font).grid(row=0, column=0, sticky="w", padx=(0, 2))
        self.current_price_var = tk.StringVar(value="")
        ttk.Entry(pricing_frame, textvariable=self.current_price_var, width=12).grid(row=0, column=1, padx=(0, 6))

        ttk.Label(pricing_frame, text="Strike Price:", font=lbl_font).grid(row=0, column=2, sticky="w", padx=(0, 2))
        self.strike_var = tk.StringVar(value="")
        ttk.Entry(pricing_frame, textvariable=self.strike_var, width=12).grid(row=0, column=3, padx=(0, 6))

        ttk.Label(pricing_frame, text="Time to Maturity (yrs):", font=lbl_font).grid(row=0, column=4, sticky="w", padx=(0, 2))
        self.ttm_var = tk.StringVar(value="")
        ttk.Entry(pricing_frame, textvariable=self.ttm_var, width=12).grid(row=0, column=5, padx=(0, 6))

        ttk.Label(pricing_frame, text="Volatility (σ):", font=lbl_font).grid(row=0, column=6, sticky="w", padx=(0, 2))
        self.vol_var = tk.StringVar(value="")
        ttk.Entry(pricing_frame, textvariable=self.vol_var, width=12).grid(row=0, column=7, padx=(0, 6))

        ttk.Label(pricing_frame, text="Risk-Free Rate:", font=lbl_font).grid(row=0, column=8, sticky="w", padx=(0, 2))
        self.rate_var = tk.StringVar(value="")
        ttk.Entry(pricing_frame, textvariable=self.rate_var, width=12).grid(row=0, column=9, padx=(0, 6))

        self.calc_btn = ttk.Button(pricing_frame, text="Calculate Prices", width=15, padding=(5,2), command=self.calculate_prices)
        self.calc_btn.grid(row=0, column=10, padx=(12, 4))
        self.view_history_btn = ttk.Button(pricing_frame, text="View History", width=15, padding=(5,2), command=self.view_history)
        self.view_history_btn.grid(row=0, column=11, padx=(12, 4))

        # -------------------------
        # Heatmap parameters frame (single horizontal row)
        # -------------------------
        heat_frame = ttk.LabelFrame(main_frame, text="HEATMAP PARAMETERS (Spot vs Volatility)", padding="6")
        heat_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(heat_frame, text="Min Spot:", font=lbl_font).grid(row=0, column=0, sticky="w", padx=(0, 2))
        self.spot_min_var = tk.StringVar(value="")
        ttk.Entry(heat_frame, textvariable=self.spot_min_var,width=12).grid(row=0, column=1, padx=(0, 6))

        ttk.Label(heat_frame, text="Max Spot:", font=lbl_font).grid(row=0, column=2, sticky="w", padx=(0, 2))
        self.spot_max_var = tk.StringVar(value="")
        ttk.Entry(heat_frame, textvariable=self.spot_max_var, width=12).grid(row=0, column=3, padx=(0, 6))

        ttk.Label(heat_frame, text="Min Vol:", font=lbl_font).grid(row=0, column=4, sticky="w", padx=(0, 2))
        self.vol_min_var = tk.StringVar(value="")
        ttk.Entry(heat_frame, textvariable=self.vol_min_var, width=12).grid(row=0, column=5, padx=(0, 6))

        ttk.Label(heat_frame, text="Max Vol:", font=lbl_font).grid(row=0, column=6, sticky="w", padx=(0, 2))
        self.vol_max_var = tk.StringVar(value="")
        ttk.Entry(heat_frame, textvariable=self.vol_max_var, width=12).grid(row=0, column=7, padx=(0, 6))

        ttk.Label(heat_frame, text="Resolution (n):", font=lbl_font).grid(row=0, column=8, sticky="w", padx=(0, 2))
        self.resolution_var = tk.IntVar(value=12)
        ttk.Spinbox(heat_frame, from_=6, to=80, textvariable=self.resolution_var, width=12).grid(row=0, column=9, padx=(0, 6))

        self.heat_btn = ttk.Button(heat_frame, text="Generate Heatmap", width=20, padding=(5,2), command=self.generate_heatmap)
        self.heat_btn.grid(row=0, column=10, padx=(12, 4), sticky="w")
        # ttk.Label(heat_frame, text="(Leave min/max empty to use defaults from pricing inputs)",foreground="gray").grid(row=2, column=0, columnspan=6, sticky="w", pady=(6, 0))

        # -------------------------
        # Outputs: Call/Put/Greeks and status
        # -------------------------
        outputs_frame = ttk.LabelFrame(main_frame, text="CALCULATED OUTPUTS", padding="6")
        outputs_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        outputs_frame.columnconfigure((0, 1, 2), weight=1)

        # Call
        call_frame = ttk.Frame(outputs_frame, padding=(10, 10))
        call_frame.grid(row=0, column=0, sticky="nsew", padx=6)
        ttk.Label(
            call_frame,
            text="CALL Value",
            font=("Segoe UI", 10, "bold")
        ).grid(row=0, column=0, sticky="w")
        self.call_val_label = tk.Label(
            call_frame,
            text="—",
            font=("Segoe UI", 16, "bold"),
            bg="#e9f6ea",
            width=20,
            anchor='center',
            padx=12,
            pady=6
        )
        self.call_val_label.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        # Put
        put_frame = ttk.Frame(outputs_frame, padding=(10, 10))
        put_frame.grid(row=0, column=1, sticky="nsew", padx=6)
        ttk.Label(
            put_frame,
            text="PUT Value",
            font=("Segoe UI", 10, "bold")
        ).grid(row=0, column=0, sticky="w")
        self.put_val_label = tk.Label(
            put_frame,
            text="—",
            font=("Segoe UI", 16, "bold"),
            bg="#fdeaea",
            width=20,
            anchor='center',
            padx=12,
            pady=6
        )
        self.put_val_label.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        # Greeks
        greeks_frame = ttk.Frame(outputs_frame, padding=(10, 10))
        greeks_frame.grid(row=0, column=2, sticky="nsew", padx=6)
        ttk.Label(
            greeks_frame,
            text="Greeks",
            font=("Segoe UI", 10, "bold")
        ).grid(row=0, column=0, sticky="w")
        self.delta_call_label = ttk.Label(greeks_frame, text="Δ (Call): —")
        self.delta_call_label.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.delta_put_label = ttk.Label(greeks_frame, text="Δ (Put): —")
        self.delta_put_label.grid(row=2, column=0, sticky="w")
        self.gamma_label = ttk.Label(greeks_frame, text="Γ: —")
        self.gamma_label.grid(row=3, column=0, sticky="w")

        # -------------------------
        # Log console
        # -------------------------
        log_frame = ttk.LabelFrame(main_frame, text="ACTIVITY LOG", padding="6")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)

        self.status_text = scrolledtext.ScrolledText(log_frame, height=7)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        log_frame.columnconfigure(0, weight=1)

        # -------------------------
        # Plot / visualization area
        # -------------------------
        plot_frame = ttk.LabelFrame(main_frame, text="IMPLIED VOLATILITY ANALYSIS / HEATMAPS", padding="6")
        plot_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(0, weight=1)

        # Create single figure with 2 subplots
        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(12, 5))
        plt.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Initial placeholder
        draw_placeholder(self.fig, self.canvas)

    def calculate_prices(self):
        """
        Calculate Call and Put option prices along with Greeks.
        Inserts the input parameters and results into the database.
        Raises an error message if calculation fails.
        Returns:
            None
        """
        try:
            self.last_calc_id = calculate_option_prices(
                self.db,
                self.current_price_var,
                self.strike_var,
                self.ttm_var,
                self.vol_var,
                self.rate_var,
                self.last_calc_id,
                self.call_val_label,
                self.put_val_label,
                self.delta_call_label,
                self.delta_put_label,
                self.gamma_label,
                self.log_message
            )
            print(self.last_calc_id)
        except Exception as e:
            messagebox.showerror("Calculation Error", f"Could not calculate option prices: {e}")
    
    def view_history(self):
        """
        Open a new window to view the history of calculations stored in the database.
        Returns:
            None
        """
        try:
            open_history_window(
                self.db,
                self.root,
                self.fig,
                self.canvas,
                self.log_message
            )
        except Exception as e:
            messagebox.showerror("History Error", f"Could not open history window: {e}")
        

    def generate_heatmap(self):
        """
        Generate and plot heatmaps for Call and Put option prices.
        Uses the last calculated calc_id to fetch and store data.
        Raises an error message if heatmap generation fails.
        Returns:
            None
        """
        try:
            plot_heatmaps(
                self.db,
                self.last_calc_id,
                self.resolution_var,
                self.current_price_var,
                self.strike_var,
                self.ttm_var,
                self.vol_var,
                self.rate_var,
                self.spot_min_var,
                self.spot_max_var,
                self.vol_min_var,
                self.vol_max_var,
                self.fig,
                self.canvas,
                self.log_message
            )
        except Exception as e:
            messagebox.showerror("Heatmap Error", f"Could not generate heatmap: {e}")

    def log_message(self, message):
        """
        Log a message with timestamp to the status text area.
        Args:
            message (str): The message to log.
        Returns:
            None
        """
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        self.root.update_idletasks()