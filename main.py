import hmac
import hashlib
import os
import asyncio
from flask import Flask, request, jsonify
from telegram import Bot

# ---------------- CONFIG ----------------
TOKEN = os.environ.get("TG_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "600440574")

app = Flask(__name__)
bot = Bot(token=TOKEN)

# ---------------- PARSER ----------------
def parse_helius_tx(tx):
    try:
        type_ = tx.get("type", "")
        source = tx.get("source", "")
        sig = tx.get("signature", "")
        token_transfers = tx.get("tokenTransfers", [])
        native_transfers = tx.get("nativeTransfers", [])

        results = []

        if token_transfers:
            for transfer in token_transfers:
                mint = transfer.get("mint", "unknown")
                amount = transfer.get("tokenAmount", 0)
                from_addr = transfer.get("fromUserAccount", "")

                sol_spent = 0
                for nt in native_transfers:
                    if nt.get("fromUserAccount") == from_addr:
                        sol_spent = nt.get("amount", 0) / 1e9

                results.append({
                    "type": type_,
                    "source": source,
                    "mint": mint,
                    "amount": amount,
                    "sol": sol_spent,
                    "sig": sig,
                    "from": from_addr,
                })
        return results
    except Exception as e:
        print("Parse error:", e)
        return []

def format_message(parsed, sig):
    direction = "📈 BUY" if parsed.get("sol", 0) > 0 else "📤 TRANSFER"
    msg = f"🔥 *ТРАНЗАКЦІЯ ВИЯВЛЕНА*\n\n"
    msg += f"Тип: {direction}\n"
    msg += f"Джерело: {parsed.get('source', 'unknown')}\n"
    msg += f"Token: `{parsed.get('mint', 'unknown')}`\n"
    msg += f"Кількість: {parsed.get('amount', 0)}\n"
    if parsed.get("sol"):
        msg += f"SOL витрачено: {parsed['sol']:.4f}\n"
    msg += f"\n[Дивитись на Solscan](https://solscan.io/tx/{sig})"
    return msg

# ---------------- WEBHOOK ----------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400

    transactions = data if isinstance(data, list) else [data]

    for tx in transactions:
        sig = tx.get("signature", "unknown")
        parsed_list = parse_helius_tx(tx)

        if parsed_list:
            for parsed in parsed_list:
                msg = format_message(parsed, sig)
                asyncio.run(bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown"))
        else:
            asyncio.run(bot.send_message(
                chat_id=CHAT_ID,
                text=f"⚡ Нова транзакція:\n[{sig[:20]}...](https://solscan.io/tx/{sig})",
                parse_mode="Markdown"
            ))

    return jsonify({"ok": True})

@app.route("/", methods=["GET"])
@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🟢 Bot running on port {port}")
    app.run(host="0.0.0.0", port=port)
