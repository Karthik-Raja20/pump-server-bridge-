from flask import Flask, request, Response

app = Flask(__name__)

# The "mailbox" — always holds ONLY the latest packet.
# A new POST always overwrites this, nothing is ever kept beyond the last one.
latest_packet = ""


@app.route("/")
def home():
    return "Server is running. POST to /data to send data, GET /data to read the latest packet."


@app.route("/data", methods=["POST"])
def receive_data():
    global latest_packet
    latest_packet = request.get_data(as_text=True)
    return {"status": "ok", "received_length": len(latest_packet)}, 200


@app.route("/data", methods=["GET"])
def send_data():
    return Response(latest_packet, mimetype="text/plain")


if __name__ == "__main__":
    # Local testing: runs on http://localhost:5000
    app.run(host="0.0.0.0", port=5000)
