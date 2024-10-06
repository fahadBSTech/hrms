import firebase_admin
from firebase_admin import credentials, messaging
import os

current_dir = os.path.dirname(os.path.abspath(__file__))

        # Construct the path to the credentials file
cred_path = os.path.join(current_dir, "firebase.json")

if os.path.isfile(cred_path):
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

def send_push_notification(token, title=None, body=None, log=None):
    if log:
        title, message = get_message_text(log)
    # Create the message
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=message
        ),
        tokens=token
    )

    # Send the message
    response = messaging.send_multicast(message)
    print("Push Notification sent Successfully")

def get_message_text(log):
    title = message = None
    if log.lower() == "in":
        title = "Don’t Forget to Check In!"
        message = "Good morning! Please remember to check in for your shift. Have a productive day!"
    elif log.lower() == "out":
        title = "Time to Check Out!"
        message = "Your shift is almost over. Please remember to check out. Have a great evening!"

    return title, message
