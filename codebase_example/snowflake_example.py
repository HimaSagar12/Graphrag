import snowflake.connector

def connect_to_snowflake():
    """Connects to Snowflake and performs a simple query."""
    conn = snowflake.connector.connect(
        user='your_user',
        password='your_password',
        account='your_account'
    )
    cursor = conn.cursor()
    cursor.execute("SELECT current_version()")
    one_row = cursor.fetchone()
    print(one_row[0])
    cursor.close()
    conn.close()

def another_function():
    print("This is another function.")

if __name__ == "__main__":
    connect_to_snowflake()
