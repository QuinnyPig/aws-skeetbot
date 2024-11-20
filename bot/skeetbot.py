from atproto import Client
import os

USERNAME = os.getenv("SKEETBOT_USERNAME", "skeetbot")
APP_PASSWORD = os.getenv("SKEETBOT_PASSWORD", "password")

client = Client()
print(USERNAME, APP_PASSWORD)
client.login(USERNAME, APP_PASSWORD)

post = client.send_post('Hello world! This is gonna be noisy as all get-out, so you might wanna wait until the bot works.')