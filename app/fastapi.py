from jose import jwt, JWTError
from dataclasses import dataclass
import uvicorn
from fastapi import FastAPI, Request, Depends, Response, status, UploadFile, File, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Form, Request
from app.logger import Logger
import os
import json
from app.utils import verify_password, hash_password, create_access_token
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from app.video_transcriper import VideoTranscript
from app.json_handler import JsonHandler
from app.regex import regex_for_id_extracting_from_the_link
from urllib.parse import urlencode
from app.label_extractor_from_video import LabelExtractor
from app.utils import verify_password, verify_token_from_cookie
from app.chatbot import Chatbot
from app.rag_pipeline import RagPipeline
from app.models.models import QuestionAnswer
from app.agent import QuizGeneratorAgent
from app.crud import CRUDOperations
from app.models.models import User

@dataclass
class FastAPIServer:
    database_type: str
    host: str
    port: int
    reload: bool
    log_level: str
    chatbot_model_name: str
    temperature_for_chatbot: float
    crud: CRUDOperations
    transcripter: VideoTranscript
    label_extractor: LabelExtractor
    json_handler: JsonHandler
    rag_pipeline: RagPipeline
    logger: Logger
    retrieved_chunk_threshold_for_agent_quiz: float = 0.7


    def __post_init__(self):
        self.app = FastAPI()
        #self.crud = CRUDOperations(self.database_type, )
        self.templates = Jinja2Templates(directory="app/templates")
        self.app.mount(f"/static", StaticFiles(directory="app/static"), name="static")
        self.logger.info("Fastapi init")
        self.agent = QuizGeneratorAgent(self.rag_pipeline, retrieved_chunk_threshold_for_agent_quiz = self.retrieved_chunk_threshold_for_agent_quiz, logger=self.logger)
        self.chatbot = Chatbot(rag_pipeline=self.rag_pipeline, model_name=self.chatbot_model_name, temperature=self.temperature_for_chatbot, logger=self.logger)

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
        async def add_youtube_transcript(request: Request, subject_id: str = Form(...), youtube_id: str = Form(...), language_code: str = Form(...)):

            video_id = regex_for_id_extracting_from_the_link(youtube_id)

            text = self.transcripter.transcript(video_id, language_code)

            self.logger.info(f"video transcript result:  {text}")

            label = self.label_extractor.extract(subject_id, text)

            try:
                payload = verify_token_from_cookie(request)
                user_id = int(payload["sub"])

                saved_note = self.json_handler.add_note_to_subject(
                    subject_id=subject_id,
                    user_id=user_id,
                    label=label,
                    note_text=text
                )

                note_chunks = self.rag_pipeline.load_notes(f"app/data/{subject_id}_{user_id}.json", subject_id=subject_id, user_id=user_id)

                self.rag_pipeline.update_vector_db(note_chunks, user_id=user_id)

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
                payload = verify_token_from_cookie(request)
                user_id = int(payload["sub"])

                label = self.label_extractor.extract(subject_id, note_text)
                
                # Bu method öğrenci ders ile ilgili veri eklediğinde o dersin .json dosyasına label olarak yeni note verisi ekler.
                saved_note = self.json_handler.add_note_to_subject(
                    subject_id=subject_id,
                    user_id=user_id,
                    label=label,
                    note_text=note_text
                )

                # Bu method; öğrenci tarafından yeni bir veri eklendiğinde vector database'i günceller.
                note_chunks = self.rag_pipeline.load_notes(f"app/data/{subject_id}_{user_id}.json", subject_id=subject_id, user_id=user_id)

                self.rag_pipeline.update_vector_db(note_chunks, user_id=user_id)

                
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
        async def ask_question(request: Request):

            token = request.cookies.get("access_token")

            if token:
                payload = verify_token_from_cookie(request)
                user_id = int(payload["sub"])

                await self.crud.initialize()
                data = await request.json()
                subject_id = data.get("subject_id")
                question = data.get("question")

                if not subject_id or not question:
                    return {"error": "Subject ID ve soru gereklidir."}

                # Cevabı üret

                # Bunları bir metne çevir

                # Chatbot'a ver
                answer = self.chatbot.ask_question(
                    subject_id=subject_id,
                    question=question,
                    user_id=user_id,
                )


                payload = verify_token_from_cookie(request)
                user_id = int(payload["sub"])

                question_answer = QuestionAnswer(
                    user_id=user_id,
                    question=question,
                    answer=answer
                )

                await self.crud.create(question_answer)

                return {"answer": answer}
            raise HTTPException(status_code=401, detail="Unauthorized: No access token provided.")

        
        @self.app.get("/profile")
        async def get_profile_html(request: Request):
            await self.crud.initialize()
            try:
                payload = verify_token_from_cookie(request)
                user_id = int(payload["sub"])

                # Veritabanından kullanıcı bilgilerini al
                user = await self.crud.read_by_id(User, user_id)
                print(user)

                if user is None:
                    return self.templates.TemplateResponse("error.html", {"request": request, "message": "Kullanıcı bulunamadı."})

                return self.templates.TemplateResponse("user_profile.html", {
                    "request": request,
                    "user_id": user_id,
                    "email": user["name"]
                })

            except Exception as e:
                return self.templates.TemplateResponse("error.html", {"request": request, "message": str(e)})


        @self.app.post("/generate_quiz")
        async def generate_quiz(request: Request):
            payload = verify_token_from_cookie(request)
            user_id = int(payload["sub"])
            
            data = await request.json()
            topic = data.get("user_input")
            result = self.agent.run(topic, user_id)

            return JSONResponse(content={"questions": result.get("questions", [])})

        @self.app.post("/evaluate_answer")
        async def evaluate_answer(request: Request):
            data = await request.json()
            question = data.get("question")
            answer = data.get("answer")
            correct_answer = data.get("correct_answer")

            print(f"question: {question}")
            print(f"answer: {answer}")

            payload = verify_token_from_cookie(request)
            user_id = str(payload["sub"])

            response = self.agent.evaluate(question, answer, correct_answer, user_id)

            return JSONResponse(content=response)


        
        @self.app.get("/get_user_notes/{subject}")
        def get_user_notes_by_subject(request: Request, subject: str):
            payload = verify_token_from_cookie(request)
            user_id = int(payload["sub"])
            notes = []

            # Eğer subject "all" ise tüm ders dosyalarını tara
            if subject == "all":
                directory = "app/data"
                for file in os.listdir(directory):
                    if file.endswith(f"_{user_id}.json"):
                        current_subject = file.split("_")[0]
                        file_path = os.path.join(directory, file)
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                entries = json.load(f)
                                for entry in entries:
                                    entry["subject"] = current_subject
                                    notes.append(entry)
                        except Exception:
                            continue
            else:
                # Belirli bir ders için
                file_path = f"app/data/{subject}_{user_id}.json"
                if os.path.exists(file_path):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            entries = json.load(f)
                            for entry in entries:
                                entry["subject"] = subject
                                notes.append(entry)
                    except Exception:
                        pass

            return JSONResponse(content={"notes": notes})
        

        @self.app.delete("/delete_note/{subject}/{note_id}")
        async def delete_note(subject: str, note_id: int, request: Request):
            try:
                payload = verify_token_from_cookie(request)
                user_id = int(payload["sub"])

                filename = f"app/data/{subject}_{user_id}.json"
                if not os.path.exists(filename):
                    raise HTTPException(status_code=404, detail="Not dosyası bulunamadı.")

                with open(filename, "r", encoding="utf-8") as f:
                    notes = json.load(f)

                updated_notes = [note for note in notes if note["id"] != note_id]

                if len(updated_notes) == len(notes):
                    raise HTTPException(status_code=404, detail="Not bulunamadı.")

                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(updated_notes, f, ensure_ascii=False, indent=2)

                return JSONResponse(content={"success": True, "message": "Not silindi."})

            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        



        @self.app.get("/logout")
        async def logout_user():
            response = RedirectResponse("/", status_code=status.HTTP_302_FOUND)
            response.delete_cookie(key="access_token")
            return response



if __name__ == "__main__":

    pass