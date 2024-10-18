import asyncio
import websockets
import json
import sqlite3

# Veritabanı bağlantısı ve tablo oluşturma
def create_db():
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT,
        recipient TEXT,
        content TEXT
    )''')
    conn.commit()
    conn.close()

create_db()

connected_clients = {}

async def handler(websocket, path):
    username = None
    try:
        async for message in websocket:
            data = json.loads(message)
            print("Received message:", data)  # Hata ayıklama için gelen mesajı yazdır

            if data['type'] == 'setUsername':
                username = data['username']
                connected_clients[websocket] = username
                await send_user_list()

            elif data['type'] == 'message':
                recipient = data['to']
                content = data['content']
                save_message(username, recipient, content)
                await send_message_to_recipient(recipient, username, content)

            elif data['type'] == 'getChatHistory':
                recipient = data['to']
                messages = get_chat_history(username, recipient)
                await websocket.send(json.dumps({"type": "chatHistory", "messages": messages}))

            elif data['type'] == 'markAsRead':  # Mesaj okundu olarak işaretleme
                recipient = data['to']
                await mark_messages_as_read(username, recipient)

            elif data['type'] == 'deleteMessage':  # Mesaj silme
                message_id = data['message_id']
                await delete_message(message_id)

    finally:
        if websocket in connected_clients:
            del connected_clients[websocket]
            await send_user_list()

async def send_user_list():
    users = list(connected_clients.values())
    message = json.dumps({"type": "userList", "users": users})
    for websocket in connected_clients.keys():
        await websocket.send(message)

async def send_message_to_recipient(recipient, sender, content):
    for websocket, username in connected_clients.items():
        if username == recipient:
            await websocket.send(json.dumps({"type": "message", "username": sender, "content": content}))

def save_message(sender, recipient, content):
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (sender, recipient, content) VALUES (?, ?, ?)', (sender, recipient, content))
    conn.commit()
    conn.close()

def get_chat_history(username, recipient):
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, sender, content FROM messages WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?) ORDER BY ROWID',
                   (username, recipient, recipient, username))  # Mesajları sırayla al
    messages = cursor.fetchall()
    conn.close()
    return [{"id": msg[0], "username": msg[1], "content": msg[2]} for msg in messages]

async def mark_messages_as_read(username, recipient):
    # Mesajın görüldüğü bilgisini burada işleyebilirsiniz.
    # Örneğin, belirli bir kullanıcıya ait mesajları işaretlemek için bir mekanizma ekleyebilirsiniz.
    pass

async def delete_message(message_id):
    conn = sqlite3.connect('chat.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages WHERE id = ?', (message_id,))
    conn.commit()
    conn.close()

start_server = websockets.serve(handler, "localhost", 8000)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
