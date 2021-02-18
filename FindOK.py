import csv
import os

files = os.listdir(".")
for file in files:
    if "res" in file and file.endswith(".csv"):
        with open(file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                #print(float(row['recover_price_radio']))
                if float(row['recover_price_radio']) == 0:
                    #print(row)
                    print(file)