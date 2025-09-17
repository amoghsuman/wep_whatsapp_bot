from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd

app = Flask(__name__)

# Load scheme CSV
schemes = pd.read_csv("wep_sample_schemes.csv")

# Store user states in-memory (simple for demo)
user_states = {}

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    from_number = request.values.get("From", "")

    resp = MessagingResponse()
    msg = resp.message()

    # Initialize state for new user
    if from_number not in user_states:
        user_states[from_number] = {"step": "start"}
        msg.body("नमस्ते 👋 Welcome to WEP Bot!\nShall we find schemes for you? (Yes/No)")
        return str(resp)

    state = user_states[from_number]

    # Flow
    if state["step"] == "start":
        if incoming_msg.lower() in ["yes", "हाँ", "haan"]:
            state["step"] = "sector"
            msg.body("Great! कृपया अपना सेक्टर बताएं:\n1. Food Processing\n2. Handicrafts\n3. Services\n4. Others")
        else:
            msg.body("ठीक है। जब तैयार हों, 'Yes' लिखें।")

    elif state["step"] == "sector":
        state["sector"] = incoming_msg
        state["step"] = "age"
        msg.body("आपका व्यवसाय कितने साल पुराना है?\n1. 1 साल से कम\n2. 1-3 साल\n3. 3+ साल")

    elif state["step"] == "age":
        state["age"] = incoming_msg
        state["step"] = "registered"
        msg.body("क्या आपका व्यवसाय पंजीकृत (GST/MSME) है? (Yes/No)")

    elif state["step"] == "registered":
        state["registered"] = incoming_msg
        state["step"] = "assistance"
        msg.body("आपको किस प्रकार की सहायता चाहिए?\n1. Loan\n2. Training\n3. Marketing\n4. Technology")

    elif state["step"] == "assistance":
        state["assistance"] = incoming_msg
        state["step"] = "done"

        # ---- Filtering Logic ----
        sector_map = {
            "1": "food",
            "2": "handicraft",
            "3": "services",
            "4": "general"
        }
        pillar_map = {
            "1": "Access to finance",
            "2": "Skill development",
            "3": "Marketing assistance",
            "4": "Technology"
        }

        sector = sector_map.get(state["sector"], "general")
        assistance = pillar_map.get(state["assistance"], "general")
        registered = state["registered"].lower() in ["yes", "हाँ"]

        # Filter schemes by assistance pillar
        filtered = schemes[schemes["pillar"].str.contains(assistance, case=False, na=False)]

        # Sector keyword match
        if sector != "general":
            filtered = filtered[filtered["eligibility_summary"].str.contains(sector, case=False, na=False)]

        # Registration filter (basic check)
        if not registered:
            filtered = filtered[filtered["eligibility_summary"].str.contains("unregistered|informal", case=False, na=False)]

        # Fallback
        if len(filtered) < 3:
            filtered = schemes.sample(3)

        # Build reply
        reply = "आपके प्रोफ़ाइल के आधार पर ये योजनाएँ उपयुक्त हैं:\n\n"
        for i, row in filtered.head(3).iterrows():
            reply += f"{i+1}️⃣ {row['scheme_name']} ({row['benefit_summary']})\n👉 Apply: {row['application_url']}\nDocs: {row['required_documents']}\n\n"

        msg.body(reply)

    else:
        msg.body("Demo end ✅. Type 'Hi' to restart.")

    return str(resp)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
