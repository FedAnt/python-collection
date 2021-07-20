###
# Парсинг сайта Мин.связи для получения списка Российского ПО.
###

import urllib.request
from bs4 import BeautifulSoup
import csv


BASE_URL = 'https://reestr.minsvyaz.ru/reestr/?PAGEN_1='
SAVE_PATH = 'E:\\soft.csv'


def get_html(url):
    response = urllib.request.urlopen(url)
    return response.read().decode(response.headers.get_content_charset())


def get_page_count(html):
    soup = BeautifulSoup(html, features='html5lib')
    paggination = soup.find('div', class_='page_nav_area')
    return int(paggination.find_all('a')[-2].get_text())


def parse(html):
    soup = BeautifulSoup(html, features='html5lib')
    table = soup.find('div', class_="result_area")

    # массив софта
    softs = []

    for row in table.find_all('div')[7:]:
        cols = row.find_all('div')

        if cols != []:
            if cols[0].get_text().strip() == '...':
                break

            softs.append({
                'nums': cols[0].get_text().strip(),
                'name': cols[1].get_text().strip().encode('cp1251', errors='replace').decode('cp1251'),
                'class': cols[2].get_text().strip(),
                'date': cols[3].get_text().strip().replace('                    ', ' '),
                'address': cols[4].find('a').get('href').strip(u'\u200b').strip('%')
            })

    return softs


def set_csv(softs, path):
    with open(path, 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(('№', 'Название', 'Класс ПО', 'Дата внесения', 'Адрес сайта'))

        for soft in softs:
            writer.writerow((soft['nums'], soft['name'], soft['class'], soft['date'], soft['address']))

    csvfile.close()


def main():
    page_count = get_page_count(get_html(BASE_URL + '1'))
    print('Всего найдено страниц %d ' % page_count)

    softs = []

    for page in range(1, page_count + 1):
        #    for page in range(191, 191 + 1):
        print('Парсинг %d%%' % (page / page_count * 100))
        softs.extend(parse(get_html(BASE_URL + '%d' % page)))

    set_csv(softs, SAVE_PATH)


if __name__ == '__main__':
    main()
