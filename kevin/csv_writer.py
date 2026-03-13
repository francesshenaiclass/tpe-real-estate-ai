import csv

def write_header_csv(file_path, header):
    with open(file_path, "w", newline= '', encoding = "utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)


def write_info_csv(file_path, rows):
    with open(file_path, "a", newline= '', encoding = "utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerows(rows)