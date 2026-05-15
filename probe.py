import socket

def test_connection():
    print("DEBUG: Starting probe from Render...")
    s = socket.socket()
    s.settimeout(5)
    try:
        print("DEBUG: Attempting to connect to 154.243.246.172:21")
        s.connect(("154.243.246.172", 21))
        print("SUCCESS: Connected from Render to Win10 vault!")
    except Exception as e:
        print("ERROR: Connection failed ->", e)
    finally:
        s.close()
        print("DEBUG: Socket closed, probe finished.")

if __name__ == "__main__":
    print("DEBUG: Probe script launched.")
    test_connection()
