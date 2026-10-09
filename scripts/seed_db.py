import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.seed import seed_db

if __name__ == "__main__":
    seed_db()
    print("Database seeding completed.")
