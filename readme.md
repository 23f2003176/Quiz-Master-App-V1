
# 🎯 KUIZU-V1

A **Flask-based web application** for creating and taking quizzes.

## 🚀 Features

✅ **User Authentication** – Secure login & registration  
✅ **Admin Dashboard** – Manage quizzes, users & analytics  
✅ **Student Interface** – Take quizzes seamlessly  
✅ **Quiz Categories & Chapters** – Organize questions effectively  
✅ **Detailed Analytics** – Track progress & performance  
✅ **RESTful API** – For mobile integration  

---

## ⚡ Installation & Setup

### 1️⃣ **Clone the Repository**
```bash
git clone https://github.com/23f2003176/Quiz-Master-App-V1.git
cd Quiz-Master-App-V1
```

### 2️⃣ **Create a Virtual Environment**
```bash
python -m venv venv
```

### 3️⃣ **Activate the Virtual Environment**
- **Windows**:  
  ```bash
  venv\Scripts\activate
  ```
- **Mac/Linux**:  
  ```bash
  source venv/bin/activate
  ```

### 4️⃣ **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 5️⃣ **Set Up Environment Variables**
Copy the example environment file:
```bash
cp .env.example .env
```
Open `.env` and configure:  

- **SECRET_KEY** (Generate a secure key):
  ```bash
  python -c "import secrets; print(secrets.token_hex(64))"
  ```
- **Database Configuration (Example using SQLite)**:
  ```bash
  SQLALCHEMY_DATABASE_URI=sqlite:///db.sqlite3
  ```

### 6️⃣ **Run the Application**
```bash
flask run
```
Your Flask app will now be running locally! 🎉  

---

## 🎯 Contribution Guidelines
Want to contribute? Feel free to **fork** this repository, submit a PR, or open an issue!

---

## 📜 License
This project is **licensed under [MIT License](LICENSE)**.  

---

Let me know if you need more improvements! 🚀
