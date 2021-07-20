import socket
import subprocess
import ipaddress
import sqlite3
import paramiko
import time

import os
import re


# имя БД 
db_name = "desc.db"
# пользователь для подключения по ssh
usr = 'someuser'
# пароль для подключения по ssh
pwd = open('pwd.txt', 'r').read()
# порт для подключения по ssh
port = 22


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


def get_select_in_DB_ex (query):
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


def main():
	# Получаем список коммутаторов для backup
	switches = get_select_in_DB_ex("SELECT id_switch, ip_addr FROM tb_switches")
	print("switches = ", switches)

	for switch in switches:
		print("Сохраняем кофигурацию коммутатора - ", switch[1])
		f = open('d:\\cisco\\' + switch[1] + '.conf', 'w')

		for str_conf in ssh_command (switch[1], "sh run"):
			f.write(str_conf)


if __name__ == '__main__':
	main()
