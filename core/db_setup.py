import sys
from tkinter import messagebox
from mysql.connector import Error

def create_table_if_not_exists(
        db, 
        log_message
    ) -> None:
    """
    Create a table in the database if it does not already exist.
    Args:
        db: The database connection object.
        log_message: An object containing table name and schema information.
    Returns:
        None
    """
    create_inputs = """
        CREATE TABLE IF NOT EXISTS option_pricing (
            calc_id INT AUTO_INCREMENT PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            current_price DOUBLE NOT NULL,
            strike_price DOUBLE NOT NULL,
            time_to_maturity DOUBLE NOT NULL,
            volatility DOUBLE NOT NULL,
            risk_free_interest_rate DOUBLE NOT NULL
        );
        """

    create_heatmaps = """
        CREATE TABLE IF NOT EXISTS heatmap_data (
            heatmap_id INT AUTO_INCREMENT PRIMARY KEY,
            calc_id INT NOT NULL,
            spot DOUBLE NOT NULL,
            volatility DOUBLE NOT NULL,
            call_price DOUBLE NOT NULL,
            put_price DOUBLE NOT NULL,
            FOREIGN KEY (calc_id) REFERENCES option_pricing(calc_id) ON DELETE CASCADE
        );
    """
    try:
        db.execute(create_inputs)
    except Error as e:
        messagebox.showerror("Database Error", f"Could not create necessary tables: {e}")
        sys.exit(1)
    try:
        db.execute(create_heatmaps)
    except Error as e:
        messagebox.showerror("Database Error", f"Could not create necessary tables: {e}")
        sys.exit(1)

    log_message("Database tables verified/created successfully.")

def insert_input_record(
        db: any, 
        current_price: float, 
        strike_price: float, 
        time_to_maturity: float, 
        volatility: float, 
        risk_free_interest_rate: float, 
        log_message: any
    ) -> int:
    """
    Insert a new record into option_pricing table and return the inserted calc_id.
    Args:
        current_price (float): Current asset price (Spot)
        strike_price (float): Strike price of the option
        time_to_maturity (float): Time to maturity in years
        volatility (float): Volatility (σ)
        risk_free_interest_rate (float): Risk-free interest rate
    Returns:
        int: The calc_id of the newly inserted record.
    """
    insert_query = """
    INSERT INTO option_pricing (current_price, strike_price, time_to_maturity, volatility, risk_free_interest_rate)
    VALUES (%s, %s, %s, %s, %s);
    """
    params = (current_price, strike_price, time_to_maturity, volatility, risk_free_interest_rate)
    try:
        calc_id = db.execute(insert_query, params)
        log_message(f"Inserted input record with calc_id={calc_id} to the database.")
        return calc_id
    except Error as e:
        messagebox.showerror("Database Error", f"Could not insert input record: {e}")
        return None
    
def insert_heatmap_records(
        db: any, 
        calc_id: int, 
        heatmap_data: list[tuple], 
        log_message: any
    ) -> None:
    """
    Insert multiple heatmap records into heatmap_data table.
    Args:
        calc_id (int): The calculation ID to associate heatmap records with.
        heatmap_data (list of tuples): Each tuple contains (spot, volatility, call_price, put_price).
    Returns:
        None
    """
    insert_query = """
    INSERT INTO heatmap_data (calc_id, spot, volatility, call_price, put_price)
    VALUES (%s, %s, %s, %s, %s);
    """
    params = [(calc_id, spot, vol, call_price, put_price) for spot, vol, call_price, put_price in heatmap_data]
    try:
        db.execute(insert_query, params, many=True)
        log_message(f"Heatmaps generated successfully for calc_id={calc_id}.")
        log_message(f"Inserted {len(params)} heatmap records for calc_id={calc_id} to the database.")
    except Error as e:
        messagebox.showerror("Database Error", f"Could not insert heatmap records: {e}")