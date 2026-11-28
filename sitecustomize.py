import sys
sys.modules["_zoneinfo"] = None  # force pure-python zoneinfo (C impl segfaults)