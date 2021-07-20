##########
# Скрипт для подписи портов на коммутаторах cisco
# !!! Переписать
##########
import socket
import subprocess
import ipaddress
import sqlite3
import paramiko
import time

import os
import re

# ----------------------------------------------------------------------------------------------------------------------
#										Parametrs
# ----------------------------------------------------------------------------------------------------------------------
# задаем диапазон ip адресов, в котором будем искать коммутаторы cisco
ip_range = "172.16.254.0/24"
# время задержки для параметра socket
timeout = 5.0
# имя БД 
db_name = "desc.db"
# путь до папки с файлами логов авторизации РС в сети 
dirName = "//dc3/transit$/logon/hosts"
# Количество запросов ping до ожидания ответа устройства
ping_counter = 4
# пользователь для подключения по ssh
usr = 'someuser'
# пароль для подключения по ssh
pwd = open('pwd.txt', 'r').read()
# порт для подключения по ssh
port = 22
# Данные c какой строки читать (ключ + номер строки для mac-address table)
nstr = 4 + 1
# список коммутаторов, которые можно подписывать
sw_list = []
# список префиксов описания портов, которые можно подписывать
ltada = []
# список префиксов описания портов, которые нельзя подписывать
ltadd = []


# ----------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------ Functions
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# Блок с общими функциями


def set_query_for_db(query):
    '''
    Функция выполняет произвольный SQL запрос
    '''
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute(query)
    con.commit()
    con.close()


def get_select_in_db_ex(query):
    '''
    функция отправляющая в БД запрос
    '''
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute(query)
    data = cur.fetchall()
    con.close()
    if len(data):
        return data


def get_select_in_db_exp(query, data):
    '''
    функция отправляющая в БД запрос
    '''
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute(query, data)
    data = cur.fetchall()
    con.close()
    if len(data):
        return data


def delete_data_from_db(tb_name, id_if):
    '''
    функция удалеяет данные из указанной таблицы БД
    '''
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute("DELETE FROM %s WHERE %s" % (tb_name, id_if))
    con.commit()
    con.close()


def insert_data_to_db(query, datas):
    '''
    Функция записывает в SQLite данных
    '''
    con = sqlite3.connect(db_name)
    con.executemany(query, datas)
    con.commit()
    con.close()


def update_data_to_db(query, data):
    '''
    Функция записывает в SQLite данных
    '''
    con = sqlite3.connect(db_name)
    con.execute(query, data)
    con.commit()
    con.close()


def check_mac_in_db(tb_name, mac_addr):
    '''
    Функция, которая роверяет наличие мак адреса в базе mac from files
    tb_name - имя БД из которой делаем запрос
    mac_addr - mac адрес в формате win ('000A5E492E8B'), который ищем в БД
    '''
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    cur.execute("SELECT count() FROM '%s' WHERE mac_addr = '%s'" % (tb_name, mac_addr))
    data = cur.fetchall()
    con.close()
    if data[0][0] != 0:
        return True
    else:
        return False


def get_win_mac(mac):
    '''
    функция для перевода мак адреса из формата cisco в формат log файлов
    50e5.49ce.bb40 -> 50E549CEBB40
    убирает точки и переводит в верхний регистр
    '''
    return re.sub('\.', '', mac.upper())


def ssh_command(host, comm):
    '''
    функция для выполнения команды на cisco
    '''
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # Подключаемся к коммутатору
    client.connect(hostname=host, username=usr, password=pwd, port=port)
    # Выполняем команду
    stdin, stdout, stderr = client.exec_command(comm)
    # Вывод читаем построчно
    data = stdout.readlines()

    # Закрываем подключение к коммутатору
    client.close()

    return data


def ssh_commands(host, comms):
    '''
    функция для выполнения команды на cisco
    '''
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # Подключаемся к коммутатору
    client.connect(hostname=host, username=usr, password=pwd, port=port)
    commands = ""
    for comm in comms:
        commands += comm + str('\n')

    channel = client.invoke_shell()
    stdin = channel.makefile('wb')
    stdout = channel.makefile('rb')

    stdin.write(commands)

    stdout.close()
    stdin.close()
    client.close()


def date_to_second(t_date):
    '''
    :param t_date: в формате "2017-05-02 10:50:16"
    :return: возвращает время в секундах
    '''
    return time.mktime(time.strptime(t_date, "%Y-%m-%d %H:%M:%S"))


