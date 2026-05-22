from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
import shutil
import subprocess
import os
import requests

app = FastAPI()

# ----------------- FRONTEND (HTML + Tailwind CSS + JS) -----------------
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reverse Video Search Engine</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white flex items-center justify-center h-screen">
    <div class="bg-gray-800 p-8 rounded-lg shadow-lg w-full max-w-md text-center border border-gray-700">
        <h1 class="text-3xl font-bold mb-2 text-indigo-400">Video Search</h1>
        <p class="text-gray-400 text-sm mb-6">Upload a clip to find the original source</p>
        
        <input type="file" id="videoInput" accept="video/*" 
            class="mb-4 block w-full text-sm text-gray-400 
            file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 
            file:text-sm file:font-bold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500" />
            
        <button onclick="uploadVideo()" id="searchBtn" 
            class="bg-indigo-500 hover:bg-indigo-600 transition text-white font-bold py-2 px-4 rounded w-full">
            🔍 Search Original Video
        </button>

        <div id="loading" class="mt-6 text-yellow-400 hidden animate-pulse font-medium">
            ⏳ Extracting frame & searching the web...
        </div>

        <div id="result" class="mt-6 text-left hidden bg-gray-900 p-4 rounded-md border border-green-500/30">
            <p class="text-green-400 font-bold mb-2 flex items-center">✅ Match Found!</p>
            <p class="text-sm"><strong>Original Link:</strong> <br>
                <a id="resLink" href="#" target="_blank" class="text-blue-400 underline break-words"></a>
            </p>
            <p class="text-sm mt-2"><strong>Status:</strong> <span id="resDuration" class="text-gray-300"></span></p>
        </div>
    </div>

    <script>
        async function uploadVideo() {
            const fileInput = document.getElementById('videoInput');
            if (!fileInput.files[0]) return alert("Please select a video file!");
            
            document.getElementById('loading').classList.remove('hidden');
            document.getElementById('result').classList.add('hidden');
            document.getElementById('searchBtn').disabled = true;

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            try {
                const response = await fetch('/search', { method: 'POST', body: formData });
                const data = await response.json();
                
                if(data.success) {
                    document.getElementById('resLink').href = data.link;
                    document.getElementById('resLink').innerText = data.link;
                    document.getElementById('resDuration').innerText = data.duration;
                    document.getElementById('result').classList.remove('hidden');
                } else {
                    alert("Backend Error: " + data.error);
                }
            } catch(e) {
                alert("Server error! Check if Render backend is awake.");
            }
            
            document.getElementById('loading').classList.add('hidden');
            document.getElementById('searchBtn').disabled = false;
        }
    </script>
</body>
</html>
"""

# ----------------- BACKEND ROUTES -----------------
@app.get("/")
async def serve_frontend():
    return HTMLResponse(content=HTML_CONTENT)

@app.post("/search")
async def process_and_search_video(file: UploadFile = File(...)):
    try:
        # 1. Save uploaded video temporarily
        video_path = f"temp_{file.filename}"
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 2. Extract a frame using FFmpeg (at the 1-second mark)
        frame_path = f"frame_extracted.jpg"
        cmd = f"ffmpeg -y -i \"{video_path}\" -ss 00:00:01 -vframes 1 \"{frame_path}\""
        subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 3. Upload frame to ImgBB
        imgbb_api_key = "2004d341fc8640cc32f3f188daf97b53"
        with open(frame_path, "rb") as image_file:
            img_response = requests.post(
                f"https://api.imgbb.com/1/upload?key={imgbb_api_key}",
                files={"image": image_file}
            ).json()
            
        if "data" not in img_response:
            return {"success": False, "error": "Image upload failed"}
            
        public_image_url = img_response["data"]["url"]

        # 4. Search that image on Google Lens using SerpApi
        serpapi_key = "723413977cdcd590c3d07450921efa5dee502ed3d5706e9502848459c04f575c"
        search_params = {
            "engine": "google_lens",
            "url": public_image_url,
            "api_key": serpapi_key
        }
        
        lens_response = requests.get("https://serpapi.com/search.json", params=search_params).json()

        # 5. Find the first YouTube or Video link from the results
        original_link = "No video link found. Try a different clip!"
        
        if "visual_matches" in lens_response:
            for match in lens_response["visual_matches"]:
                link = match.get("link", "")
                if "youtube.com" in link or "youtu.be" in link or "vimeo" in link:
                    original_link = link
                    break # Stop at the first video match
        
        original_duration = "Check the link for full video details"
        
        # 6. Clean up memory
        if os.path.exists(video_path): os.remove(video_path)
        if os.path.exists(frame_path): os.remove(frame_path)
        
        return {"success": True, "link": original_link, "duration": original_duration}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
