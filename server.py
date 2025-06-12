from fastapi import FastAPI, Request, HTTPException, Depends,Body,APIRouter,HTTPException
import uvicorn
import openai
import os
import sys
from pydantic import BaseModel
from typing import Dict, Any, Optional, Union, List
import requests
from functools import lru_cache
import logging
from euriai import EuriaiClient





# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==== 🔐 Config ====
class Settings:
    def __init__(self):
        self.euriai_api_key = os.environ.get("EURIAI_API_KEY", "")
        self.google_api_key = os.environ.get("GOOGLE_API_KEY", "")
        self.search_engine_id = os.environ.get("SEARCH_ENGINE_ID", "")
        
        # Log configuration status (but don't expose actual keys)
        logger.info(f"EURIAI_API_KEY set: {'Yes' if self.euriai_api_key else 'No'}")
        logger.info(f"GOOGLE_API_KEY set: {'Yes' if self.google_api_key else 'No'}")
        logger.info(f"SEARCH_ENGINE_ID set: {'Yes' if self.search_engine_id else 'No'}")
        logger.info(f"Python version: {sys.version}")


@lru_cache()
def get_settings():
    return Settings()

# ==== 📋 Models ====
class BaseRequest(BaseModel):
    euriai_api_key: Optional[str] = None  # ✅ Changed from openai_api_key
    google_api_key: Optional[str] = None
    search_engine_id: Optional[str] = None


class ParseFileRequest(BaseRequest):
    file_path: str

class PlagiarismRequest(BaseRequest):
    text: str
    similarity_threshold: Optional[int] = 40

class GradeRequest(BaseModel):
    text: str
    rubric: str
    euriai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    search_engine_id: Optional[str] = None
    model: Optional[str] = "gpt-4.1-nano"   #changed class

class ErrorResponse(BaseModel):
    detail: str

class GradeResponse(BaseModel):
    grade: str

class PlagiarismResult(BaseModel):
    url: str
    similarity: int

class PlagiarismResponse(BaseModel):
    results: List[PlagiarismResult]

# ==== 🚀 FastAPI Setup ====
app = FastAPI(
    title="Assignment Grader API",
    description="API for parsing, grading, and checking plagiarism in academic assignments",
    version="1.0.0",
    responses={
        500: {"model": ErrorResponse}
    }
)

@app.get("/")
async def root():
    return {"message": "Assignment Grader API", "status": "running", "version": "1.0.0"}

# Helper function to get the effective API keys
# Helper function to get the effective API keys
def get_api_keys(request, settings):
    euriai_key = getattr(request, "euriai_api_key", None) or settings.euriai_api_key
    google_key = getattr(request, "google_api_key", None) or settings.google_api_key
    search_id = getattr(request, "search_engine_id", None) or settings.search_engine_id
    
    return {
        "euriai_api_key": euriai_key,
        "google_api_key": google_key,
        "search_engine_id": search_id
    }



# ==== 📄 File Parsing ====
async def parse_pdf(file_path: str) -> str:
    try:
        import fitz  # PyMuPDF - Import only when needed
        doc = fitz.open(file_path)
        return "\n".join([page.get_text() for page in doc])
    except ImportError:
        raise HTTPException(status_code=500, detail="PyMuPDF not installed. Install with 'pip install pymupdf'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing PDF: {str(e)}")

async def parse_docx(file_path: str) -> str:
    try:
        from docx import Document  # Import only when needed
        doc = Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    except ImportError:
        raise HTTPException(status_code=500, detail="python-docx not installed. Install with 'pip install python-docx'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing DOCX: {str(e)}")

