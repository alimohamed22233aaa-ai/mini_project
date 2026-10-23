from flask import Flask, jsonify

app = Flask(__name__)

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Flask App</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      background: linear-gradient(135deg, #4f46e5, #0ea5e9);
      color: #0f172a;
      padding: 1rem;
    }
    .card {
      background: #fff;
      border-radius: 20px;
      padding: 3rem 2.5rem;
      max-width: 440px;
      width: 100%;
      text-align: center;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.25);
    }
    .emoji { font-size: 3rem; margin-bottom: 1rem; }
    h1 { font-size: 1.8rem; margin-bottom: 0.5rem; }
    p { color: #475569; margin-bottom: 1.5rem; }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.4rem 1rem;
      border-radius: 999px;
      background: #f1f5f9;
      font-size: 0.9rem;
      font-weight: 600;
    }
    .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #94a3b8;
    }
    .dot.ok { background: #22c55e; animation: pulse 1.8s infinite; }
    .dot.fail { background: #ef4444; }
    @keyframes pulse {
      0%   { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.6); }
      70%  { box-shadow: 0 0 0 10px rgba(34, 197, 94, 0); }
      100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
    }
    a {
      display: inline-block;
      margin-top: 1.5rem;
      color: #4f46e5;
      font-size: 0.9rem;
      text-decoration: none;
    }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <main class="card">
    <div class="emoji">🚀</div>
    <h1>Hello from Flask!</h1>
    <p>Your app is deployed and running.</p>
    <div class="status">
      <span class="dot" id="dot"></span>
      <span id="label">Checking...</span>
    </div>
    <br>
    <a href="/health">View health endpoint</a>
  </main>
  <script>
    fetch("/health")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        document.getElementById("dot").className = "dot ok";
        document.getElementById("label").textContent = "Status: " + d.status;
      })
      .catch(function () {
        document.getElementById("dot").className = "dot fail";
        document.getElementById("label").textContent = "Service unavailable";
      });
  </script>
</body>
</html>"""


@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok"), 200


@app.route("/", methods=["GET"])
def index():
    return PAGE, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)