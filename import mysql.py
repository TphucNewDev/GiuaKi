import mysql.connector
from mysql.connector import errorcode

config = {
    'user': 'root',
    'password': '123456',
    'host': 'localhost',
}

#Connect to MySQL
try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    print("Connect MySQL Server successful!")
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Connect error, please check your username/password.")
    else:
        print(err)