@app.post("/tools/parse_file", response_model=str)
async def parse_file(request: ParseFileRequest, settings: Settings = Depends(get_settings)):
    try:
        file_path = request.file_path
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
            
        ext = os.path.splitext(file_path)[-1].lower()
        
        if ext == ".pdf":
            return await parse_pdf(file_path)
        elif ext == ".docx":
            return await parse_docx(file_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error parsing file: {str(e)}")

# ==== 📄 Plagiarism Checking ====
@app.post("/tools/check_plagiarism", response_model=PlagiarismResponse)
async def check_plagiarism(request: PlagiarismRequest, settings: Settings = Depends(get_settings)):
    try:
        # Get API keys
        keys = get_api_keys(request, settings)
        
        if not keys["google_api_key"] or not keys["search_engine_id"]:
            raise HTTPException(status_code=500, detail="Google API key or Search Engine ID not configured")
            
        from fuzzywuzzy import fuzz  # Import only when needed
        
        text = request.text
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
            
        # Take first 300 chars for the search query
        query = text[:300].replace("\n", " ").strip()
        
        url = f"https://www.googleapis.com/customsearch/v1"
        params = {
            "q": query,
            "key": keys["google_api_key"],
            "cx": keys["search_engine_id"]
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, 
                              detail=f"Google API error: {response.text}")
                              
        data = response.json()
        results = data.get("items", [])
        
        plagiarism_results = [
            PlagiarismResult(
                url=item["link"],
                similarity=fuzz.token_set_ratio(text, item.get("snippet", ""))
            )
            for item in results
        ]
        
        # Sort by similarity (highest first)
        plagiarism_results.sort(key=lambda x: x.similarity, reverse=True)
        
        # Filter by threshold if provided
        threshold = request.similarity_threshold or 0
        if threshold > 0:
            plagiarism_results = [r for r in plagiarism_results if r.similarity >= threshold]
        
        return PlagiarismResponse(results=plagiarism_results)
    except ImportError:
        raise HTTPException(status_code=500, detail="fuzzywuzzy not installed. Install with 'pip install fuzzywuzzy python-Levenshtein'")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking plagiarism: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error checking plagiarism: {str(e)}")

# ==== 📄 Grading Functions ====
async def call_euriai_api(prompt: str, api_key: str, model: str = "gpt-4.1-nano") -> str:
    if not api_key:
        raise HTTPException(status_code=500, detail="Euriai API key not configured")

    try:
        client = EuriaiClient(
            api_key=api_key,
            model=model  # Example: "gpt-4.1-nano" or "gemini-2.5-pro-exp-03-25"
        )

        response = client.generate_completion(
            prompt=prompt,
            temperature=0.5,
            max_tokens=1024
        )
        return response["choices"][0]["message"]["content"].strip()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Euriai API error: {str(e)}")

@app.post("/tools/grade_text", response_model=GradeResponse)
async def grade_text(request: GradeRequest, settings: Settings = Depends(get_settings)):
    try:
        text = request.text
        rubric = request.rubric
        model = request.model or "gpt-4.1-nano"  # Default Euriai model

        # Get API keys
        keys = get_api_keys(request, settings)

        if not text.strip() or not rubric.strip():
            raise HTTPException(status_code=400, detail="Text and rubric cannot be empty")

        if not keys["euriai_api_key"]:
            raise HTTPException(status_code=500, detail="Euriai API key not configured")

        # Create grading prompt
        prompt = f"""You are an academic grader. Grade the following assignment based on the rubric. 
Respond with only the grade:

Rubric: {rubric}

Assignment: {text}"""

        # Use Euriai API
        client = EuriaiClient(api_key=keys["euriai_api_key"], model=model)
        response = client.generate_completion(prompt=prompt, temperature=0.5, max_tokens=1024)
        grade = response["choices"][0]["message"]["content"].strip()

        return GradeResponse(grade=grade)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error grading text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error grading text: {str(e)}")

@app.post("/tools/generate_feedback", response_model=str)
async def generate_feedback(request: GradeRequest, settings: Settings = Depends(get_settings)):
    try:
        text = request.text
        rubric = request.rubric
        model = request.model or "gpt-4.1-nano"  # Euriai default model

        # Get API keys
        keys = get_api_keys(request, settings)

        if not text.strip() or not rubric.strip():
            raise HTTPException(status_code=400, detail="Text and rubric cannot be empty")

        if not keys["euriai_api_key"]:
            raise HTTPException(status_code=500, detail="Euriai API key not configured")

        # Construct the prompt
        prompt = f"""You are an academic reviewer. Provide detailed, constructive feedback on the following assignment based on the rubric.

Rubric: {rubric}

Assignment: {text}"""

        # Use Euriai Client
        client = EuriaiClient(api_key=keys["euriai_api_key"], model=model)
        response = client.generate_completion(
            prompt=prompt,
            temperature=0.7,
            max_tokens=1024
        )

        feedback = response["choices"][0]["message"]["content"].strip()
        return feedback

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating feedback: {str(e)}")


# ==== ✅ Support for alternative URL formats ====
@app.post("/tool/{tool_name}")
async def tool_endpoint_singular(tool_name: str, request: Request, settings: Settings = Depends(get_settings)):
    try:
        body = await request.json()
        
        if tool_name == "parse_file":
            req = ParseFileRequest(**body)
            return await parse_file(req, settings)
        elif tool_name == "check_plagiarism":
            req = PlagiarismRequest(**body)
            return await check_plagiarism(req, settings)
        elif tool_name == "grade_text":
            req = GradeRequest(**body)
            return await grade_text(req, settings)
        elif tool_name == "generate_feedback":
            req = GradeRequest(**body)
            return await generate_feedback(req, settings)
        else:
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in tool endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Support for /api/tools/ endpoint
@app.post("/api/tools/{tool_name}")
async def tool_endpoint_api(tool_name: str, request: Request, settings: Settings = Depends(get_settings)):
    return await tool_endpoint_singular(tool_name, request, settings)

#added

@app.post("/debug/check_keys")
async def check_keys_debug(request: Request, settings: Settings = Depends(get_settings)):
    try:
        body = await request.json()
        euriai = body.get("euriai_api_key") or settings.euriai_api_key
        google = body.get("google_api_key") or settings.google_api_key
        search = body.get("search_engine_id") or settings.search_engine_id

        return {
            "euriai_api_key_set": bool(euriai),
            "google_api_key_set": bool(google),
            "search_engine_id_set": bool(search)
        }
    except Exception as e:
        logger.error(f"Error in /debug/check_keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==== ✅ Run with uvicorn ====
if __name__ == "__main__":
    logger.info("🚀 Assignment Grader API running at http://127.0.0.1:8088")
    logger.info("📚 Available tools:")
    logger.info("   - /tools/parse_file")
    logger.info("   - /tools/check_plagiarism")
    logger.info("   - /tools/grade_text")
    logger.info("   - /tools/generate_feedback")
    logger.info("   - /debug/check_keys")
    logger.info("   - Alternative formats also supported: /tool/... and /api/tools/...")
    
    uvicorn.run(app, host="0.0.0.0", port=8088)
