from jose import jwt, JWTError
from dataclasses import dataclass
import uvicorn
from fastapi import FastAPI, Request, Depends, Response, status, UploadFile, File, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Form, Request
from app.logger import Logger
from app.utils import verify_password, hash_password, create_access_token
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from app.video_transcriper import VideoTranscript
from app.json_handler import JsonHandler
from app.regex import regex_for_id_extracting_from_the_link
from urllib.parse import urlencode
from app.label_extractor_from_video import LabelExtractor
from app.rag_pipeline import RagPipeline
from app.crud import CRUDOperations
from app.models.models import User

@dataclass
class FastAPIServer:
    database_type: str
    host: str
    port: int
    reload: bool
    log_level: str
    crud: CRUDOperations
    transcripter: VideoTranscript
    label_extractor: LabelExtractor
    json_handler: JsonHandler
    rag_pipeline: RagPipeline
    logger: Logger

    def __post_init__(self):
        self.app = FastAPI()
        #self.crud = CRUDOperations(self.database_type, )
        self.templates = Jinja2Templates(directory="app/templates")
        self.app.mount(f"/static", StaticFiles(directory="app/static"), name="static")
        self.logger.info("Fastapi init")

        self.subject_map = {
            "matematik": "Matematik",
            "biyoloji": "Biyoloji",
            "fizik": "Fizik",
            "kimya": "Kimya",
            "turkce": "Türkçe",
            "tarih": "Tarih",
            "cografya": "Coğrafya",
            "geometri": "Geometri",
            "edebiyat": "Edebiyat",
            "din": "Din Kültürü",
            "felsefe":"Felsefe"
        }

    def run(self):
        self.server()
        self.logger.info("Server Initialized!")
        uvicorn.run(app=self.app, host=self.host, port=self.port, log_level=self.log_level)

    def server(self):
        @self.app.get("/")
        async def base(request: Request):
            token = request.cookies.get("access_token")

            if token:
                return self.templates.TemplateResponse("main_page.html", {"request": request})
            
            return self.templates.TemplateResponse("register.html", {"request": request})


        @self.app.post("/login")
        async def login_user(request: Request, email: str = Form(...), password: str = Form(...)):

            await self.crud.initialize()
            user = await self.crud.read_by_email(User, str(email))

            if not user or not verify_password(password, user.hashed_password):
                return self.templates.TemplateResponse("register.html", {"request": request, "error": "Invalid credentials"})

            token = create_access_token({"sub": str(user.id)})
            response = RedirectResponse("/main_page", status_code=status.HTTP_302_FOUND)
            response.set_cookie(key="access_token", value=token, httponly=True, max_age=900)
            
            return response
        
        @self.app.get("/main_page")
        async def get_main_page(request: Request):
            token = request.cookies.get("access_token")
            
            if token:
                return self.templates.TemplateResponse("main_page.html", {"request": request})
            
            return self.templates.TemplateResponse("register.html", {"request": request, "error": "Invalid credentials"})
            

        @self.app.post("/register")
        async def register_user(request: Request,email: str = Form(...),username: str = Form(...),password: str = Form(...)):
            await self.crud.initialize()

            user_exist = await self.crud.read_by_email(User, email)
            if user_exist:
                return self.templates.TemplateResponse("register.html", {"request": request, "error": "Username already exists"})

            user = User(
                email=email,
                username=username,
                hashed_password=hash_password(password)
            )
            await self.crud.create(user)

            token = create_access_token({"sub": str(user.id)})
            response = RedirectResponse("/main_page", status_code=status.HTTP_302_FOUND)
            response.set_cookie(key="access_token", value=token, httponly=True, max_age=900)
            return response
        
        @self.app.get("/subject", response_class=HTMLResponse)
        async def subject_page(request: Request, subject: str, success: str = None):
            token = request.cookies.get("access_token")
            if token:
                subject_name = self.subject_map.get(subject, "Bilinmeyen Ders")
                return self.templates.TemplateResponse("subject.html", {
                    "request": request,
                    "subject_id": subject,
                    "subject_name": subject_name,
                    "success": success
                })
            return self.templates.TemplateResponse("main_page.html", {"request": request})
            
            
        @self.app.post("/add_youtube_transcript")
        async def add_youtube_transcript(subject_id: str = Form(...), youtube_id: str = Form(...), language_code: str = Form(...)):

            video_id = regex_for_id_extracting_from_the_link(youtube_id)

            text = self.transcripter.transcript(video_id, language_code)

            self.logger.info(f"video transcript result:  {text}")

            label = self.label_extractor.extract(subject_id, text)

            try:
                saved_note = self.json_handler.add_note_to_subject(
                    subject_id=subject_id,
                    label=label,
                    note_text=text
                )

                note_chunks = self.rag_pipeline.load_notes(f"app/data/{subject_id}.json", subject_id= subject_id)
                self.rag_pipeline.update_vector_db(note_chunks)

                params = urlencode({"subject": subject_id, "success": "1"})
                return RedirectResponse(url=f"/subject?{params}", status_code=303)

            except Exception as e:
                self.logger.error(f"Error processing note for subject_id '{subject_id}': {e}")
                raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
            


        @self.app.post("/add_text_note")
        async def add_text_note(request:Request, subject_id: str = Form(...), note_text: str = Form(...)):
            token = request.cookies.get("access_token")
            if not token:
                raise HTTPException(status_code=401, detail="Unauthorized: No access token provided.")
    
            try:

                label = self.label_extractor.extract(subject_id, note_text)
                
                # Bu method öğrenci ders ile ilgili veri eklediğinde o dersin .json dosyasına label olarak yeni note verisi ekler.
                saved_note = self.json_handler.add_note_to_subject(
                    subject_id=subject_id,
                    label=label,
                    note_text=note_text
                )

                # Bu method; öğrenci tarafından yeni bir veri eklendiğinde vector database'i günceller.
                note_chunks = self.rag_pipeline.load_notes(f"app/data/{subject_id}.json", subject_id= subject_id)
                self.rag_pipeline.update_vector_db(note_chunks)

                
                params = urlencode({"subject": subject_id, "success": "1"})
                return RedirectResponse(url=f"/subject?{params}", status_code=303)
            
            except Exception as e:
                self.logger.error(f"Error processing note for subject_id '{subject_id}': {e}")
                raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
            

        @self.app.post("/upload_pdf")
        async def upload_pdf(subject_id: str = Form(...), pdf_file: UploadFile = File(...)):
            content = await pdf_file.read()
            # text = extract_text_from_pdf(content)  # OCR veya pdfplumber ile
            text = ""
            # text → vector db'ye subject_id ile kaydedilir
            return RedirectResponse(url=f"/subject?subject={subject_id}", status_code=303)
        

        @self.app.post("/ask-question")
        async def ask_question():
            pass


        @self.app.get("/logout")
        async def logout_user():
            response = RedirectResponse("/", status_code=status.HTTP_302_FOUND)
            response.delete_cookie(key="access_token")
            return response



if __name__ == "__main__":

    pass