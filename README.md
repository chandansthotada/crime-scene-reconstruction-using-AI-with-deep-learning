1. Install dependencies:
   `npm install`
2. Set the `GEMINI_API_KEY` in [.env.local](.env.local) to your Gemini API key
3. Run the app:
   `npm run dev`
##backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload