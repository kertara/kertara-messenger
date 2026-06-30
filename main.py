import tkinter as tk
import sys
import gc
from gui.base import KertaraGUI

def on_closing(root):
    root.destroy()
    gc.collect()

def main():
    user_profile = sys.argv[1] if len(sys.argv) > 1 else None
    root = tk.Tk()
    
    app = KertaraGUI(root, user_profile=user_profile)
    
    if hasattr(app, 'main_container'):
        root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root))
        root.mainloop()

if __name__ == "__main__":
    main()