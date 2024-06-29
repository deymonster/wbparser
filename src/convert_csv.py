import csv

input_filename = 'data.csv'
output_filename = 'processed_data.csv'

with open(input_filename, mode='r', encoding='utf-8') as infile, open(output_filename, mode='w', encoding='utf-8', newline='') as outfile:
    reader = csv.reader(infile)
    writer = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)

    headers = next(reader)  # Считывание заголовков
    writer.writerow(headers)  # Запись заголовков в выходной файл

    for row in reader:
        # Оборачиваем значение в столбце `name` (индекс 1) в двойные кавычки
        writer.writerow([row[0], f'"{row[1]}"', row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9]])


print(f'Файл успешно обработан и сохранен как {output_filename}.')