# ----------------------------------------------------------------------------------------------------------------------
# 1 Блок по сканированию сети и записи IP адресов cisco в БД


def my_ping(ip_range):
    '''
    функция пингует диапазон IP адресов и возвращет список доступных устройств
    '''
    # Create the network
    ip_net = ipaddress.ip_network(ip_range)

    # Get all hosts on that network
    all_hosts = list(ip_net.hosts())

    # Configure subprocess to hide the console window
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = subprocess.SW_HIDE
    ip_range_online = []
    # For each IP address in the subnet,
    # run the ping command with subprocess.popen interface
    for i in range(len(all_hosts)):
        for j in range(0, ping_counter):
            output = subprocess.Popen(['ping', '-n', '1', '-w', '500', str(all_hosts[i])], stdout=subprocess.PIPE,
                                      startupinfo=info).communicate()[0]
            if ("Заданный узел недоступен" in output.decode('cp866')):
                None
            elif ("Превышен интервал ожидания для запроса" in output.decode('cp866')):
                None
            else:
                print(str(all_hosts[i]) + " is Online")
                ip_range_online.append(str(all_hosts[i]))
                break
    return ip_range_online


def find_cisco_ip(ip_range_online):
    '''
    функция по диапозону ищет устройства, которые по 22 порту отвечают фразой
    "SSH-2.0-Cisco-1.25"
    '''
    ip_cisco_online = []
    for i in range(len(ip_range_online)):
        ip_device = ip_range_online[i]
        # print (str(ip_device))
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # sock = socket.socket()
            sock.settimeout(timeout)
            sock.connect((str(ip_device), 22))  # соединяемся к порту, i - port
            sock.settimeout(None)

        except:
            pass

        else:
            result = sock.recv(65536)  # очередная порция байтов
            if ("SSH-2.0-Cisco-1.25" in result.decode("utf-8")):
                ip_cisco_online.append(ip_device)
            sock.close()
            continue  # если порт закрыт, то переходим к следующему
    return ip_cisco_online


# !!! Переписать !!! #
def insert_ip_cisco_in_db(ip_cisco_online):
    '''
    функция принимает диапазон ip адресов
    проверяет на существование этих IP адресов в БД
    и если они отсутствуют, то записывает их в БД
    '''
    con = sqlite3.connect(db_name)
    cur = con.cursor()
    ip_for_insert = []
    j = 0
    for i in range(len(ip_cisco_online)):

        cur.execute("SELECT * FROM tb_switches WHERE ip_addr = '%s'" % ip_cisco_online[i])
        data = cur.fetchall()
        if not len(data):
            ip_for_insert.append([])
            ip_for_insert[j].append(ip_cisco_online[i])
            ip_for_insert[j].append("1")
            j += 1
    con.close()

    con = sqlite3.connect(db_name)
    con.executemany("INSERT INTO tb_switches (ip_addr, status) VALUES(?, ?)", ip_for_insert)
    con.commit()
    con.close()


# !!! Переписать !!! #
def insert_cisco_sign_db():
    # Функция получает данные по коммутаторам
    switches = get_select_in_db_ex("select id_switch, ip_addr, name from tb_switches where status = 1")

    for switch in switches:
        print(switch[1])
        datas = ssh_command(switch[1], "show version")
        for data in datas:
            # Получаем серийный номер
            if data.find("Model number") + 1 > 0:
                mn = data.split(": ")[1].strip()
            # Получаем версию прошивки
            elif data.find("IOS (tm)") + 1 > 0:
                ios = data.split(",")[0].split("e (")[1][0:-1].strip()
            # Получаем мак адрес коммутатора
            elif data.find("MAC Address") + 1 > 0:
                mac_addr = data.split(": ")[1].strip()
            # Получаем время работы коммутатора
            elif data.find("uptime") + 1 > 0:
                hostname = data.split(" ")[0].strip()
        print(ios)
        print(mn)
        print(mac_addr)
        print(hostname)
        # Обновляем название коммутатора
        if switch[2] == "":
            update_data_to_db("UPDATE tb_switches SET name = ? WHERE id_switch = ?", (hostname, switch[0]))
            print("!")
        print("--!!!---")


