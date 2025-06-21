# app.py
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
# IMPORTANT: Replace with a strong, random secret key in a production environment
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_super_secret_key_parkeasy_2025') 

# Define the path for the database
DATABASE = 'parking_app.db'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin_password' # Default admin password

def get_db():
    """Establishes a database connection or returns the existing one."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row # This allows access to columns by name
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Closes the database connection at the end of the request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initializes the database schema and creates the admin user."""
    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
            );
        ''')

        # Create parking_lots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parking_lots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prime_location_name TEXT NOT NULL,
                address TEXT NOT NULL,
                pin_code TEXT NOT NULL,
                price_per_hour REAL NOT NULL,
                maximum_number_of_spots INTEGER NOT NULL
            );
        ''')

        # Create parking_spots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parking_spots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_id INTEGER NOT NULL,
                spot_number INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'A', -- 'A' for Available, 'O' for Occupied
                FOREIGN KEY (lot_id) REFERENCES parking_lots(id) ON DELETE CASCADE,
                UNIQUE (lot_id, spot_number)
            );
        ''')

        # Create reservations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spot_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                parking_timestamp TEXT NOT NULL,
                leaving_timestamp TEXT,
                parking_cost REAL,
                FOREIGN KEY (spot_id) REFERENCES parking_spots(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        ''')

        # Check and create admin user if not exists
        cursor.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USERNAME,))
        admin_exists = cursor.fetchone()
        if not admin_exists:
            hashed_password = generate_password_hash(ADMIN_PASSWORD)
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                           (ADMIN_USERNAME, hashed_password, 'admin'))
            db.commit()
            print(f"Admin user '{ADMIN_USERNAME}' created with password '{ADMIN_PASSWORD}'")
        else:
            print(f"Admin user '{ADMIN_USERNAME}' already exists.")

        db.commit()
    print("Database initialized successfully.")

# Run database initialization once when the app starts
with app.app_context():
    init_db()

# --- Authentication and Authorization Decorators ---
def login_required(f):
    """Decorator to require user login."""
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__ # Preserve original function name for Flask
    return wrap


