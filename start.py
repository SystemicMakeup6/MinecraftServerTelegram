import re
import subprocess
import threading
import telebot
from queue import Queue

bot = telebot.TeleBot("")
#вставьте токен своего тг бота
CHAT_ID = 
#вставьте свой id в тг
JAVA_COMMAND = "java -Xmx4G -Xms1G -jar server.jar"
#вставьте параменты запуска вашего сервера
process = None
command_queue = Queue()

def update_bot_status(is_running: bool):
    """Обновляет статус (био) бота в Telegram"""
    status = "🟢 Сервер работает 🟢" if is_running else "🔴 Сервер выключен 🔴"
    try:
        bot.set_my_short_description(status)
    except Exception as e:
        log_output(f"Ошибка обновления статуса: {e}")

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def log_output(message):
    message = strip_ansi(message)
    print(message)
    try: 
        bot.send_message(CHAT_ID, message)
    except Exception as e: 
        print(f"Ошибка отправки в Telegram: {e}")

def read_process_output(process):
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None: 
            break
        if output: 
            log_output(output.strip())

def process_command(command):
    if process and process.poll() is None:
        try:
            process.stdin.write(f"{command}\n")
            process.stdin.flush()
        except Exception as e: 
            log_output(f"Ошибка выполнения команды: {command}\n{str(e)}")

def start_server():
    global process
    try:
        update_bot_status(False)
        process = subprocess.Popen(
            JAVA_COMMAND.split(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            text=True
        )
        update_bot_status(True)
        
        threading.Thread(target=read_process_output, args=(process,), daemon=True).start()
        process.wait()
    except Exception as e: 
        log_output(f"Ошибка при запуске сервера: {e}")
        update_bot_status(False)
    finally: 
        update_bot_status(False)
        process = None

def console_input_handler():
    while True:
        try:
            command = input()
            if command.lower() in ('exit', 'quit'):
                if process and process.poll() is None:
                    process.terminate()
                break
            command_queue.put(command)
        except (EOFError, KeyboardInterrupt): 
            break

@bot.message_handler(func=lambda message: message.chat.id == CHAT_ID)
def handle_telegram_message(message):
    command_queue.put(message.text)

if __name__ == "__main__":
    update_bot_status(False)
    
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    console_thread = threading.Thread(target=console_input_handler, daemon=True)
    console_thread.start()
    
    def command_processor():
        while True:
            command = command_queue.get()
            process_command(command)
            command_queue.task_done()
    
    processor_thread = threading.Thread(target=command_processor, daemon=True)
    processor_thread.start()
    
    try: 
        bot.infinity_polling()
    except Exception as e: 
        log_output(f"Ошибка в работе бота: {e}")
    finally:
        if process and process.poll() is None:
            process.terminate()
        update_bot_status(False)