# ----------------------------------------------------------------------------------------------------------------------
# 2 Блок по записи данных о mac адресах, из лог файлов входа в систему, в БД


def get_datas_from_files_int():
    '''
    получение из log-файлов данных в сети Интернет-ГХК
    '''
    # счетчик строк
    i = 0
    # список списков с данными
    l = []

    # считываем список файлов
    names = os.listdir(dirName)
    for name in names:
        # создаем внутри списка вложенные списки
        l.append([])
        # получаем полное имя
        fullname = os.path.join(dirName, name)
        f = open(fullname, 'r')
        # получаем последую строку
        last_string = f.readlines()[-1]
        # делим последную строку на список
        l_last_string = (re.split('\|', last_string))
        # дата и время
        l[i].append(l_last_string[0].strip(" ").replace('/', '-') + " " + l_last_string[1].strip(" "))
        # имя РС
        l[i].append(l_last_string[2].strip(" "))
        # ip адрес РС
        l[i].append(l_last_string[3].strip(" ").replace(' ', ''))
        # mac адрес РС
        l[i].append(l_last_string[4].strip(" ")[4:])
        un_os = l_last_string[5].strip(" ").split(' OS:')
        # имя пользователя
        l[i].append(un_os[0].split("\\")[0])
        l[i].append(un_os[0].split("\\")[1])
        # версия ОС (6)
        l[i].append(un_os[1])
        # время изменения файла (7)
        # l[i].append(datetime.fromtimestamp(os.path.getmtime(fullname)))
        i += 1
        f.close()
    return l


def get_datas_from_files_kc(dir_name):
    # получение из log-файлов данных в КС

    # счетчик строк
    i = 0
    # список списков с данными
    l = []

    # считываем список файлов
    names = os.listdir(dir_name)
    for name in names:
        # создаем внутри списка вложенные списки
        l.append([])
        # получаем полное имя
        fullname = os.path.join(dir_name, name)
        f = open(fullname, 'r')
        # получаем последую строку
        last_string = f.readlines()[-1]
        # print (last_string)
        # делим последную строку на список
        l_last_string = (re.split('\|', last_string))

        cur_string = l_last_string[0].split(';')

        # дата и время
        l[i].append(cur_string[0])
        # hostname
        l[i].append(cur_string[1].split('\\')[1])
        # username
        l[i].append(cur_string[2].split('\\')[1])
        # mac-address
        l[i].append(cur_string[3])
        # IP адрес
        l[i].append(cur_string[4].strip(' ').replace(' ', ''))
        # версия ОС
        l[i].append(cur_string[9])

        i += 1
        f.close()
    return l


def get_datas_from_file_int(f_name):
    '''

    Функция читающая один log-файл из сети Интернет-ГХК
    и разбивающая последную строку на поля таблицы tb_mac_from_files

    f_name - имя файла, которое мы анализируем этой функцией
    outdata - данные собранные для записи в БД tb_mac_from_files
    '''

    # создаем внутри списка вложенные списки
    outdata = []
    # получаем полное имя
    fullname = os.path.join(dirName, f_name)
    # открываем файл
    f = open(fullname, 'r')
    # получаем последую строку
    last_string = f.readlines()[-1]
    # делим последную строку на список
    l_last_string = (re.split('\|', last_string))

    # дата и время входа пользователя в систему из log-файла (0)
    outdata.append(l_last_string[0].strip(" ").replace('/', '-') + " " + l_last_string[1].strip(" "))
    # имя РС (1)
    outdata.append(l_last_string[2].strip(" "))
    # ip адрес РС (2)
    outdata.append(l_last_string[3].strip(" ").replace(' ', ''))
    # mac адрес РС (3)
    outdata.append(l_last_string[4].strip(" ")[4:])
    # ФИО пользователя (4)
    un_os = l_last_string[5].strip(" ").split(' OS:')
    # l[i].append(un_os[0])
    outdata.append(un_os[0].split("\\")[0])
    # логин пользователя (5)
    outdata.append(un_os[0].split("\\")[1])
    # версия ОС (6)
    outdata.append(un_os[1])
    # время изменения log-файла (7)
    # outdata.append(datetime.fromtimestamp(os.path.getmtime(fullname)))

    f.close()
    return outdata


