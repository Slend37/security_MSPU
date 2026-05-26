import requests

BASE_URL = "http://127.0.0.1:8000"

def test_idor():
    session = requests.Session()

    response = session.post(f"{BASE_URL}/set-session", params={"name": "Alice"})
    if response.status_code != 200:
        return False

    response = session.get(f"{BASE_URL}/files/1")

    if response.status_code == 403:
        return True
    else:
        return False

def test_access():
    session = requests.Session()

    response = session.post(f"{BASE_URL}/set-session", params={"name": "Alice"})
    if response.status_code != 200:
        return False

    response = session.get(f"{BASE_URL}/files/2")

    if response.status_code == 200:
        return True
    else:
        return False

def test_admin_delete():
    session_bob = requests.Session()
    response = session_bob.post(f"{BASE_URL}/set-session", params={"name": "Bob"})

    response = session_bob.get(f"{BASE_URL}/files/1")

    if response.status_code != 200:
        return False

    session_admin = requests.Session()
    response = session_admin.post(f"{BASE_URL}/set-session", params={"name": "Admin"})

    if response.status_code != 200:
        return False

    response = session_admin.delete(f"{BASE_URL}/files/1")

    if response.status_code != 200:
        return False

    response = session_admin.get(f"{BASE_URL}/files/1")

    if response.status_code == 404:
        return True
    else:
        return False

if __name__ == "__main__":
    results = []

    results.append(test_idor())
    results.append(test_access())
    results.append(test_admin_delete())

    print(f"Test 1 (IDOR - Alice пытается получить файл Bob): {'PASSED' if results[0] else 'FAILED'}")
    print(f"Test 2 (Access - Alice получает свой файл): {'PASSED' if results[1] else 'FAILED'}")
    print(f"Test 3 (Admin - удаляет файл Bob): {'PASSED' if results[2] else 'FAILED'}")

    if all(results):
        print("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    else:
        print("НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
