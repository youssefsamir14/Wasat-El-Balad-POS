from database.db import initialize_database
from services.auth import ensure_default_manager
from ui.login import LoginWindow

if __name__ == "__main__":
    initialize_database()
    ensure_default_manager()
    LoginWindow().mainloop()