def set_datas_from_file():
    '''
    Функция опрашивает все log-файлы из папки глобальной переменной dirName
    и записывает эти данные в БД, в случае если запись об этой РС есть, то
    обновляет данные
    '''
    # считываем список файлов
    f_names = os.listdir(dirName)

    # пробегаемся по файлам и смотрим надо ли данные по ним обновлять или записывать по новой
    for f_name in f_names:
        # получаем данные с последней строки читаемого файла f_name
        data_from_f = get_datas_from_file_int(f_name)

        # получаем из БД (tb_mac_from_files) строку содержащую mac-адрес из файла
        data_from_db = get_select_in_db_exp(
            "select * from tb_mac_from_files where mac_addr=:mac_addr",
            {"mac_addr": data_from_f[3], })

        if (data_from_db == None):
            print("Insert - {}".format(data_from_f))
            insert_data_to_db('''
                INSERT INTO tb_mac_from_files (date_from_file, dns_name, ip_addr, mac_addr, fio, username, os) 
                VALUES(?, ?, ?, ?, ?, ?, ?)''', (
                    data_from_f,))
        else:
            # Проверяем сколько записей в БД с таким маком как полученным из файла
            # Если записей больше чем одна,
            if (len(data_from_db) > 1):
                # то удаляем все старые записи и оставляем самую свежую
                clear_dublicate_mac(data_from_f[3])
            # Проверяем даты последнего апдейта и обновляем
            if (date_to_second(data_from_f[0]) > date_to_second(data_from_db[0][1])):
                print("Update - {} - {}".format(data_from_f, data_from_db[0][0]))
                update_data_to_db('''
                    UPDATE tb_mac_from_files 
                    SET date_from_file = ?, dns_name = ?, ip_addr = ?, mac_addr = ?, fio = ?, username = ?, os = ?
                    WHERE id_mac_from_file = ?''', (
                        data_from_f[0], data_from_f[1], data_from_f[2], data_from_f[3], data_from_f[4], data_from_f[5],
                        data_from_f[6], data_from_db[0][0]))

        clear_dublicate_mac(data_from_f[3])

    return 0


def clear_dublicate_mac(mac_addr):
    '''

    :param mac_addr:
    :return:
    '''
    # получаем из БД (tb_mac_from_files) строку содержащую mac-адрес из файла
    data_from_dbs = get_select_in_db_exp(
        "select * from tb_mac_from_files where mac_addr=:mac_addr",
        {"mac_addr": mac_addr, })
    tmp_date = '2000-01-01 00:00:01'
    tmp_id = 0
    if (len(data_from_dbs) > 1):
        for data_from_db in data_from_dbs:

            print(data_from_db)
            if (tmp_id != data_from_db[0]):
                if (date_to_second(tmp_date) < date_to_second(data_from_db[1])):
                    if (tmp_id != 0):
                        delete_data_from_db("tb_mac_from_files", "id_mac_from_file = " + str(tmp_id))
                        print("Delete - {} - {}".format(tmp_id, tmp_date))
                    tmp_id = data_from_db[0]
                    tmp_date = data_from_db[1]
                else:
                    delete_data_from_db("tb_mac_from_files", "id_mac_from_file = " + str(data_from_db[0]))
                    print("Delete - {} -  {}".format(data_from_db[0], data_from_db[1]))

        print("Result - {} - {}".format(tmp_id, tmp_date))
        print("\n")
    return 0


# ----------------------------------------------------------------------------------------------------------------------
# 3 Блок по записи данных о mac адресах с устройств cisco в БД


def update_desc_in_db(switch):
    '''
    обновление подписей в БД с коммутатора
    :return:
    '''
    # получаем данные о подписи портов на коммутаторах
    datas = sis_parser(switch[2])
    # обновляем подписи в БД
    for data in datas:
        update_data_to_db("UPDATE tb_desc_on_switches SET descs = ? WHERE id_switch = ? and port_name = ?",
                          (data[2], data[0], data[1]))
    return 0


