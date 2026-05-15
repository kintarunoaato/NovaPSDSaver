import socket

def test_connection():
    s = socket.socket()
    s.settimeout(5)
    try:
        s.connect(("154.243.246.172", 21))  # Win10 public IP + FTP port
        print("Connected from Render!")
    except Exception as e:
        print("Failed:", e)
    finally:
        s.close()

if __name__ == "__main__":
    test_connection()
