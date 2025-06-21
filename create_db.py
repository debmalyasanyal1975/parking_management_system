import sqlite3
from werkzeug.security import generate_password_hash

def create_tables():
    conn = sqlite3.connect('park_easy.db')
    c = conn.cursor()

    # USERS table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'user'))
        )
    ''')

    # PARKING LOTS table
    c.execute('''
        CREATE TABLE IF NOT EXISTS parking_lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prime_location_name TEXT NOT NULL,
            address TEXT NOT NULL,
            pin_code TEXT NOT NULL,
            price_per_hour REAL NOT NULL,
            maximum_number_of_spots INTEGER NOT NULL
        )
    ''')

    # PARKING SPOTS table
    c.execute('''
        CREATE TABLE IF NOT EXISTS parking_spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER NOT NULL,
            spot_number INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('A', 'O')),
            FOREIGN KEY (lot_id) REFERENCES parking_lots(id)
        )
    ''')

    # RESERVATIONS table
    c.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spot_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            parking_timestamp TEXT NOT NULL,
            leaving_timestamp TEXT,
            parking_cost REAL,
            FOREIGN KEY (spot_id) REFERENCES parking_spots(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Insert default admin user if not present
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        hashed_password = generate_password_hash("admin_password")
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ('admin', hashed_password, 'admin'))
        print("🛡️ Default admin user created (username: admin, password: admin_password)")

    conn.commit()
    conn.close()
    print("✅ Database and tables created successfully!")

if __name__ == '__main__':
    create_tables()