def update_autodesc(switch):
    '''
    !!! New
    Функция проверяющая корректность ключа поля auto_descs в таблице tb_desc_on_switches
    '''
    # обновляем подписи на коммутаторе
    update_desc_in_db(switch)
    # Получаем строки подписей на текущем коммутаторе из БД
    lports = get_select_in_db_exp('''
        SELECT *
        FROM tb_desc_on_switches
        WHERE id_switch = :switch_id
        ''', {"switch_id": switch[0], })

    if (lports is not None):
        # !!! Этот блок можно переписать и справочные слова брать из БД
        # для каждой строки проверяем описание и если в нем встречаются знакомые слова, то
        for lport in lports:
            # в этом случае ставим флаг auto_descs = 1
            lallows = get_select_in_db_ex("SELECT * FROM tb_auto_desc_allow")
            ldenys = get_select_in_db_ex("SELECT * FROM tb_auto_desc_deny")
            flag = -1
            for lallow in lallows:
                if (lport[3].lower().find(lallow[0]) != -1):
                    flag = 1
            for ldeny in ldenys:
                if (lport[3].lower().find(ldeny[0]) != -1):
                    flag = 0
            if (flag != -1):
                update_data_to_db("UPDATE tb_desc_on_switches SET auto_descs = ? WHERE id_desc_on_switch = ?",
                                  (flag, lport[0]))

    else:
        print("Что-то явно пошло не так как задумывалось в функции update_autodesc")
    # return ничего не делает
    return 0


def set_new_desc_to_db():
    '''

    :return:
    '''
    print("switches = ", sw_list)

    # для каждого коммутатора
    for switch in sw_list:
        # запрашиваем в БД список портов, которые можно подписывать
        lports = get_select_in_db_exp('''
            SELECT *
            FROM tb_desc_on_switches
            WHERE id_switch = :switch_id AND
                auto_desc = 1
            ''', {"switch_id": switch[0], })
        print("\nswitch = ", switch)

        # Если записей в БД о портах которые можно подписывать нет,
        if (lports is None):
            # то проверяем есть ли записи о портах этого коммутатора вообще	в БД
            tports = get_select_in_db_exp('''
                SELECT *
                FROM tb_desc_on_switches
                WHERE id_switch = :switch_id
                ''', {"switch_id": switch[0], })

            # Если записей о портах этого коммутатора нет в БД, то
            if (tports is None):
                # считываем с коммутатора все строки по команде "sis" и
                # записываем в БД подписи с коммутаторов
                insert_data_to_db('''INSERT INTO tb_desc_on_switches (id_switch, port_name, descs, auto_desc)
                                  VALUES(?, ?, ?, ?)''', sis_parser(switch[2]))

        # Если записи в БД о портах которые можно подписать есть,
        else:
            # получаем данные с текущего коммутатора об активных mac адресах
            switch_datas = ssh_command(switch[2], 'show mac- | inc Fa0')

            # создаем массив с активными маками на портах, которые можно подписывать
            act_macs = []
            # пробегаемся по mac адресам
            for switch_data in switch_datas:
                print("switch_data - ", switch_data)
                # флаг - найден порт из списка активных маков среди разрешенных для подписи портов из БД
                flag = 0
                # если в списке мак таблицы есть порты, которые можно подписывать
                for lport in lports:
                    # сравниваем название портов, чтобы понять есть ли в списке порт для подписи
                    if (switch_data.split()[3] == lport[2]):
                        flag = 1
                # то добавляем в результирующую таблицу
                if (flag == 1):
                    act_macs.append(switch_data.split())
            print("act_macs = ", act_macs)
            # на выходе получаем массив act_macs =  [['254', '0011.2f38.7d84', 'DYNAMIC', 'Fa0/1'],
            # ['254', '001f.c689.7e49', 'DYNAMIC', 'Fa0/12']]
            # 21	5	00C0B79FC589	Fa0/15	254

            # c мак адресами и портами которые необходимо подписать
            for act_mac in act_macs:
                for lport in lports:
                    # ищем порт среди act_mac для того чтобы сравнить дескрипшин
                    if (act_mac[3] == lport[2]):
                        #
                        db_mac_sw = get_select_in_db_exp('''
                            SELECT *
                            FROM tb_mac_from_switches
                            WHERE mac_addr = :mac_addr
                            ''', {"mac_addr": get_win_mac(act_mac[1])})

                        # если данных о маке текущего порта есть,
                        if (db_mac_sw is not None):
                            # проверяем, что в базе такая запись есть и совпадает полностью
                            if not (get_win_mac(act_mac[1]) == db_mac_sw[0][2] and act_mac[3] == db_mac_sw[0][3]):
                                print("--------act_mac, db_mac_sw === {} == {}".format(act_mac, db_mac_sw))
                        # если данные о маке текущего порта отсутствуют
                        else:
                            del act_mac[2]
                            act_mac.insert(0, switch[0])
                            act_mac.insert(1, get_win_mac(act_mac[2]))
                            del act_mac[3]

                            print("Insert = ", act_mac)
                            update_data_to_db('''
                                INSERT INTO tb_mac_from_switches (id_switch, mac_addr, vlan, port_name) 
                                VALUES(?, ?, ?, ?)''',
                                              act_mac)

        # проверяем корректность
        update_autodesc(switch)


