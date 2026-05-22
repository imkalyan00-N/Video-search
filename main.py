from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
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
    <title>Deep Photo Search Engine</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-white flex items-center justify-center min-h-screen p-4">
    <div class="bg-gray-800 p-8 rounded-lg shadow-lg w-full max-w-2xl text-center border border-gray-700">
        <h1 class="text-3xl font-bold mb-2 text-indigo-400">Deep Photo Search</h1>
        <p class="text-gray-400 text-sm mb-6">Upload an image to find ALL related video/web links across the internet</p>
        
        <input type="file" id="imageInput" accept="image/*" 
            class="mb-4 block w-full text-sm text-gray-400 
            file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 
            file:text-sm file:font-bold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500" />
            
        <button onclick="uploadImage()" id="searchBtn" 
            class="bg-indigo-500 hover:bg-indigo-600 transition text-white font-bold py-2 px-4 rounded w-full">
            🔍 Deep Search Now
        </button>

        <div id="loading" class="mt-6 text-yellow-400 hidden animate-pulse font-medium">
            ⏳ Scanning the deep web for matches...
        </div>

        <div id="result" class="mt-6 text-left hidden bg-gray-900 p-4 rounded-md border border-green-500/30">
            <p class="text-green-400 font-bold mb-4 flex items-center">✅ Matches Found!</p>
            <ul id="linksList" class="list-disc pl-5 space-y-2 text-sm">
                </ul>
        </div>
    </div>

    <script>
        async function uploadImage() {
            const fileInput = document.getElementById('imageInput');
            if (!fileInput.files[0]) return alert("Please select an image file!");
            
            document.getElementById('loading').classList.remove('hidden');
            document.getElementById('result').classList.add('hidden');
            document.getElementById('linksList').innerHTML = '';
            document.getElementById('searchBtn').disabled = true;

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            try {
                const response = await fetch('/search', { method: 'POST', body: formData });
                const data = await response.json();
                
                if(data.success) {
                    if(data.links.length === 0) {
                        document.getElementById('linksList').innerHTML = '<li class="text-red-400">No deep links found. Try another image.</li>';
                    } else {
                        data.links.forEach(item => {
                            const li = document.createElement('li');
                            li.innerHTML = `<a href="${item.url}" target="_blank" class="text-blue-400 hover:text-blue-300 underline break-words"><b>${item.title}</b><br><span class="text-xs text-gray-500">${item.url}</span></a>`;
                            document.getElementById('linksList').appendChild(li);
                        });
                    }
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
async def process_and_search_image(file: UploadFile = File(...)):
    try:
        # 1. Read the uploaded image directly into memory
        image_bytes = await file.read()
        
        # 2. Upload image to ImgBB
        imgbb_api_key = "2004d341fc8640cc32f3f188daf97b53"
        img_response = requests.post(
            f"https://api.imgbb.com/1/upload?key={imgbb_api_key}",
            files={"image": (file.filename, image_bytes)}
        ).json()
            
        if "data" not in img_response:
            return {"success": False, "error": "Image upload failed"}
            
        public_image_url = img_response["data"]["url"]

        # 3. Deep Search on Google Lens using SerpApi
        serpapi_key = "723413977cdcd590c3d07450921efa5dee502ed3d5706e9502848459c04f575c"
        search_params = {
            "engine": "google_lens",
            "url": public_image_url,
            "api_key": serpapi_key
        }
        
        lens_response = requests.get("https://serpapi.com/search.json", params=search_params).json()

        # 4. Extract ALL unique visual matches (Top 10-15 results)
        collected_links = []
        seen_urls = set()
        
        if "visual_matches" in lens_response:
            for match in lens_response["visual_matches"]:
                url = match.get("link", "")
                title = match.get("title", "No Title Available")
                
                # Check if it's a valid link and not duplicate
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    collected_links.append({"title": title, "url": url})
                    
                # Limit to top 15 deep links to avoid overloading the UI
                if len(collected_links) >= 15:
                    break
        
        return {"success": True, "links": collected_links}
        
    except Exception as e:
        return {"success": False, "error": str(e)}
