from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import csv

app = Flask(__name__)

# Load schemes using csv.DictReader (no pandas)
SCHEMES_CSV = "wep_sample_schemes.csv"
schemes = []
with open(SCHEMES_CSV, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        schemes.append(row)

# Helper: simple filter function (case-insensitive substring match)
def contains_any(text, keyword):
    try:
        return keyword.lower() in (text or "").lower()
    except:
        return False

# Simple ranking: digitized first, same-state boost if needed, then last_updated
def rank_and_pick(filtered_list, top_n=3):
    # ensure we have consistent keys
    for r in filtered_list:
        r.setdefault("digitized (yes/no)", "no")
        r.setdefault("last_updated", "")
    # sort: digitized yes first, then by last_updated desc
    filtered_list.sort(key=lambda x: (0 if x["digitized (yes/no)"].strip().lower() == "yes" else 1,
                                      x.get("last_updated","")), reverse=False)
    return filtered_list[:top_n]

# In-memory user states (for demo)
user_states = {}

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    from_number = request.values.get("From", "")

    resp = MessagingResponse()
    msg = resp.message()

    if from_number not in user_states:
        user_states[from_number] = {"step": "start"}
        msg.body("नमस्ते 👋 Welcome to WEP Bot!\nShall we find schemes for you? (Yes/No)")
        return str(resp)

    state = user_states[from_number]

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

        # Mapping
        sector_map = {"1": "food", "2": "handicraft", "3": "services", "4": "general"}
        pillar_map = {"1": "Access to finance", "2": "Skill development", "3": "Marketing assistance", "4": "Technology"}

        sector = sector_map.get(state.get("sector",""), "general")
        assistance = pillar_map.get(state.get("assistance",""), "general")
        registered = state.get("registered","").lower() in ["yes", "हाँ"]

        # Filter by pillar (assistance)
        filtered = [s for s in schemes if assistance.lower() in (s.get("pillar") or "").lower()]

        # Sector keyword match
        if sector != "general":
            filtered = [s for s in filtered if sector in (s.get("eligibility_summary") or "").lower()]

        # Registration check (if unregistered prefer those mentioning 'unregistered' or 'informal')
        if not registered:
            filtered = [s for s in filtered if "unregistered" in (s.get("eligibility_summary") or "").lower() or "informal" in (s.get("eligibility_summary") or "").lower()]

        # Fallback
        if len(filtered) < 3:
            # pick top 3 from full list (digitized first)
            filtered = schemes[:3]

        top = rank_and_pick(filtered, top_n=3)

        reply_lines = ["आपके प्रोफ़ाइल के आधार पर ये योजनाएँ उपयुक्त हैं:\n"]
        for idx, row in enumerate(top, start=1):
            reply_lines.append(f"{idx}️⃣ {row.get('scheme_name')} ({row.get('benefit_summary')})")
            reply_lines.append(f"👉 Apply: {row.get('application_url')}")
            reply_lines.append(f"Docs: {row.get('required_documents')}\n")

        msg.body("\n".join(reply_lines))

    else:
        msg.body("Demo end ✅. Type 'Hi' to restart.")

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