# ----------------------------------------------------------------------------------------------------------------------
# Попытка № 3

def sis_parser(ip_switch):
    datas = ssh_command(ip_switch, "sis")
    i = 0
    l = []
    for data in datas:
        port = data[0:10].strip(' ')
        # print (port.encode('ascii'))

        if port == "Port" or port == '\r\n':
            next
        else:
            l.append([])
            l[i].append(
                str(get_select_in_db_exp("SELECT id_switch FROM tb_switches WHERE ip_addr=?", (str(ip_switch),))[0][0]))
            l[i].append(data[0:10].strip(' '))
            # name = d[10:29].strip(' ')
            l[i].append(data[10:29].strip(' '))
            l[i].append("0")
            # status = d[29:42].strip(' ')
            # l[i].append(data[29:42].strip(' '))
            # vlan = d[42:53].strip(' ')
            # l[i].append(data[42:53].strip(' '))
            # duplex = d[53:60].strip(' ')
            # l[i].append(data[53:60].strip(' '))
            # speed = d[60:67].strip(' ')
            # l[i].append(data[60:67].strip(' '))
            # type_p = d[67:].strip(' ')
            # l[i].append(data[67:].strip(' '))
            # id_port_name = get_id_port_name(port)
            # l[i].append(get_id_host (ip_switch))
            # id_host = get_id_host (ip_switch)
            # print(l[i])
            # print (str(i) + " - " + port + "; id-port = " + str(id_port_name) + "; desc = " + name)
            i += 1
    return l


def update_desc_in_db2(switch):
    '''
    обновление подписей в БД с коммутатора
    :return:
    '''
    # получаем данные о подписи портов на коммутаторах
    datas = sis_parser(switch[2])
    # получаем данные о подписях в БД
    lports = get_select_in_db_exp('''
            SELECT *
            FROM tb_desc_on_switches
            WHERE id_switch = :switch_id
            ''', {"switch_id": switch[0], })
    # print("lports - ", lports)
    # если подписи портов есть в БД, то делаем обнолвение полей
    if len(lports) > 0:
        # обновляем подписи в БД
        for data in datas:
            update_data_to_db('''
                    UPDATE tb_desc_on_switches 
                    SET descs = ?, f_new_desc = ? 
                    WHERE id_switch = ? and port_name = ?''',
                             (data[2], "0", data[0], data[1]))
    else:
        # если подписи портов не записаны в БД, то вставляем новые строки
        insert_data_to_db('''INSERT INTO tb_desc_on_switches (id_switch, port_name, descs, auto_desc)
                                          VALUES(?, ?, ?, ?)''', sis_parser(switch[2]))
    return 0


def check_port_for_auto_desc():
    '''

    :param tlfi:
    :return:
    '''


    return 0


def update_mac_in_db(switch):
    '''

    :param switch:
    :return:
    '''
    # получаем данные с текущего коммутатора об активных mac адресах
    sw_lmacs = ssh_command(switch[2], 'show mac- | inc Fa0')
    # list for insert
    lfi = []


    for sw_lmac in sw_lmacs:
        # temp list for insert
        tlfi = []
        tlfi.append(switch[0])
        tlfi.append(get_win_mac(sw_lmac.split()[1]))
        tlfi.append(sw_lmac.split()[3])
        tlfi.append(sw_lmac.split()[0])
        tlfi.append("1")
        if check_port_for_auto_desc(tlfi):
            lfi.append(tlfi)

    print("lfi - ", lfi)

    # получаем данные из БД о имеющихся mac адресах
    db_lmacs = get_select_in_db_exp('''
            SELECT *
            FROM tb_mac_from_switches
            WHERE id_switch = :switch_id
            ''', {"switch_id": switch[0], })
    # print("db_lmacs - ", db_lmacs)
    return 0


