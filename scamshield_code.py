import re
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

SCAM_MESSAGES = [
    "Congratulations! You are selected for work from home internship. Pay Rs 500 registration fee to confirm your seat. Urgent, limited seats.",
    "URGENT: You won a cash prize of Rs 2500000 in lucky draw. Click http://bit.ly/claim-prize to claim immediately.",
    "Earn Rs 5000 per day. No interview. Send Rs 999 refundable security deposit on UPI to get the job.",
    "Your internship offer letter is ready. Pay Rs 1500 processing fee to get the certificate today. Contact HR on WhatsApp.",
    "Winner! You have won an iPhone. Share your Aadhaar and bank account details to receive the gift now.",
    "Part time job: like YouTube videos and earn Rs 3000 daily. Join our Telegram group now. No experience needed.",
    "Your resume is selected by TCS without interview. Deposit Rs 2000 as training kit fee within 24 hours.",
    "Your SBI account will be blocked today. Update your KYC immediately at http://sbi-kyc-update.xyz/login",
    "Guaranteed 100% placement. Pay registration amount and get joining letter instantly.",
    "You are the lucky winner of the college lottery. Send OTP to claim Rs 50000 cash prize.",
    "Hiring freshers for typing job. Salary 40000 per month. Pay Rs 700 for ID card and security deposit.",
    "Your scholarship is approved. Click the link and enter your bank details and OTP to receive it.",
    "Google internship selected! Confirm by paying Rs 1200 verification fee. Offer expires today, act now.",
    "Your exam fee refund is pending. Share your debit card number and CVV to get refund immediately.",
    "Hurry! Last chance to get free laptop. Register at www.free-laptop.top and pay Rs 199 delivery charge.",
    "Your parcel is held at customs. Pay Rs 850 clearance fee via UPI immediately.",
    "Exclusive internship at Microsoft for only Rs 999. Certificate guaranteed. Pay now on this UPI id.",
    "Your KYC has expired. Click here to verify or account will be suspended in 24 hours. http://tinyurl.com/kyc-verify",
    "You won a free Goa trip in lucky draw. Claim now by paying Rs 299 booking charge.",
    "Airline job for freshers. Salary 35000. Pay Rs 5000 for uniform and medical test before joining.",
]

SAFE_MESSAGES = [
    "Campus drive by Infosys is on Monday at 10 am in the seminar hall. Carry your ID card.",
    "Your OTP for login is 482913. Do not share it with anyone.",
    "Reminder: internal exam timetable is uploaded on the college portal.",
    "Hi, are we meeting for the project discussion tomorrow after class?",
    "Thank you for applying to the summer internship at Zoho. We will contact you within two weeks.",
    "Your Swiggy order has been delivered. Enjoy your meal!",
    "The last date for fee payment on the official college portal is 30th.",
    "Interview invitation: join the Google Meet at 3 PM on Friday for your technical round.",
    "Don't forget to eat lunch. I will call you in the evening.",
    "Assignment 3 deadline is extended to Sunday midnight. Upload it on the LMS.",
    "Your Amazon order has shipped and will arrive on Thursday.",
    "Team meeting moved to 4 pm. Please update your status before the call.",
    "Happy birthday! Let's have a treat this weekend.",
    "Congratulations on completing your course! Your certificate is available on the dashboard.",
    "The hackathon registration is open and free for all students on the official website.",
    "Can you send me the notes for the data structures lecture? I missed class.",
    "Your cab is arriving in 3 minutes. Vehicle TN 07 AB 1234.",
    "Library notice: the book you reserved is available. Collect it within 3 days.",
    "Your offer letter has been sent to your registered email. No fees are required to join.",
    "Webinar on machine learning basics on Saturday 11 AM. Register for free on the college portal.",
]


@st.cache_resource
def train_model():
    texts = SCAM_MESSAGES + SAFE_MESSAGES
    labels = [1] * len(SCAM_MESSAGES) + [0] * len(SAFE_MESSAGES)
    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2))
    numbers = vectorizer.fit_transform(texts)
    model = LogisticRegression(max_iter=1000)
    model.fit(numbers, labels)
    return vectorizer, model


def ml_scam_probability(message):
    vectorizer, model = train_model()
    probability = model.predict_proba(vectorizer.transform([message]))[0][1]
    return probability * 100


RULES = [
    ("Asks for money", 40,
     ["registration fee", "security deposit", "processing fee", "verification fee", "refundable",
      "pay rs", "send money", "upi", "booking charge", "clearance fee", "delivery charge", "training kit"],
     "It asks you to pay money. Real internships and jobs never charge candidates."),

    ("Prize / lottery", 30,
     ["you won", "you have won", "lucky draw", "lucky winner", "cash prize", "lottery", "winner", "claim now", "free laptop"],
     "It talks about a prize. You cannot win a contest you never entered."),

    ("False urgency", 20,
     ["urgent", "immediately", "limited seats", "within 24 hours", "last chance", "act now", "expires today", "hurry"],
     "It pushes you to hurry so you don't think carefully."),

    ("Too good to be true", 25,
     ["work from home", "per day", "daily", "no interview", "without interview", "no experience", "guaranteed", "100% placement"],
     "The offer sounds unrealistic (high pay, no interview, guaranteed)."),

    ("Asks for private data", 40,
     ["send otp", "share otp", "enter otp", "and otp", "aadhaar", "cvv", "debit card number", "bank details", "bank account", "kyc"],
     "It asks for private data like OTP, Aadhaar or bank details."),

    ("Moves you to WhatsApp/Telegram", 15,
     ["whatsapp", "telegram"],
     "Scammers like to move chats to WhatsApp or Telegram."),
]


