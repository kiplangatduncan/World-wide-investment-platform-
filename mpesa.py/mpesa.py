from flask import request, jsonify


def register_mpesa_routes(app):

    @app.route("/mpesa", methods=["GET"])
    def mpesa_home():
        return jsonify({
            "success": True,
            "message": "M-Pesa module is working"
        })

    @app.route("/mpesa/callback", methods=["POST"])
    def mpesa_callback():
        data = request.get_json(silent=True) or {}

        print("M-Pesa callback received:")
        print(data)

        return jsonify({
            "ResultCode": 0,
            "ResultDesc": "Accepted"
        })
