import sys
import os

print("CWD:", os.getcwd())
print("Path:", sys.path)

try:
    import main
    print("Successfully imported main")
except Exception as e:
    print("Error importing main:", e)
    import traceback
    traceback.print_exc()

try:
    from services.stocks import get_stock_info
    print("Successfully imported services.stocks")
except Exception as e:
    print("Error importing services:", e)
