import json
import urllib.request
import urllib.error


BASE = "http://127.0.0.1:5000"


def post(path: str, body: dict, token: str | None = None):
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw}


def main():
    status, data = post("/api/auth/login", {"email": "ostiadedo456@gmail.com", "password": "12345678"})
    print("LOGIN", status, data)
    token = data.get("access_token")

    status, gen = post(
        "/api/exercises/generate",
        {"module": "dynamical_systems", "type": "ode", "difficulty": 1},
        token,
    )
    print("GENERATE", status, gen)
    ex_id = gen["exercise"]["id"]

    status, sub = post(
        f"/api/exercises/{ex_id}/submit",
        {"answer": 1.0, "time_spent": 3},
        token,
    )
    print("SUBMIT", status, sub)


if __name__ == "__main__":
    main()

