import mysql.connector
from mysql.connector import Error

class DBHandler:
    """
    MySQL Database Handler for Black-Scholes application.
    Manages connection setup and teardown.
    """
    def __init__(self, config: dict, reconnect_attempts: int = 3):
        self.config = dict(config)
        self.reconnect_attempts = reconnect_attempts
        self.connection = None
        self.connect()

    def connect(self):
        """Establish a connection to the MySQL database."""
        last_error = None
        for attempt in range(1, self.reconnect_attempts + 1):
            try:
                self.connection = mysql.connector.connect(**self.config)
                if self.connection.is_connected():
                    print("Connected to MySQL database")
                    return
            except Error as e:
                last_error = e
                if "Unknown database" in str(e) or '1049' in str(e):
                    try:
                        temp_connection = mysql.connector.connect(
                            host=self.config.get('host'),
                            user=self.config.get('user'),
                            password=self.config.get('password')
                        )
                        temp_cursor = temp_connection.cursor()
                        temp_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.config.get('database')}")
                        temp_cursor.close()
                        temp_connection.close()
                        print(f"Database '{self.config.get('database')}' created.")
                    except Error as ce:
                        print(f"Error creating database: {ce}")
                        break
                print(f"Attempt {attempt} - Error connecting to MySQL: {e}")
        
        if not self.connection or not self.connection.is_connected():
            raise last_error or Error("Failed to connect to MySQL database")

    def ensure_connection(self):
        """Ensure the MySQL connection is active, reconnect if necessary."""
        try:
            if self.connection is None or not self.connection.is_connected():
                self.connect()
        except Error as e:
            print(f"Error ensuring MySQL connection: {e}")
            raise

    def execute(self, query: str, params: tuple = (), many: bool = False, fetch: bool = False):
        """Execute a query with optional parameters."""
        self.ensure_connection()
        cursor = self.connection.cursor()   # Cursor object: A 'controller' for MySQL queries that actually runs the queries and holds the results.
        try:
            if many:
                cursor.executemany(query, params)
            else:
                cursor.execute(query, params or ())
            if fetch:
                return cursor.fetchall()
            else:
                self.connection.commit()
                return cursor.lastrowid
        except Error as e:
            print(f"Error executing query: {e}")
            raise
        finally:
            cursor.close()
    
    def close(self):
        """Close the MySQL connection."""
        try:
            if self.connection and self.connection.is_connected():
                self.connection.close()
                print("MySQL connection closed")
        except Error as e:
            print(f"Error closing MySQL connection: {e}")