import os
import time
import base64
import stripe
import openai
from typing import Optional
from fastapi import FastAPI, Request, File, UploadFile, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from supabase import create_client, Client

# === CONFIGURATION ===
app = FastAPI(title="CheerDad.app")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_MONTHLY_PRICE_ID = os.getenv("STRIPE_MONTHLY_PRICE_ID")
STRIPE_ANNUAL_PRICE_ID = os.getenv("STRIPE_ANNUAL_PRICE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

stripe.api_key = STRIPE_SECRET_KEY
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === MODELS ===
class TranslationRequest(BaseModel):
    transcription: str
    sport: str
    email: Optional[str] = None

class EmailSignup(BaseModel):
    email: str
    is_coach: bool = False

class CheckoutRequest(BaseModel):
    email: str
    plan_type: str

# === UI / FRONTEND ===
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <script src="https://cdn.tailwindcss.com"></script>
    <title>CheerDad.app | The Sideline Translator</title>
    <style>
        @keyframes pulse-red {
            0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
            70% { transform: scale(1.05); box-shadow: 0 0 0 15px rgba(239, 68, 68, 0); }
            100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }
        .recording-active { animation: pulse-red 1.5s infinite; }
        #checkoutModal { display: none; }
        #checkoutModal.open { display: flex; }
    </style>
</head>
<body class="bg-gray-50 text-gray-900 font-sans min-h-screen flex flex-col items-center p-5">

    <header class="text-center mt-6 mb-8">
        <h1 class="text-4xl font-black text-blue-600 tracking-tight">CheerDad<span class="text-gray-400">.app</span></h1>
        <p class="text-gray-500 font-medium mt-1">Confused? We've got you, Dad.</p>
    </header>

    <main class="w-full max-w-md bg-white rounded-3xl shadow-xl p-8 space-y-8">

        <!-- SPORT SELECTOR -->
        <div id="sportSelector" class="space-y-4">
            <p class="text-center font-bold text-gray-700 uppercase tracking-wide text-sm">1. Pick Your Sport</p>
            <div class="grid grid-cols-3 gap-3">
                <button onclick="selectSport('NFL', '🏈')" class="sport-btn p-4 bg-gray-100 rounded-2xl text-2xl hover:bg-blue-50 transition-all border-2 border-transparent" data-sport="NFL">🏈<br><span class="text-xs font-bold">NFL</span></button>
                <button onclick="selectSport('NBA', '🏀')" class="sport-btn p-4 bg-gray-100 rounded-2xl text-2xl hover:bg-blue-50 transition-all border-2 border-transparent" data-sport="NBA">🏀<br><span class="text-xs font-bold">NBA</span></button>
                <button onclick="selectSport('MLB', '⚾')" class="sport-btn p-4 bg-gray-100 rounded-2xl text-2xl hover:bg-blue-50 transition-all border-2 border-transparent" data-sport="MLB">⚾<br><span class="text-xs font-bold">MLB</span></button>
                <button onclick="selectSport('PGA', '⛳')" class="sport-btn p-4 bg-gray-100 rounded-2xl text-2xl hover:bg-blue-50 transition-all border-2 border-transparent" data-sport="PGA">⛳<br><span class="text-xs font-bold">PGA</span></button>
                <button onclick="selectSport('Soccer', '⚽')" class="sport-btn p-4 bg-gray-100 rounded-2xl text-2xl hover:bg-blue-50 transition-all border-2 border-transparent" data-sport="Soccer">⚽<br><span class="text-xs font-bold">Soccer</span></button>
            </div>
        </div>

        <!-- MIC SECTION -->
        <div class="flex flex-col items-center space-y-3">
            <p class="text-sm text-gray-500 text-center leading-snug">
                2. Hit record, then let your <strong>athlete</strong> recap her practice or competition.
            </p>
            <button id="recordBtn" disabled class="w-32 h-32 bg-gray-300 rounded-full flex flex-col items-center justify-center text-white shadow-lg disabled:opacity-50 transition-all">
                <span class="text-4xl">🎤</span>
                <span id="recordLabel" class="text-xs font-black mt-1">LOCKED</span>
            </button>
            <p id="hintText" class="text-sm text-gray-400 italic">Select a sport to unlock</p>
        </div>

        <!-- PROGRESS BAR + PRICING (below the mic) -->
        <div id="progressContainer" class="pt-2 border-t border-gray-100">
            <div class="flex justify-between text-xs font-semibold text-gray-400 mb-1">
                <span id="usageText">0 of 3 Free Used</span>
                <div class="space-x-2">
                    <button onclick="createCheckout('monthly')" class="text-blue-500 hover:underline">$4.99/mo</button>
                    <span class="text-gray-300">|</span>
                    <button onclick="createCheckout('annual')" class="text-red-500 hover:underline">$14.99 Season</button>
                </div>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-1.5">
                <div id="progressBar" class="bg-green-500 h-1.5 rounded-full transition-all duration-500" style="width: 0%"></div>
            </div>
        </div>

        <!-- RESULT -->
        <div id="resultArea" class="hidden space-y-4">
            <div class="p-5 bg-blue-50 rounded-2xl border border-blue-100">
                <p id="translationOutput" class="text-lg font-medium italic text-blue-900 leading-relaxed"></p>
            </div>
            <div class="flex gap-2">
                <button onclick="share()" class="flex-1 bg-green-500 text-white font-bold py-4 rounded-2xl shadow-lg hover:bg-green-600">📤 SHARE</button>
                <button onclick="resetUI()" class="flex-1 bg-gray-100 text-gray-600 font-bold py-4 rounded-2xl">RETRY</button>
            </div>
        </div>

        <!-- LOADING -->
        <div id="loadingState" class="hidden text-center space-y-4">
            <div class="animate-spin text-4xl">⚙️</div>
            <p id="dadJoke" class="text-sm font-medium text-gray-500 animate-pulse"></p>
        </div>

    </main>

    <!-- CHECKOUT MODAL -->
    <div id="checkoutModal" class="fixed inset-0 bg-black bg-opacity-50 z-50 items-center justify-center p-4">
        <div class="bg-white rounded-3xl shadow-2xl w-full max-w-sm p-8 space-y-5">
            <div class="text-center">
                <p class="text-2xl">🏆</p>
                <h2 class="text-xl font-black text-gray-900 mt-1">Unlock Unlimited Translations</h2>
                <p id="modalPlanLabel" class="text-sm text-gray-500 mt-1"></p>
            </div>

            <div class="space-y-3">
                <label class="block text-sm font-semibold text-gray-700">Email Address</label>
                <input 
                    type="email" 
                    id="modalEmail" 
                    placeholder="dad@example.com"
                    class="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
            </div>

            <!-- Consent checkbox -->
            <div class="flex items-start gap-3">
                <input type="checkbox" id="consentCheck" class="mt-1 w-4 h-4 accent-blue-500 flex-shrink-0" />
                <label for="consentCheck" class="text-xs text-gray-500 leading-snug">
                    I agree to the 
                    <a href="/terms" target="_blank" class="text-blue-500 underline">Terms of Service</a> 
                    and 
                    <a href="/privacy" target="_blank" class="text-blue-500 underline">Privacy Policy</a>. 
                    I understand my email will be used to manage my subscription and that I can cancel anytime.
                </label>
            </div>

            <p id="modalError" class="text-xs text-red-500 hidden"></p>

            <button 
                onclick="submitCheckout()" 
                class="w-full bg-blue-600 text-white font-black py-4 rounded-2xl hover:bg-blue-700 transition-all shadow-lg">
                Continue to Payment →
            </button>

            <button 
                onclick="closeModal()" 
                class="w-full text-gray-400 text-sm hover:text-gray-600 py-1">
                Cancel
            </button>

            <p class="text-xs text-gray-300 text-center">
                Secured by Stripe. We never store your card details.
            </p>
        </div>
    </div>

    <!-- FOOTER -->
    <footer class="mt-10 w-full max-w-md px-4 pb-10 space-y-4 text-center">
        
        <!-- Personal touch -->
        <p class="text-xs text-gray-400 leading-relaxed">
            Love the app? Help support the dev! 🙌<br>
            Built by a cheer coach — and a dad — to help other dads stay connected.
        </p>

        <!-- Subtle CheerConnect promo -->
        <p class="text-xs text-gray-400">
            Coach or gym owner? 
            <a href="https://cheerconnect.app?utm_source=cheerdad&utm_medium=footer" target="_blank" class="text-blue-400 hover:underline font-medium">CheerConnect</a> 
            was built for your business.
        </p>

        <!-- Legal -->
        <div class="text-xs text-gray-300 space-x-2">
            <a href="/privacy" class="hover:text-gray-400">Privacy Policy</a>
            <span>|</span>
            <a href="/terms" class="hover:text-gray-400">Terms of Service</a>
        </div>
        <p class="text-xs text-gray-300">© 2026 CheerDad.app. All rights reserved. Not affiliated with any cheerleading organization. For entertainment purposes only.</p>
    </footer>

    <script>
        let selectedSport = null;
        let isRecording = false;
        let recorder;
        let audioChunks = [];
        let usage = parseInt(localStorage.getItem('translations_used') || 0);

        const jokes = [
            "Why don't cheerleaders get lost? They know the routine.",
            "How many dads does it take to understand a full-up? All of them.",
            "Confused? It's okay, I came for the snacks too.",
            "My daughter's triple twist is elite. I can barely do a sit-up.",
            "I'm not a regular dad, I'm a cool (and confused) cheer dad."
        ];

        function selectSport(id, emoji) {
            selectedSport = id;
            document.querySelectorAll('.sport-btn').forEach(b => b.classList.remove('border-blue-500', 'bg-blue-100', 'scale-105'));
            const active = document.querySelector(`[data-sport="${id}"]`);
            active.classList.add('border-blue-500', 'bg-blue-100', 'scale-105');
            
            const btn = document.getElementById('recordBtn');
            btn.disabled = false;
            btn.classList.replace('bg-gray-300', 'bg-red-500');
            document.getElementById('recordLabel').innerText = "RECORD";
            document.getElementById('hintText').classList.add('hidden');
        }

        const recordBtn = document.getElementById('recordBtn');
        recordBtn.onclick = async () => {
            if (usage >= 3) { 
                alert("You've used your 3 free translations! Upgrade for unlimited access."); 
                return; 
            }
            if (!isRecording) {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                recorder = new MediaRecorder(stream);
                recorder.ondataavailable = e => audioChunks.push(e.data);
                recorder.onstop = uploadAudio;
                audioChunks = [];
                recorder.start();
                isRecording = true;
                recordBtn.classList.add('recording-active');
                document.getElementById('recordLabel').innerText = "STOP";
            } else {
                recorder.stop();
                isRecording = false;
                recordBtn.classList.remove('recording-active');
                document.getElementById('recordLabel').innerText = "RECORD";
            }
        };

        async function uploadAudio() {
            showLoading(true);
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const formData = new FormData();
            formData.append('file', audioBlob);

            try {
                const res = await fetch('/upload', { method: 'POST', body: formData });
                const { transcription } = await res.json();
                
                const transRes = await fetch('/translate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ transcription, sport: selectedSport })
                });
                const { translation } = await transRes.json();
                
                displayResult(translation);
                updateUsage();
            } catch (e) {
                alert("Translation failed. Try again!");
                showLoading(false);
            }
        }

        function displayResult(text) {
            showLoading(false);
            document.getElementById('sportSelector').classList.add('hidden');
            recordBtn.parentElement.classList.add('hidden');
            document.getElementById('resultArea').classList.remove('hidden');
            document.getElementById('translationOutput').innerText = text;
        }

        function showLoading(show) {
            document.getElementById('loadingState').classList.toggle('hidden', !show);
            if(show) {
                document.getElementById('dadJoke').innerText = jokes[Math.floor(Math.random()*jokes.length)];
            }
        }

        function updateUsage() {
            usage++;
            localStorage.setItem('translations_used', usage);
            document.getElementById('usageText').innerText = `${usage} of 3 Free Used`;
            document.getElementById('progressBar').style.width = `${(usage/3)*100}%`;
            
            const bar = document.getElementById('progressBar');
            if (usage === 1) bar.classList.replace('bg-green-500', 'bg-yellow-500');
            if (usage === 2) bar.classList.replace('bg-yellow-500', 'bg-orange-500');
            if (usage === 3) bar.classList.replace('bg-orange-500', 'bg-red-500');
        }

        function share() {
            const text = `My daughter's cheer recap (Dad Translation):\\n\\n"${document.getElementById('translationOutput').innerText}"\\n\\nGet your own: CheerDad.app`;
            if (navigator.share) {
                navigator.share({ text });
            } else {
                navigator.clipboard.writeText(text);
                alert("Copied to clipboard! ✅");
            }
        }

        function resetUI() {
            document.getElementById('resultArea').classList.add('hidden');
            document.getElementById('sportSelector').classList.remove('hidden');
            recordBtn.parentElement.classList.remove('hidden');
        }

        let pendingPlanType = null;

        function createCheckout(planType) {
            pendingPlanType = planType;
            const labels = {
                monthly: '$4.99/month — 30 Days Unlimited',
                annual: '$14.99/year — Full Season Pass'
            };
            document.getElementById('modalPlanLabel').innerText = labels[planType] || '';
            document.getElementById('modalEmail').value = '';
            document.getElementById('consentCheck').checked = false;
            document.getElementById('modalError').classList.add('hidden');
            document.getElementById('checkoutModal').classList.add('open');
            setTimeout(() => document.getElementById('modalEmail').focus(), 100);
        }

        function closeModal() {
            document.getElementById('checkoutModal').classList.remove('open');
            pendingPlanType = null;
        }

        // Close modal if clicking backdrop
        document.getElementById('checkoutModal').addEventListener('click', function(e) {
            if (e.target === this) closeModal();
        });

        async function submitCheckout() {
            const email = document.getElementById('modalEmail').value.trim();
            const consent = document.getElementById('consentCheck').checked;
            const errorEl = document.getElementById('modalError');

            if (!email || !email.includes('@')) {
                errorEl.innerText = 'Please enter a valid email address.';
                errorEl.classList.remove('hidden');
                return;
            }
            if (!consent) {
                errorEl.innerText = 'Please agree to the Terms of Service and Privacy Policy to continue.';
                errorEl.classList.remove('hidden');
                return;
            }

            errorEl.classList.add('hidden');

            try {
                const res = await fetch('/create-checkout-session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, plan_type: pendingPlanType })
                });
                const data = await res.json();
                if (data.error) {
                    errorEl.innerText = 'Checkout failed: ' + data.error;
                    errorEl.classList.remove('hidden');
                    return;
                }
                if (data.url) { window.location.href = data.url; }
            } catch (e) {
                errorEl.innerText = 'Something went wrong. Please try again.';
                errorEl.classList.remove('hidden');
            }
        }

        function initializeUsage() {
            document.getElementById('usageText').innerText = `${usage} of 3 Free Used`;
            document.getElementById('progressBar').style.width = `${(usage/3)*100}%`;
            const bar = document.getElementById('progressBar');
            if (usage === 0) bar.className = 'bg-green-500 h-1.5 rounded-full transition-all duration-500';
            if (usage === 1) bar.className = 'bg-yellow-500 h-1.5 rounded-full transition-all duration-500';
            if (usage === 2) bar.className = 'bg-orange-500 h-1.5 rounded-full transition-all duration-500';
            if (usage === 3) bar.className = 'bg-red-500 h-1.5 rounded-full transition-all duration-500';
        }
        
        initializeUsage();
        
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('success') === 'true') {
            alert('✅ Payment successful! You now have unlimited translations!');
            localStorage.setItem('translations_used', '0');
            localStorage.setItem('is_paid', 'true');
            window.history.replaceState({}, document.title, "/");
        }
        if (urlParams.get('cancel') === 'true') {
            alert('Payment cancelled. You still have your free translations!');
            window.history.replaceState({}, document.title, "/");
        }
    </script>
