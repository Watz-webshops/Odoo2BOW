#!/usr/bin/env python3
import subprocess
import sys
import os

os.chdir(r"C:\Users\ruben\.vscode\github repos\Odoo2BOW\Odoo2BOW\frontend")
result = subprocess.run([sys.executable, "-m", "npm", "run", "build"], capture_output=False, text=True)
sys.exit(result.returncode)
