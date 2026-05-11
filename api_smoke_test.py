import json
import urllib.request

BASE = "http://127.0.0.1:5000"


def post(path, body, token=None):
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers)
    with urllib.request.urlopen(req) as res:
        return res.status, json.loads(res.read().decode("utf-8"))


def main():
    # login
    status, data = post(
        "/api/auth/login",
        {"email": "ostiadedo456@gmail.com", "password": "12345678"},
    )
    print("LOGIN", status, "user" in data, "access_token" in data)
    token = data["access_token"]

    # dynamical systems
    status, data = post(
        "/api/dynamical-systems/simulate",
        {"system": "harmonic_oscillator"},
        token,
    )
    print("DS_SIM", status, "t" in data, "solution" in data)

    # numerical methods
    status, data = post(
        "/api/numerical-methods/solve",
        {"method": "runge_kutta_4", "function": "-y + sin(t)"},
        token,
    )
    print("NM_SOLVE", status, "t" in data, "y" in data)

    # exercises - dynamical systems ODE
    status, data = post(
        "/api/exercises/generate",
        {"module": "dynamical_systems", "type": "ode", "difficulty": 1},
        token,
    )
    print("EX_GEN_DS_ODE", status, "exercise" in data, data)


if __name__ == "__main__":
    main()