</body>
</html>
"""

# === BACKEND ENDPOINTS ===

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_CONTENT

@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    temp_filename = f"temp_{int(time.time())}.wav"
    with open(temp_filename, "wb") as buffer:
        buffer.write(await file.read())
    
    with open(temp_filename, "rb") as audio:
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio
        )
    
    os.remove(temp_filename)
    return {"transcription": transcript.text}

@app.post("/translate")
async def translate_text(req: TranslationRequest):
    system_prompt = f"""
You are a bilingual sports translator. You are fluent in two languages:

LANGUAGE 1 - CHEER: You have 15+ years as an All-Star cheerleading coach. You understand stunting, tumbling, scoring, competition structure, skill levels, and what it takes to execute at a high level. You've coached flyers, trained tumblers, and sat in the coaches box at Worlds.

LANGUAGE 2 - DAD SPORTS: You are equally fluent in Football, Basketball, Baseball, Golf, and Soccer. You understand the pressure, the skill, the grind, and the glory of each sport at the highest level.

DAD'S SPORT: {req.sport}

YOUR JOB: A cheer athlete just described something from practice or competition. Translate it from cheer language into {req.sport} language so her dad instantly gets it — not just what happened, but the WEIGHT of it.

RULES:
1. Match the difficulty of the cheer skill to an equivalent moment in {req.sport}. Sticking tumbling = draining a clutch free throw. A hit zero at a bid tournament = clinching a playoff berth on the road.
2. Use {req.sport} jargon naturally. Dad should feel like his buddy is calling him about a game.
3. Keep cheer terminology IN but immediately follow it with the {req.sport} equivalent so dad gets both.
4. High energy. Short sentences. Proud coach meets hype commentator.
5. End with one line that makes dad feel like he needs to be at the next competition.
6. No section headers like "OFF THE COURT" or "FINAL WORD". Just flow naturally.
"""
    
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"RECAP TO TRANSLATE: {req.transcription}"}
        ]
    )
    
    return {"translation": response.choices[0].message.content}

@app.post("/create-checkout-session")
async def create_checkout_session(req: CheckoutRequest):
    price_ids = {
        "monthly": STRIPE_MONTHLY_PRICE_ID,
        "annual": STRIPE_ANNUAL_PRICE_ID
    }
    
    selected_price = price_ids.get(req.plan_type)
    if not selected_price:
        return {"error": "Invalid plan type"}

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': selected_price, 'quantity': 1}],
            mode='subscription',
            success_url='https://cheerdad.app/?success=true',
            cancel_url='https://cheerdad.app/?cancel=true',
            client_reference_id=req.email,
            customer_email=req.email,
        )
        return {"url": checkout_session.url}
    except Exception as e:
        return {"error": str(e)}

@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            email = session.get('customer_email')
            if email:
                supabase.table('email_signups').upsert({
                    'email': email,
                    'is_paid': True,
                    'stripe_customer_id': session.get('customer')
                }).execute()
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/privacy", response_class=HTMLResponse)
async def privacy():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <title>Privacy Policy | CheerDad.app</title>
</head>
<body class="bg-gray-50 font-sans p-8 max-w-2xl mx-auto">
    <a href="/" class="text-blue-500 text-sm hover:underline">← Back to CheerDad.app</a>
    <h1 class="text-3xl font-black text-blue-600 mt-6 mb-2">Privacy Policy</h1>
    <p class="text-gray-400 text-sm mb-8">Last updated: January 2026</p>

    <div class="space-y-6 text-gray-700 leading-relaxed">
        <section>
            <h2 class="font-bold text-lg mb-2">What We Collect</h2>
            <p>We collect audio recordings you submit for translation, your email address if you sign up or purchase a plan, and basic usage data (number of translations used, stored locally on your device).</p>
        </section>
        <section>
            <h2 class="font-bold text-lg mb-2">How We Use It</h2>
            <p>Audio is sent to OpenAI's Whisper API for transcription and then to GPT-4 for translation. We do not store your audio recordings. Email addresses are used to manage your subscription and communicate with you.</p>
        </section>
        <section>
            <h2 class="font-bold text-lg mb-2">Third Parties</h2>
            <p>We use OpenAI for AI processing, Stripe for payment processing, and Supabase for data storage. Each has their own privacy policy governing your data.</p>
        </section>
        <section>
            <h2 class="font-bold text-lg mb-2">Your Rights</h2>
            <p>You can request deletion of your account data at any time by emailing us. We do not sell your personal information.</p>
        </section>
        <section>
            <h2 class="font-bold text-lg mb-2">Contact</h2>
            <p>Questions? Reach us at hello@cheerdad.app</p>
        </section>
    </div>
    <p class="text-xs text-gray-300 mt-12">© 2026 CheerDad.app. All rights reserved.</p>
</body>
</html>
"""

