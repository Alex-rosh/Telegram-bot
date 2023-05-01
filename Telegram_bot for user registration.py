import telebot
import psycopg2
from datetime import datetime
import hashlib

# создаем подключение к базе данных PostgreSQL
conn = psycopg2.connect(
    dbname="your_database",
    user="your_username",
    password="your_password",
    host="localhost",
    port="5432"
)

# создаем курсор для работы с базой данных
cur = conn.cursor()

# создаем таблицу в базе данных для хранения информации о пользователях
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    full_name TEXT,
    birthday DATE,
    gender TEXT,
    city TEXT,
    email TEXT,
    encrypt_password VARCHAR(255),
    password TEXT
);
""")

# сохраняем изменения в базе данных
conn.commit()

# создаем объект чат-бота
bot = telebot.TeleBot("TOKEN")



key_main = 'registration'.encode('utf-8')
key_hash = hashlib.sha256(key_main)
key_bytes = key_hash.digest()
key = str(key_bytes)


# функция для шифрования пароля
def encrypt_password(password: str, key: str) -> str:
    encrypted_password = ''
    for i in range(len(password)):
        key_c = key[i % len(key)]
        encrypted_c = chr(ord(password[i]) ^ ord(key_c))
        encrypted_password += encrypted_c
    return encrypted_password


# функция для расшифровки пароля
def decrypt_password(encrypted_password: str, key: str) -> str:
    decrypted_password = ''
    for i in range(len(encrypted_password)):
        key_c = key[i % len(key)]
        decrypted_c = chr(ord(encrypted_password[i]) ^ ord(key_c))
        decrypted_password += decrypted_c
    return decrypted_password


# функция для регистрации пользователя
@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1)
    registration_button = telebot.types.KeyboardButton('Зарегистрироваться')
    login_button = telebot.types.KeyboardButton('Войти в личный кабинет')
    markup.add(registration_button, login_button)
    bot.send_message(message.chat.id, 'Выберите действие', reply_markup=markup)


# функция для ввода ФИО
@bot.message_handler(func=lambda message: message.text == 'Зарегистрироваться')
def ask_full_name(message):
    bot.send_message(message.chat.id, 'Введите ФИО')
    bot.register_next_step_handler(message, ask_birthday)

# функция для ввода даты рождения
def ask_birthday(message):
    full_name = message.text
    bot.send_message(message.chat.id, 'Введите дату рождения в формате дд.мм.гггг')
    bot.register_next_step_handler(message, ask_gender, full_name)
    return full_name

# функция для ввода пола
def ask_gender(message, full_name):
    try:
        birthday = message.text
        birthday = datetime.strptime(birthday, '%d.%m.%Y').date()
        bot.send_message(message.chat.id, 'Введите пол')
        bot.register_next_step_handler(message, ask_city, full_name, birthday)
    except ValueError:
        bot.send_message(message.chat.id, 'Неверный формат даты. Попробуйте еще раз.')
        bot.register_next_step_handler(message, ask_birthday)


# функция для ввода города
def ask_city(message, full_name, birthday):
    gender = message.text
    bot.send_message(message.chat.id, 'Введите город')
    bot.register_next_step_handler(message, ask_email, full_name, birthday, gender)
    return gender

# функция для ввода email
def ask_email(message, full_name, birthday, gender):
    city = message.text
    bot.send_message(message.chat.id, 'Введите email')
    bot.register_next_step_handler(message, ask_password, full_name, birthday, gender, city)
    return city

# функция для ввода пароля
def ask_password(message, full_name, birthday, gender, city):
    email = message.text
    bot.send_message(message.chat.id, 'Введите пароль')
    bot.register_next_step_handler(message, ask_confirmation_password, full_name, birthday, gender, city, email)
    return email

def ask_confirmation_password(message, full_name, birthday, gender, city, email):
    password = message.text
    bot.send_message(message.chat.id, 'Подтвердите пароль')
    bot.register_next_step_handler(message, save_user_data, full_name, birthday, gender, city, email, password)
    return password

def save_user_data(message, full_name, birthday, gender, city, email, password):
    confirmation_password = message.text
    if password != confirmation_password:
        bot.send_message(message.chat.id, 'Пароли не совпадают. Попробуйте еще раз.')
        bot.register_next_step_handler(message, ask_confirmation_password(message, full_name, birthday, gender, city, email))
    else:
        encrypted_password = encrypt_password(password, key)
        cur.execute("INSERT INTO users (full_name, birthday, gender, city, email, encrypt_password, password) VALUES (%s, %s, %s, %s, %s, %s, %s);", (full_name, birthday, gender, city, email, encrypted_password, password))
        conn.commit()
        bot.send_message(message.chat.id, 'Вы успешно зарегистрированы и можете войти в личный кабинет')

@bot.message_handler(func=lambda message: message.text == 'Войти в личный кабинет')
def login(message):
    bot.send_message(message.chat.id, 'Введите email')
    bot.register_next_step_handler(message, check_email)

def check_email(message):
    email = message.text
    if email == 'admin':
        user_data=[]
        bot.send_message(message.chat.id, 'Введите пароль администратора')
        bot.register_next_step_handler(message, check_password, user_data)
    else:
        cur.execute("SELECT * FROM users WHERE email=%s;", (email,))
        user_data = cur.fetchone()
        if user_data is None:
            bot.send_message(message.chat.id, 'Пользователь с таким email не найден. Попробуйте еще раз.')
            bot.register_next_step_handler(message, check_email)
        else:
            bot.send_message(message.chat.id, 'Введите пароль')
            bot.register_next_step_handler(message, check_password, user_data)

def check_password(message, user_data):
    password = message.text
    chat_id = message.chat.id
    if password == 'admin':
        try:
            cur.execute("SELECT * FROM users;")
            rows = cur.fetchall()
            with open("users_db.txt", "w") as f:
                for row in rows:
                    f.write(f"{row[0]}: {row[1]} {row[2]} {row[3]} {row[4]} {row[5]} {row[7]}\n")
            print("Users database exported successfully.")
        except Exception as e:
            print(f"Error exporting users database: {e}")
        finally:
            cur.close()
        with open('users_db.txt', 'rb') as f:
            bot.send_document(chat_id, f)
    else:
        encrypted_password = user_data[6]
        if password == decrypt_password(encrypted_password, key):
            bot.send_message(message.chat.id, 'Добро пожаловать в личный кабинет')
        else:
            bot.send_message(message.chat.id, 'Неверный пароль. Попробуйте еще раз.')
            bot.register_next_step_handler(message, check_password, user_data)

bot.polling()