def update_switch_data_in_db():
    '''
    Главная функция выполняющая все действия блока
    :return:
    '''
    # Пробегаемся по коммутаторам
    for switch in sw_list:
        print("\nswitch - ", switch)
        # Обновляем данные sis
        update_desc_in_db2(switch)
        # Обновляем данные sma
        update_mac_in_db(switch)

    return 0


# ----------------------------------------------------------------------------------------------------------------------
# 4 Блок по подготовке новых подписей для устройств 


def get_new_description_from_port(datas):
    '''
    функция получает массив списков по формату представления vw_summary
    и преобразовывает старые подписи в новые для дальнейшей записи их в БД
    data[1] - id_switch
    data[3] - имя порта (номер порта в формате Fa0/1)
    data[7] - текущая подпись порта
    data[11] - последнее название АРМ зарегистрированное с отображаемым мак адресом в папке transit
    data[18] - ip-адрес коммутатора
    data[19] - статус коммутатора (включен или выключен)
    data[20] - ключ по которому определяем можно производить автоподпись портов или нет
    '''
    i = 0
    # создаем список
    l = []

    # получаем список списков коммутаторов
    for data in datas:
        # print("{} - {}".format(data[20], data))
        # проверяем, что данный коммутатор можно подписывать автоматически
        if data[20]:

            # проверяем, что на порту нет надписи Хаб
            if data[7].lower().find('hub') < 0:
                # проверяем, что порт подписан в нужном формате с разделителем "|"
                # (<номер кабинета>-<номер розетки в помещении><L/R>|<АРМ>)
                if len(data[7].split('|')) > 1:
                    # проверяем что имя АРМ не совпадает и подписываем, иначе порт считаем подписанным верно
                    if data[7].split('|')[1] != data[11]:
                        room = data[7].split('|')[0] + '|' + data[11]
                    # иначе все подписано верно
                    else:
                        room = data[7]

                # если порт имеет произвольную подпись, то
                else:
                    # ищем совпадение по формату (r.303-1r Y)
                    result = re.findall(r'(\b[r](\b[\.])*\d{3}(\b[-]\d{1})*([r|l|R|L])*([ Y])*)', data[7])
                    # Если нашли совпадение по формату, то
                    if len(result):
                        # приводим номер помещение к общему виду
                        room = result[0][0].lstrip('r').strip().strip('.').upper()
                        # если помещение не дописано и имеет только 3 цифры, то
                        if len(room) <= 3:
                            # дописываем -??, что бы получить общий вормат
                            room = room + '-00'
                        # заносим данные в таблицу БД
                        room = room + '|' + str(data[11])

                    # если совпадение по формату не нейдено
                    else:
                        # ищем более свежий формат состоящий из 3х первых цифр
                        result = re.findall(r'(\d{3}\b[-]\d{1}[r|l|R|L])+(\b[./]\d{1})*', data[7])
                        # проверяем, что нашли новый формат
                        if len(result):
                            # состоит он только из цифр
                            if len(result[0][0]) > 0:
                                room = result[0][0]
                            # или ему еще можно подписать номер розетки
                            if len(result[0][1]) > 0:
                                room = room + str(result[0][1])
                            # заносим данные в таблицу БД
                            room = room + '|' + str(data[11])
                        # если ничего не нашли по номерам помещений то вносим формат из нулей
                        else:
                            # заносим данные в таблицу БД
                            room = '000-00|' + str(data[11])
            # если хаб присутствует, то
            else:
                # текущую подпись порта переводим в верхний регистр
                room = data[7].upper()

            # создаем внутри списка вложенные списки со строками
            l.append([])
            # id_switch
            l[i].append(data[1])
            # имя порта который мы хотим подписать
            l[i].append(data[3])
            # ip-адрес коммутатора
            l[i].append(data[18])
            # статус коммутатора (включен или выключен)
            # l[i].append(data[19])
            # ключ по которому определяем можно производить автоподпись портов или нет
            # l[i].append(data[20])
            # новая подпись
            l[i].append(room)
            i += 1

    return l


# ----------------------------------------------------------------------------------------------------------------------
# 5 Блок по внесению новых подписей на коммутаторы