def admin_required(f):
    """Decorator to require admin role."""
    def wrap(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Unauthorized access. Admin privileges required.', 'danger')
            return redirect(url_for('login')) # Or to a generic unauthorized page
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__ # Preserve original function name for Flask
    return wrap

# --- Routes ---

@app.route('/', methods=['GET', 'POST'])
def login():
    """Handles user and admin login."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f'Welcome, {user["username"]}!', 'success')
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'user')",
                           (username, hashed_password))
            db.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Please choose a different one.', 'danger')
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Logs out the current user."""
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- Admin Routes ---

@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    """Displays the admin dashboard with parking lot overview."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM parking_lots")
    parking_lots = cursor.fetchall()

    lot_status = []
    for lot in parking_lots:
        cursor.execute("SELECT COUNT(*) FROM parking_spots WHERE lot_id = ?", (lot['id'],))
        total_spots = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM parking_spots WHERE lot_id = ? AND status = 'O'", (lot['id'],))
        occupied_spots = cursor.fetchone()[0]
        available_spots = total_spots - occupied_spots
        lot_status.append({
            'lot': lot,
            'total_spots': total_spots,
            'occupied_spots': occupied_spots,
            'available_spots': available_spots
        })
    return render_template('admin_dashboard.html', lot_status=lot_status)

@app.route('/admin/parking_lot/add', methods=['GET', 'POST'])
@admin_required
def add_parking_lot():
    """Handles adding a new parking lot."""
    if request.method == 'POST':
        prime_location_name = request.form['prime_location_name']
        address = request.form['address']
        pin_code = request.form['pin_code']
        price_per_hour = float(request.form['price_per_hour'])
        maximum_number_of_spots = int(request.form['maximum_number_of_spots'])

        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO parking_lots (prime_location_name, address, pin_code, price_per_hour, maximum_number_of_spots) VALUES (?, ?, ?, ?, ?)",
            (prime_location_name, address, pin_code, price_per_hour, maximum_number_of_spots)
        )
        lot_id = cursor.lastrowid

        # Add parking spots for the new lot
        for i in range(1, maximum_number_of_spots + 1):
            cursor.execute("INSERT INTO parking_spots (lot_id, spot_number, status) VALUES (?, ?, 'A')",
                           (lot_id, i))
        db.commit()
        flash('Parking lot added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_edit_parking_lot.html', lot=None)

@app.route('/admin/parking_lot/edit/<int:lot_id>', methods=['GET', 'POST'])
@admin_required
def edit_parking_lot(lot_id):
    """Handles editing an existing parking lot."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM parking_lots WHERE id = ?", (lot_id,))
    lot = cursor.fetchone()

    if not lot:
        flash('Parking lot not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        prime_location_name = request.form['prime_location_name']
        address = request.form['address']
        pin_code = request.form['pin_code']
        price_per_hour = float(request.form['price_per_hour'])
        new_maximum_number_of_spots = int(request.form['maximum_number_of_spots'])

        # Get current number of spots
        cursor.execute("SELECT COUNT(*) FROM parking_spots WHERE lot_id = ?", (lot_id,))
        current_spots = cursor.fetchone()[0]

        # Update parking lot details
        cursor.execute(
            "UPDATE parking_lots SET prime_location_name = ?, address = ?, pin_code = ?, price_per_hour = ?, maximum_number_of_spots = ? WHERE id = ?",
            (prime_location_name, address, pin_code, price_per_hour, new_maximum_number_of_spots, lot_id)
        )

        # Adjust parking spots based on new maximum_number_of_spots
        if new_maximum_number_of_spots > current_spots:
            for i in range(current_spots + 1, new_maximum_number_of_spots + 1):
                cursor.execute("INSERT INTO parking_spots (lot_id, spot_number, status) VALUES (?, ?, 'A')", (lot_id, i))
        elif new_maximum_number_of_spots < current_spots:
            # Delete extra spots (and related reservations if any exist - CASCADE ensures this)
            # Find the highest spot number for this lot
            cursor.execute("SELECT MAX(spot_number) FROM parking_spots WHERE lot_id = ?", (lot_id,))
            max_spot_number_in_db = cursor.fetchone()[0]

            for i in range(new_maximum_number_of_spots + 1, max_spot_number_in_db + 1):
                # Only delete if not occupied, or handle occupied spots as per business logic (e.g., prevent deletion)
                # For simplicity, we assume you can delete if needed, but in real world, this is complex.
                # If a spot is occupied, you might want to prevent its deletion.
                cursor.execute("DELETE FROM parking_spots WHERE lot_id = ? AND spot_number = ? AND status = 'A'", (lot_id, i))
                # If you want to delete occupied spots too, remove the `AND status = 'A'` part.
                # It's better to warn admin if occupied spots are being deleted.
        db.commit()
        flash('Parking lot updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_edit_parking_lot.html', lot=lot)

@app.route('/admin/parking_lot/delete/<int:lot_id>', methods=['POST'])
@admin_required
def delete_parking_lot(lot_id):
    """Handles deleting a parking lot."""
    db = get_db()
    cursor = db.cursor()
    try:
        # Check if there are any occupied spots in this lot
        cursor.execute("SELECT COUNT(*) FROM parking_spots WHERE lot_id = ? AND status = 'O'", (lot_id,))
        occupied_count = cursor.fetchone()[0]

        if occupied_count > 0:
            flash(f'Cannot delete parking lot. There are {occupied_count} occupied spots.', 'danger')
        else:
            cursor.execute("DELETE FROM parking_lots WHERE id = ?", (lot_id,))
            db.commit()
            flash('Parking lot deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting parking lot: {e}', 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/parking_lot/<int:lot_id>/spots')
@admin_required
def view_parking_spots(lot_id):
    """Displays parking spots for a specific lot."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM parking_lots WHERE id = ?", (lot_id,))
    lot = cursor.fetchone()

    if not lot:
        flash('Parking lot not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    cursor.execute("""
        SELECT
            ps.id AS spot_id,
            ps.spot_number,
            ps.status,
            r.id AS reservation_id,
            r.user_id,
            u.username AS reserved_by_username,
            r.parking_timestamp
        FROM parking_spots ps
        LEFT JOIN reservations r ON ps.id = r.spot_id AND r.leaving_timestamp IS NULL
        LEFT JOIN users u ON r.user_id = u.id
        WHERE ps.lot_id = ?
        ORDER BY ps.spot_number
    """, (lot_id,))
    parking_spots = cursor.fetchall()

    return render_template('view_parking_spots.html', lot=lot, parking_spots=parking_spots)

# --- Admin: User Management Routes ---
@app.route('/admin/manage_users')
@admin_required
def admin_manage_users():
    """Displays a list of all users for admin to manage."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, username, role FROM users ORDER BY username ASC")
    users = cursor.fetchall()
    return render_template('admin_manage_users.html', users=users)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Deletes a user from the system."""
    db = get_db()
    cursor = db.cursor()

    # Prevent admin from deleting themselves or other admins (for simplicity)
    cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    user_to_delete = cursor.fetchone()

    if not user_to_delete:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_manage_users'))

    if user_to_delete['role'] == 'admin':
        flash('Cannot delete an admin user.', 'danger')
        return redirect(url_for('admin_manage_users'))

    if user_id == session.get('user_id'):
        flash('You cannot delete your own account while logged in.', 'danger')
        return redirect(url_for('admin_manage_users'))

    try:
        # Check if the user has any active reservations
        cursor.execute("SELECT COUNT(*) FROM reservations WHERE user_id = ? AND leaving_timestamp IS NULL", (user_id,))
        active_reservations_count = cursor.fetchone()[0]

        if active_reservations_count > 0:
            flash('Cannot delete user with active parking reservations. Please ensure they have released all spots.', 'danger')
        else:
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            db.commit()
            flash('User deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting user: {e}', 'danger')
    return redirect(url_for('admin_manage_users'))


# --- Admin: All Reservations Route ---
@app.route('/admin/all_reservations')
@admin_required
def admin_all_reservations():
    """Displays a list of all reservations (past and active) for admin."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT
            r.id,
            r.parking_timestamp,
            r.leaving_timestamp,
            r.parking_cost,
            u.username,
            ps.spot_number,
            pl.prime_location_name
        FROM reservations r
        JOIN users u ON r.user_id = u.id
        JOIN parking_spots ps ON r.spot_id = ps.id
        JOIN parking_lots pl ON ps.lot_id = pl.id
        ORDER BY r.parking_timestamp DESC;
    """)
    all_reservations = cursor.fetchall()
    return render_template('admin_all_reservations.html', all_reservations=all_reservations)


# --- User Routes ---

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    """Displays the user dashboard with available parking lots and user's reservations."""
    db = get_db()
    cursor = db.cursor()

    # Get available parking lots and their spot counts
    cursor.execute("""
        SELECT
            pl.id,
            pl.prime_location_name,
            pl.address,
            pl.pin_code,
            pl.price_per_hour,
            pl.maximum_number_of_spots,
            COUNT(ps.id) FILTER (WHERE ps.status = 'A') AS available_spots,
            COUNT(ps.id) AS total_spots
        FROM parking_lots pl
        JOIN parking_spots ps ON pl.id = ps.lot_id
        GROUP BY pl.id
        ORDER BY pl.prime_location_name;
    """)
    parking_lots_summary = cursor.fetchall()

    # Get user's current reservations
    user_id = session['user_id']
    cursor.execute("""
        SELECT
            r.id AS reservation_id,
            r.parking_timestamp,
            r.leaving_timestamp,
            r.parking_cost,
            ps.spot_number,
            pl.prime_location_name,
            pl.address,
            pl.price_per_hour
        FROM reservations r
        JOIN parking_spots ps ON r.spot_id = ps.id
        JOIN parking_lots pl ON ps.lot_id = pl.id
        WHERE r.user_id = ? AND r.leaving_timestamp IS NULL
        ORDER BY r.parking_timestamp DESC;
    """, (user_id,))
    user_reservations = cursor.fetchall()

    return render_template('user_dashboard.html',
                           parking_lots_summary=parking_lots_summary,
                           user_reservations=user_reservations)

@app.route('/user/book_spot/<int:lot_id>', methods=['POST'])
@login_required
def book_spot(lot_id):
    """Allows a user to book an available spot in a parking lot."""
    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    # Check if user already has an active reservation
    cursor.execute("SELECT COUNT(*) FROM reservations WHERE user_id = ? AND leaving_timestamp IS NULL", (user_id,))
    active_reservations = cursor.fetchone()[0]
    if active_reservations > 0:
        flash('You already have an active parking reservation. Please release it before booking a new one.', 'warning')
        return redirect(url_for('user_dashboard'))

    # Find an available spot in the specified lot
    cursor.execute("""
        SELECT id, spot_number FROM parking_spots
        WHERE lot_id = ? AND status = 'A'
        ORDER BY spot_number ASC LIMIT 1
    """, (lot_id,))
    available_spot = cursor.fetchone()

    if available_spot:
        spot_id = available_spot['id']
        spot_number = available_spot['spot_number']
        parking_timestamp = datetime.now().isoformat()

        # Update spot status to 'O' (Occupied)
        cursor.execute("UPDATE parking_spots SET status = 'O' WHERE id = ?", (spot_id,))

        # Create reservation
        cursor.execute(
            "INSERT INTO reservations (spot_id, user_id, parking_timestamp, leaving_timestamp, parking_cost) VALUES (?, ?, ?, NULL, NULL)",
            (spot_id, user_id, parking_timestamp)
        )
        db.commit()
        flash(f'Spot {spot_number} in parking lot booked successfully!', 'success')
    else:
        flash('No available spots in this parking lot.', 'danger')
    return redirect(url_for('user_dashboard'))

@app.route('/user/release_spot/<int:reservation_id>', methods=['POST'])
@login_required
def release_spot(reservation_id):
    """Allows a user to release a booked parking spot."""
    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM reservations WHERE id = ? AND user_id = ? AND leaving_timestamp IS NULL",
                   (reservation_id, user_id))
    reservation = cursor.fetchone()

    if reservation:
        spot_id = reservation['spot_id']
        parking_timestamp_str = reservation['parking_timestamp']
        parking_timestamp = datetime.fromisoformat(parking_timestamp_str)
        leaving_timestamp = datetime.now()

        # Calculate parking duration in hours
        duration = leaving_timestamp - parking_timestamp
        duration_hours = duration.total_seconds() / 3600.0

        # Get price per hour from parking lot
        cursor.execute("""
            SELECT pl.price_per_hour
            FROM parking_lots pl
            JOIN parking_spots ps ON pl.id = ps.lot_id
            WHERE ps.id = ?
        """, (spot_id,))
        price_per_hour = cursor.fetchone()['price_per_hour']

        parking_cost = round(duration_hours * price_per_hour, 2) # Round to 2 decimal places

        # Update reservation
        cursor.execute(
            "UPDATE reservations SET leaving_timestamp = ?, parking_cost = ? WHERE id = ?",
            (leaving_timestamp.isoformat(), parking_cost, reservation_id)
        )

        # Update parking spot status to 'A' (Available)
        cursor.execute("UPDATE parking_spots SET status = 'A' WHERE id = ?", (spot_id,))
        db.commit()
        flash(f'Parking spot released. Total cost: ${parking_cost:.2f}', 'success')
    else:
        flash('Reservation not found or already released.', 'danger')
    return redirect(url_for('user_dashboard'))


if __name__ == '__main__':
    # Ensure the templates directory exists
    if not os.path.exists('templates'):
        os.makedirs('templates')
    app.run(debug=True) # debug=True for development, turn off for production
