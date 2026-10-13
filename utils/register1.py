import os
import json

def register1(file_name, content):
     if not os.path.exists(file_name):
          with open(file_name, "w", encoding="utf-8") as file:
               json.dump([], file, indent=4)
     with open(file_name, "r", encoding="utf-8") as file:
          try:
               registers = json.load(file)
          except json.JSONDecodeError:
               registers = []
     registers.append(content)
     with open(file_name, "w", encoding="utf-8") as file:
          json.dump(registers, file, indent=4)