def put_new_descr_switch():
    '''
    Функция проверяет таблицу tb_new_desc на наличие новых подписей коммутаторов
    и вносит изменения в коммутатор
    '''
    # получаем список коммутаторов
    datas = get_select_in_db_ex('''
        SELECT id_switch, ip_addr, count(id_switch) 
        FROM tb_new_desc
        GROUP BY id_switch''')

    for data in datas:
        print("\n---" + str(data) + "---")
        ssh_commands(data[1], get_commond_line(data))


def get_commond_line(switch):
    '''
    Функция подготавливает массив комманд для конкретного коммутатора
    '''
    qs = get_select_in_db_exp('''
        SELECT *, count(port_name) 
        FROM tb_new_desc 
        WHERE id_switch=? 
        GROUP BY id_switch, port_name''', (switch[0],))
    print("qs - {}".format(qs))
    l = []
    l.append("conf ter")
    for q in qs:

        if q[6] < 2:
            l.append("int " + q[2])
            l.append("desc " + q[4])
            l.append("exit")
    if len(l) > 1:
        l.append("exit")
        l.append("wr")
        l.append("exit")

    # очищаем БД от записей, которые передаем на подпись коммутаторов
    for q in qs:
        print("Удаляем строку - {}".format(q))
        update_data_to_db("UPDATE tb_new_desc SET f_new_desc = ? WHERE id_new_desc = ?", ("1", q[0]))
        # delete_data_from_db("tb_new_desc", "id_new_desc = " + str(q[0]))
    return l



# ----------------------------------------------------------------------------------------------------------------------
# -------------------------------------------------------MAIN
# ----------------------------------------------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------------------------------------------
# 1--- Блок по сканированию сети и записи IP адресов cisco в БД
print(" - Сканирую подсеть " + str(ip_range))

# получаем список ip-адресов доступных по ICMP из диапазона ip_range
ip_range_online = my_ping(ip_range)

# отсеиваем все устройства, кроме cisco
ip_cisco_online = find_cisco_ip(ip_range_online)

# записываем в БД все IP адреса устройств, которые отозвались как cisco
insert_ip_cisco_in_db(ip_cisco_online)


# получаем список коммутаторов с которыми в дальнейшем будем работать
print("Получаем из БД список коммутаторов с которыми будем работать ")
# sw_list = get_select_in_db_ex("SELECT * FROM tb_switches WHERE status = 1 and auto_desc = 1")
sw_list = get_select_in_db_ex("SELECT * FROM tb_switches WHERE status = 1 and auto_desc = 1 and id_switch = 2")
print(sw_list)
ltada = get_select_in_db_ex("SELECT * FROM tb_auto_desc_allow")
ltadd = get_select_in_db_ex("SELECT * FROM tb_auto_desc_deny")

# ----------------------------------------------------------------------------------------------------------------------
# 2--- Блок по записи данных о mac адресах, из лог файлов входа в систему, в БД
# print("\n --- Модуль 2 - считывание лог файлов")
# print(" - Сканирую файлы логов из папки " + str(dirName))
# set_datas_from_file()

# Обновление учетных данных коммутатора (серийный номер, имя, версия прошивки)
# insert_cisco_sign_db()

# ----------------------------------------------------------------------------------------------------------------------
# 3--- Блок по считыванию подписей и mac адресов с портов cisco в БД
print("\n --- Модуль 3 - считывание подписей и mac адресов")

# Считываем данные с коммутаторов и обновляем подписи портов в БД.
update_switch_data_in_db()


# -----------------------------------------------
# set_new_desc_to_db()

# ----------------------------------------------------------------------------------------------------------------------
# 4--- Блок по сравнению данных в БД о подписях устройств и внесение новых подписей
# print("\n --- Модуль 4 - подготовка данных для подписи портов на коммутатороах")

# datas = get_new_description_from_port(get_select_in_db_ex("SELECT * FROM vw_summary"))

# insert_data_to_db("INSERT INTO tb_new_desc (id_switch, port_name, ip_addr, descs) VALUES(?, ?, ?, ?)", datas)

# Чистим дубли по подписям портов
# set_query_for_db(
'''
delete
from tb_new_desc 
where id_new_desc in (
    SELECT id_new_desc
    FROM vw_dup_desc
)
'''
# )

# ----------------------------------------------------------------------------------------------------------------------
# 5--- Блок по внесению новых подписей на коммутаторы
# print("\n --- Модуль 5 - подпись портов коммутаторов")
# put_new_descr_switch()
