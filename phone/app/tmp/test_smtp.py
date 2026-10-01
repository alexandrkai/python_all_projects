import smtplib

server = smtplib.SMTP("192.168.1.222", 587)
server.starttls()
server.login("info@pulsesms.ru", "291297")
print("Успешная авторизация!")
server.quit()
pass