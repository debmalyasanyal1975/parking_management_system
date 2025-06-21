# ParkEasy - Smart Parking Management System

ParkEasy is a full-stack web application designed to simplify parking management in campuses, office complexes, or residential areas. It allows users to register, view available parking lots, reserve a spot, and track their parking activity. Admins can manage parking lots, monitor reservations, and control user access.

---

## 🚀 Features

### 👤 User Side:

* Register and log in securely
* View available parking lots and real-time spot status
* Book and release parking spots
* View cost based on parking duration

### 🛠️ Admin Side:

* Admin dashboard with real-time stats
* Add, edit, or delete parking lots
* Manage individual parking spots
* View and delete registered users
* Monitor all reservations (past and active)

---

## ⚙️ Technologies Used

* **Backend:** Python, Flask
* **Frontend:** HTML, CSS, Bootstrap 5, Font Awesome
* **Database:** SQLite3
* **Templating:** Jinja2

---

## 🔐 Security

* Passwords are securely hashed using Werkzeug
* Role-based access control (Admin/User)
* Session-based user login

---

## 🧱 Database Schema (ER Diagram)

* **Users** → id, username, password, role
* **ParkingLots** → id, name, address, pin\_code, price\_per\_hour, max\_spots
* **ParkingSpots** → id, lot\_id (FK), spot\_number, status
* **Reservations** → id, spot\_id (FK), user\_id (FK), timestamps, cost

---

## 📌 Installation Instructions

1. **Clone the repo:**

```bash
git clone https://github.com/debmalyasanyal1975/ParkEasy.git
cd ParkEasy
```

2. **Set up a virtual environment:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Run the application:**

```bash
python app.py runserver
```

5. **Visit:** `http://localhost:5000`

---

## 📽️ Presentation

* \https://drive.google.com/file/d/1T8uv_bqZLsX6oVNzly6OubqEcj2I7Tox/view?usp=drive_link

---

## 🤖 AI/LLM Use Disclosure

* About **20%** of this project was built with the help of AI (ChatGPT) for guidance on design, Flask structure, and code suggestions. The remaining **80%** was independently developed and tested by the student.

---

## 📄 License

MIT License

---

**Developed by Debmalya Sanyal**