def check_rules(message):
    text = message.lower()
    score = 0
    reasons = []
    for name, points, words, explanation in RULES:
        found = [w for w in words if w in text]
        if found:
            score += points
            reasons.append(name + ": " + explanation + "  (found: " + ", ".join(found[:3]) + ")")
    return min(score, 100), reasons


SHORT_LINK_SITES = ["bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly", "rb.gy"]
BAD_ENDINGS = [".xyz", ".top", ".click", ".tk", ".ml", ".buzz", ".work", ".loan", ".icu"]
FAKE_BRANDS = ["sbi", "hdfc", "icici", "paytm", "amazon", "google", "netflix", "jio", "tcs", "infosys"]


def check_links(message):
    links = re.findall(r"(?:https?://|www\.)[^\s]+", message.lower())
    highest = 0
    reasons = []
    for link in links:
        score = 0
        notes = []
        if any(site in link for site in SHORT_LINK_SITES):
            score += 35
            notes.append("shortened link hides the real website")
        if any(end in link for end in BAD_ENDINGS):
            score += 30
            notes.append("suspicious website ending")
        if link.startswith("http://"):
            score += 10
            notes.append("not secure (http)")
        if any(w in link for w in ["kyc", "claim", "prize", "free", "verify", "login", "winner"]):
            score += 15
            notes.append("scam-like word inside the link")
        if any(b in link for b in FAKE_BRANDS) and not re.search(r"//([a-z0-9-]+\.)?(" + "|".join(FAKE_BRANDS) + r")\.(com|in|co\.in)(/|$)", link):
            score += 35
            notes.append("pretends to be a famous brand")
        score = min(score, 100)
        if score > 0:
            reasons.append("Risky link " + link + ": " + ", ".join(notes))
        highest = max(highest, score)
    return highest, reasons


def analyse(message):
    rule_score, rule_reasons = check_rules(message)
    ml_score = ml_scam_probability(message)
    link_score, link_reasons = check_links(message)

    risk = 0.40 * rule_score + 0.45 * ml_score + 0.30 * link_score
    risk = int(min(round(risk), 100))

    if risk >= 60:
        verdict = "SCAM"
    elif risk >= 30:
        verdict = "SUSPICIOUS"
    else:
        verdict = "SAFE"

    reasons = rule_reasons + link_reasons
    if ml_score >= 60:
        reasons.append("The ML model has seen similar scam messages before.")
    if not reasons:
        reasons.append("No scam patterns, risky links or payment requests found.")

    return verdict, risk, rule_score, ml_score, link_score, reasons


st.set_page_config(page_title="scamshield", page_icon="🛡️")
st.title("🛡️ scamshield")
st.write("Real-time scam protection for students. Paste any SMS, email or WhatsApp message below.")

SAMPLES = {
    "-- choose a sample --": "",
    "Fake internship (fee)": "Congratulations! You are selected for a work from home internship at Google. Pay Rs 999 registration fee on UPI to confirm your seat. Limited seats, urgent! Contact HR on WhatsApp.",
    "Cash prize + link": "URGENT: You have won a cash prize of Rs 2500000 in the lucky draw. Claim now at http://bit.ly/claim-prize-now and share your bank account details.",
    "Fake bank KYC": "Your SBI account will be blocked today. Update your KYC immediately: http://sbi-kyc-update.xyz/login",
    "Genuine interview mail": "Hi, thank you for applying to the Zoho summer internship. Your technical interview is on Friday at 3 PM on Google Meet. No fees are required at any stage.",
    "Normal chat": "Hey, are we meeting for the project discussion tomorrow after class?",
}
choice = st.selectbox("Try a sample message:", list(SAMPLES.keys()))
message = st.text_area("Message to check:", value=SAMPLES[choice], height=150)

if st.button("Scan message"):
    if message.strip() == "":
        st.warning("Please type or paste a message first.")
    else:
        verdict, risk, rule_score, ml_score, link_score, reasons = analyse(message)

        if verdict == "SCAM":
            st.error("🚨 SCAM  -  Risk " + str(risk) + "/100")
        elif verdict == "SUSPICIOUS":
            st.warning("⚠️ SUSPICIOUS  -  Risk " + str(risk) + "/100")
        else:
            st.success("✅ SAFE  -  Risk " + str(risk) + "/100")
        st.progress(risk / 100)

        col1, col2, col3 = st.columns(3)
        col1.metric("Keyword rules", str(rule_score) + "/100")
        col2.metric("ML model", str(int(ml_score)) + "%")
        col3.metric("Link check", str(link_score) + "/100")

        st.subheader("Why?")
        for reason in reasons:
            st.write("• " + reason)