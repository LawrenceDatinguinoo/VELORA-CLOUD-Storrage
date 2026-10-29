from database import create_tables
from auth import login, register
from dashboard import Dashboard

create_tables()

# Create admin user if it doesn't exist
user = login("admin", "1234")
if not user:
    register("admin", "1234", "admin", 1)
    user = login("admin", "1234")

if user:
    app = Dashboard(user)
    app.mainloop()
else:
    print("Login failed")