@app.get("/terms", response_class=HTMLResponse)
async def terms():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <title>Terms of Service | CheerDad.app</title>
</head>
<body class="bg-gray-50 font-sans p-8 max-w-2xl mx-auto">
    <a href="/" class="text-blue-500 text-sm hover:underline">← Back to CheerDad.app</a>
    <h1 class="text-3xl font-black text-blue-600 mt-6 mb-2">Terms of Service</h1>
    <p class="text-gray-400 text-sm mb-8">Last updated: January 2026</p>

    <div class="space-y-6 text-gray-700 leading-relaxed">
        <section>
            <h2 class="font-bold text-lg mb-2">Use of Service</h2>
            <p>CheerDad.app is an entertainment tool designed to help parents understand cheerleading terminology. It is not affiliated with any cheerleading organization, governing body, or gym.</p>
        </section>
        <section>
            <h2 class="font-bold text-lg mb-2">Free Translations</h2>
            <p>New users receive 3 free translations. Free usage is tracked locally on your device. We reserve the right to modify free tier limits.</p>
        </section>
        <section>
            <h2 class="font-bold text-lg mb-2">Subscriptions</h2>
            <p>Paid plans are billed through Stripe. Monthly plans renew monthly. Season Pass is billed annually. You may cancel at any time through your account or by contacting us.</p>
        </section>
        <section>
            <h2 class="font-bold text-lg mb-2">Disclaimer</h2>
            <p>Translations are AI-generated and for entertainment purposes only. We make no guarantees about accuracy. Do not use this service for official competition reporting or coaching decisions.</p>
        </section>
        <section>
            <h2 class="font-bold text-lg mb-2">Contact</h2>
            <p>Questions? Reach us at hello@cheerdad.app</p>
        </section>
    </div>
    <p class="text-xs text-gray-300 mt-12">© 2026 CheerDad.app. All rights reserved.</p>
</body>
</html>
"""
