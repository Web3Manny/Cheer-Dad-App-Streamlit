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

# Environment Variables - FIXED: Using os.getenv() correctly
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_MONTHLY_PRICE_ID = os.getenv("STRIPE_MONTHLY_PRICE_ID")
STRIPE_ANNUAL_PRICE_ID = os.getenv("STRIPE_ANNUAL_PRICE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Clients
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
    </style>
</head>
<body class="bg-gray-50 text-gray-900 font-sans min-h-screen flex flex-col items-center p-5">

    <header class="text-center mt-6 mb-8">
        <h1 class="text-4xl font-black text-blue-600 tracking-tight">CheerDad<span class="text-gray-400">.app</span></h1>
        <p class="text-gray-500 font-medium mt-1">Confused? We've got you, Dad.</p>
    </header>

    <main class="w-full max-w-md bg-white rounded-3xl shadow-xl p-8 space-y-8">
        
        <!-- PROGRESS BAR - ADDED -->
        <div id="progressContainer">
            <div class="flex justify-between text-xs font-bold text-gray-400 mb-1 uppercase">
                <span id="usageText">0 of 3 Free Used</span>
                <div class="space-x-2">
                    <button onclick="createCheckout('monthly')" class="text-blue-500 hover:underline">$4.99 Monthly</button>
                    <span class="text-gray-300">|</span>
                    <button onclick="createCheckout('annual')" class="text-red-500 hover:underline">$14.99 Season Pass</button>
                </div>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
                <div id="progressBar" class="bg-green-500 h-2 rounded-full transition-all duration-500" style="width: 0%"></div>
            </div>
        </div>

        <div id="sportSelector" class="space-y-4">
            <p class="text-center font-bold text-gray-700">1. PICK YOUR SPORT</p>
            <div class="grid grid-cols-3 gap-3">
                <button onclick="selectSport('NFL', '🏈')" class="sport-btn p-4 bg-gray-100 rounded-2xl text-2xl hover:bg-blue-50 transition-all border-2 border-transparent" data-sport="NFL">🏈<br><span class="text-xs font-bold">NFL</span></button>
                <button onclick="selectSport('NBA', '🏀')" class="sport-btn p-4 bg-gray-100 rounded-2xl text-2xl hover:bg-blue-50 transition-all border-2 border-transparent" data-sport="NBA">🏀<br><span class="text-xs font-bold">NBA</span></button>
                <button onclick="selectSport('MLB', '⚾')" class="sport-btn p-4 bg-gray-100 rounded-2xl text-2xl hover:bg-blue-50 transition-all border-2 border-transparent" data-sport="MLB">⚾<br><span class="text-xs font-bold">MLB</span></button>
                <button onclick="selectSport('PGA', '⛳')" class="sport-btn p-4 bg-gray-100 rounded-2xl text-2xl hover:bg-blue-50 transition-all border-2 border-transparent" data-sport="PGA">⛳<br><span class="text-xs font-bold">PGA</span></button>
                <button onclick="selectSport('Soccer', '⚽')" class="sport-btn p-4 bg-gray-100 rounded-2xl text-2xl hover:bg-blue-50 transition-all border-2 border-transparent" data-sport="Soccer">⚽<br><span class="text-xs font-bold">Soccer</span></button>
            </div>
        </div>

        <div class="flex flex-col items-center space-y-4">
            <button id="recordBtn" disabled class="w-32 h-32 bg-gray-300 rounded-full flex flex-col items-center justify-center text-white shadow-lg disabled:opacity-50 transition-all">
                <span class="text-4xl">🎤</span>
                <span id="recordLabel" class="text-xs font-black mt-1">LOCKED</span>
            </button>
            <p id="hintText" class="text-sm text-gray-400 italic">Select a sport to start translating</p>
        </div>

        <div id="resultArea" class="hidden space-y-4 animate-in fade-in duration-500">
            <div class="p-5 bg-blue-50 rounded-2xl border border-blue-100">
                <p id="translationOutput" class="text-lg font-medium italic text-blue-900 leading-relaxed"></p>
            </div>
            <div class="flex gap-2">
                <button onclick="share()" class="flex-1 bg-green-500 text-white font-bold py-4 rounded-2xl shadow-lg hover:bg-green-600">📤 SHARE</button>
                <button onclick="resetUI()" class="flex-1 bg-gray-100 text-gray-600 font-bold py-4 rounded-2xl">RETRY</button>
            </div>
        </div>

        <div id="loadingState" class="hidden text-center space-y-4">
            <div class="animate-spin text-4xl">⚙️</div>
            <p id="dadJoke" class="text-sm font-medium text-gray-500 animate-pulse"></p>
        </div>
    </main>

    <footer class="mt-12 w-full max-w-md px-4 pb-10">
        <div class="p-6 bg-blue-50 rounded-2xl border border-blue-100 text-center">
            <p class="text-xs text-gray-500 font-bold uppercase tracking-widest mb-2">Coach's Corner</p>
            <p class="text-sm text-gray-600 mb-3">Gym Owners & Coaches: This was built for fun—<strong>CheerConnect</strong> was built for your business.</p>
            <a href="https://cheerconnect.app?utm_source=cheerdad&utm_medium=footer" target="_blank" class="text-blue-600 font-black hover:underline">LEARN MORE →</a>
        </div>
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

        // Recording Logic
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
            
            // Change progress bar color as it fills
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

        // ADDED: Stripe Checkout function
        async function createCheckout(planType) {
            const email = prompt("Enter your email to secure your pass:");
            if (!email) return;
            
            // Basic email validation
            if (!email.includes('@')) {
                alert("Please enter a valid email address");
                return;
            }
            
            try {
                const res = await fetch('/create-checkout-session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: email, plan_type: planType })
                });
                const data = await res.json();
                
                if (data.error) {
                    alert("Checkout failed: " + data.error);
                    return;
                }
                
                if (data.url) {
                    window.location.href = data.url;
                }
            } catch (e) {
                alert("Something went wrong. Please try again.");
            }
        }

        // Initialize Usage on page load
        function initializeUsage() {
            document.getElementById('usageText').innerText = `${usage} of 3 Free Used`;
            document.getElementById('progressBar').style.width = `${(usage/3)*100}%`;
            
            // Set correct color based on usage
            const bar = document.getElementById('progressBar');
            if (usage === 0) bar.className = 'bg-green-500 h-2 rounded-full transition-all duration-500';
            if (usage === 1) bar.className = 'bg-yellow-500 h-2 rounded-full transition-all duration-500';
            if (usage === 2) bar.className = 'bg-orange-500 h-2 rounded-full transition-all duration-500';
            if (usage === 3) bar.className = 'bg-red-500 h-2 rounded-full transition-all duration-500';
        }
        
        // Run on page load
        initializeUsage();
        
        // Check for success/cancel params
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('success') === 'true') {
            alert('✅ Payment successful! You now have unlimited translations!');
            localStorage.setItem('translations_used', '0');
            localStorage.setItem('is_paid', 'true');
            // Remove query params
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
    # Save temp file
    temp_filename = f"temp_{int(time.time())}.wav"
    with open(temp_filename, "wb") as buffer:
        buffer.write(await file.read())
    
    # Whisper Transcription
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
    Act as the ultimate, high-energy sports fanatic talking to your best friend about his daughter's cheer team.
    
    SPORT CONTEXT: {req.sport}
    
    STRICT RULES:
    1. HIGH STAKES VIBE: Use words like 'Clutch,' 'Heart,' 'Elite,' and 'Statement Win.'
    2. NO 'AI' FLUFF: Do not explain metaphors. Do not say 'This is like...'
    3. ALL GAS, NO BRAKES: Use short, explosive sentences.
    4. SPORT-SPECIFIC LINGO:
       - NBA: 'playing above the rim,' 'clutch buckets,' 'draining treys,' 'elite spacing,' 'nothing but net'
       - NFL: 'punching it in,' 'iron-clad defense,' 'winning the turnover battle,' 'two-minute drill,' 'ball security'
       - MLB: 'painting the corners,' 'frozen rope hits,' 'clinching the division,' 'throwing a gem'
       - PGA: 'clutch putts,' 'pin-seeking shots,' 'Sunday charge,' 'staying in the short grass'
       - Soccer: 'stoppage-time magic,' 'absolute worldies,' 'top of the table,' 'clean sheet'
    
    THE GOAL: Help the dad understand what his athlete is sharing so they can fully connect.
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
    # Mapping plan types to your actual Stripe Price IDs
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
            line_items=[{
                'price': selected_price,
                'quantity': 1,
            }],
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
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            email = session.get('customer_email')
            
            # Save to Supabase
            if email:
                supabase.table('email_signups').upsert({
                    'email': email,
                    'is_paid': True,
                    'stripe_customer_id': session.get('customer')
                }).execute()
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
