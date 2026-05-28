import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))
import db_creation

if __name__ == "__main__":
    db_creation.main()
