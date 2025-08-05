from jose import jwt, JWTError
from dataclasses import dataclass
import uvicorn
from fastapi import FastAPI, Request, Depends, Response, status, UploadFile, File, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Form, Request
from fastapi import BackgroundTasks
from typing import List
from uuid import uuid4
from app.logger import Logger
import tempfile
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
from app.context_aware_summarizer import Summarizer
from app.rag_pipeline import RagPipeline
from app.models.models import QuestionAnswer, Challenges, WrongAnswer
from app.agent import QuizGeneratorAgent
from app. challenge_generator import ChallengeGenerator
from app.flash_card_agent import FlashCardAgent
from app.crud import CRUDOperations
from app.pdf_parser import PdfParser
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
    summarizer_model_name: str
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
        self.pdf_parser = PdfParser()
        self.summerizer = Summarizer(summarizer_model_name=self.summarizer_model_name)
        self.challenge_generator = ChallengeGenerator(logger=self.logger)
        self.flas_card_agent = FlashCardAgent(logger=self.logger)
        self.agent = QuizGeneratorAgent(self.rag_pipeline, retrieved_chunk_threshold_for_agent_quiz = self.retrieved_chunk_threshold_for_agent_quiz, logger=self.logger)
        self.chatbot = Chatbot(rag_pipeline=self.rag_pipeline, model_name=self.chatbot_model_name, temperature=self.temperature_for_chatbot, logger=self.logger)

        self.challenge_messages = []

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
        

        @self.app.get("/aboutme")
        async def base(request: Request):
            token = request.cookies.get("access_token")

            if token:
                return self.templates.TemplateResponse("aboutme.html", {"request": request})
            
            return self.templates.TemplateResponse("register.html", {"request": request})


        @self.app.post("/login")
        async def login_user(request: Request, email: str = Form(...), password: str = Form(...)):

            await self.crud.initialize()
            user = await self.crud.read_by_email(User, str(email))

            if not user or not verify_password(password, user.hashed_password):
                return self.templates.TemplateResponse("register.html", {"request": request, "error": "Invalid credentials"})

            token = create_access_token({"sub": str(user.id)})
            response = RedirectResponse("/main_page", status_code=status.HTTP_302_FOUND)
            response.set_cookie(key="access_token", value=token, httponly=True, max_age=9000)
            
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
            response.set_cookie(key="access_token", value=token, httponly=True, max_age=9000)
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
            return self.templates.TemplateResponse("register.html", {"request": request})
            
            
        @self.app.post("/add_youtube_transcript")
        async def add_youtube_transcript(request: Request, subject_id: str = Form(...), youtube_id: str = Form(...), language_code: str = Form(...)):

            token = request.cookies.get("access_token")
            if token:
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
            return self.templates.TemplateResponse("register.html", {"request": request})
            


        @self.app.post("/add_text_note")
        async def add_text_note(request:Request, subject_id: str = Form(...), note_text: str = Form(...)):
            token = request.cookies.get("access_token")

            if not token:
                return self.templates.TemplateResponse("register.html", {"request": request})
    
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
        async def upload_pdf(request: Request, subject_id: str = Form(...), pdf_file: UploadFile = File(...)):
            token = request.cookies.get("access_token")
            if not token:
                return self.templates.TemplateResponse("register.html", {"request": request})

            try:
                payload = verify_token_from_cookie(request)
                user_id = int(payload["sub"])

                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(await pdf_file.read())
                    tmp_path = tmp.name


                text = self.pdf_parser.parse(tmp_path)

                label = self.label_extractor.extract(subject_id, text)

                self.json_handler.add_note_to_subject(
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
                self.logger.error(f"PDF işleme hatası: {e}")
                raise HTTPException(status_code=500, detail=f"PDF işlenemedi: {str(e)}")
        

        @self.app.post("/ask-question")
        async def ask_question(request: Request):

            token = request.cookies.get("access_token")

            if not token:
                return self.templates.TemplateResponse("register.html", {"request": request})

            if token:
                payload = verify_token_from_cookie(request)
                user_id = int(payload["sub"])

                await self.crud.initialize()
                data = await request.json()
                subject_id = data.get("subject_id")
                question = data.get("question")

                if not subject_id or not question:
                    return {"error": "Subject ID ve soru gereklidir."}


                # Database'den kullanıcının son 3 soru-cevap çiftini getir
                context_aware = await self.crud.get_last_3_conversations_by_user(user_id)

                # BUrada bu context aware'i summarize edilir.
                summarized_context_aware = self.summerizer.sumarize(context_aware)

                self.logger.info(f"summarized context aware: {summarized_context_aware}")

                answer = self.chatbot.ask_question(
                    subject_id=subject_id,
                    question=question,
                    user_id=user_id,
                    summarized_context_aware = summarized_context_aware
                )


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
            token = request.cookies.get("access_token")
            
            if not token:
                print("Token cookie'de bulunamadı.")
                return self.templates.TemplateResponse("register.html", {"request": request})

            await self.crud.initialize()

            payload = verify_token_from_cookie(request)
            
            if payload is None:
                print("Token geçersiz ya da süresi dolmuş.")
                # Cookie'yi temizle (isteğe bağlı)
                response = self.templates.TemplateResponse("register.html", {
                    "request": request,
                    "message": "Oturum süreniz dolmuş. Lütfen tekrar giriş yapın."
                })
                response.delete_cookie("access_token")  # Güvenlik için
                return response

            user_id = int(payload["sub"])

            user = await self.crud.read_by_id(User, user_id)
            if user is None:
                print("Kullanıcı veritabanında bulunamadı.")
                return self.templates.TemplateResponse("error.html", {"request": request, "message": "Kullanıcı bulunamadı."})

            total_score = await self.crud.get_user_score_by_id(user_id)
            print(total_score)

            return self.templates.TemplateResponse("user_profile.html", {
                "request": request,
                "user_id": user_id,
                "email": user["name"],
                "total_score": total_score
            })




        @self.app.post("/generate_quiz")
        async def generate_quiz(request: Request):
            token = request.cookies.get("access_token")

            if not token:
                return self.templates.TemplateResponse("register.html", {"request": request})
            
            payload = verify_token_from_cookie(request)
            user_id = int(payload["sub"])
            
            data = await request.json()
            topic = data.get("user_input")
            result = self.agent.run(topic, user_id)

            return JSONResponse(content={"questions": result.get("questions", [])})

        @self.app.post("/evaluate_answer")
        async def evaluate_answer(request: Request):
            token = request.cookies.get("access_token")

            if not token:
                return self.templates.TemplateResponse("register.html", {"request": request})
            
            data = await request.json()
            question = data.get("question")
            answer = data.get("answer")
            correct_answer = data.get("correct_answer")

            print(f"question: {question}")
            print(f"answer: {answer}")

            payload = verify_token_from_cookie(request)
            user_id = int(payload["sub"])

            response = self.agent.evaluate(question, answer, correct_answer, user_id)


            return JSONResponse(content=response)
        

        @self.app.post("/save_wrong_answers")
        async def save_wrong_answers(request: Request, data: dict):
            token = request.cookies.get("access_token")

            if not token:
                return self.templates.TemplateResponse("register.html", {"request": request})
            
            await self.crud.initialize()
            wrong_answers_from_ui = data.get("wrong_answers", [])

            payload = verify_token_from_cookie(request)
            user_id = int(payload["sub"])

            if not user_id:
                return {"detail": "user_id eksik"}, 400

            for item in wrong_answers_from_ui:

                wrong_answer = WrongAnswer(
                    question=item["question"],
                    user_answer=item["selected_answer"],
                    correct_answer=item["correct_answer"],
                    user_id=user_id
                )
                
                await self.crud.create(wrong_answer)
            
            return JSONResponse(content={"backend": "success"})



        
        @self.app.get("/get_user_notes/{subject}")
        def get_user_notes_by_subject(request: Request, subject: str):

            token = request.cookies.get("access_token")

            if not token:
                return self.templates.TemplateResponse("register.html", {"request": request})
            
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
            token = request.cookies.get("access_token")

            if not token:
                return self.templates.TemplateResponse("register.html", {"request": request})
            
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
            
        
        # Kullanıcıya challenge mesajı gönder
        @self.app.post("/send_challenge")
        async def send_challenge(request: Request):
            token = request.cookies.get("access_token")

            if not token:
                return self.templates.TemplateResponse("register.html", {"request": request})
            
            await self.crud.initialize()

            payload = verify_token_from_cookie(request)
            challenge_sender_id = int(payload["sub"])
            data = await request.json()

            challenge_receiver_user_email = data.get("email")
            challenge_topic = data.get("topic")

            # Quiz json oluştur
            challenge_quiz_json = self.challenge_generator.run(challenge_topic, challenge_sender_id)

            # Kullanıcı kontrolü
            challenge_receiver_user = await self.crud.read_by_email(User, challenge_receiver_user_email)
            if not challenge_receiver_user:
                return JSONResponse(status_code=404, content={"message": "Bu e-posta adresine sahip kullanıcı bulunamadı."})

            # Challenge objesi oluştur
            challenge = Challenges(
                challenge_sender_id=challenge_sender_id,
                challenge_receiver_id=challenge_receiver_user.id,
                quiz_json=challenge_quiz_json,
                sender_answer_for_challenge=None,
                receiver_answer_for_challenge=None,
                accepted_receiver=False
            )

            # DB'ye yaz ve ID’yi al
            created_challenge = await self.crud.create_challenge(challenge)

            return JSONResponse(content={
                "message": "Challenge oluşturuldu.",
                "challenge_id": created_challenge.id,
                "quiz": challenge_quiz_json
            })
        


        @self.app.get("/get_challenges")
        async def get_challenges(request: Request):
            await self.crud.initialize()
            payload = verify_token_from_cookie(request)
            user_id = int(payload["sub"])

            filters = {
                "challenge_receiver_id": user_id,
                "accepted_receiver": False
            }
            incoming_challenges = await self.crud.read_challenges(filters=filters)

            self.logger.info(f"gelen challengelar: {incoming_challenges}")

            challenges_list = []
            for c in incoming_challenges:
                try:
                    # Eğer quiz_json string olarak kaydedildiyse, dict'e çevir:
                    quiz = c.quiz_json
                    if isinstance(quiz, str):
                        quiz = json.loads(quiz)

                    question = quiz.get("questions", [])[0].get("question", "Bilinmeyen Konu")

                except Exception as e:
                    self.logger.error(f"Challenge sorusu parse edilemedi: {e}")
                    question = "Bilinmeyen Konu"

                challenges_list.append({
                    "id": c.id,
                    "topic": question
                })

            self.logger.info(f"challenge list: {challenges_list}")

            return JSONResponse(content={"challenges": challenges_list})
        

        @self.app.post("/accept_challenge")
        async def accept_challenge(request: Request):
            token = request.cookies.get("access_token")

            if not token:
                return self.templates.TemplateResponse("register.html", {"request": request})
            
            await self.crud.initialize()
            payload = verify_token_from_cookie(request)
            user_id = int(payload["sub"])

            data = await request.json()
            challenge_id = int(data.get("id"))

            challenge = await self.crud.read_challenge_by_id(challenge_id)

            if not challenge or challenge.challenge_receiver_id != user_id:
                return JSONResponse(status_code=403, content={"message": "Bu challenge size ait değil."})

            challenge.accepted_receiver = True
            await self.crud.update_challenge(challenge)

            # Quiz sorularını geri dön
            quiz_json = challenge.quiz_json
            if isinstance(quiz_json, str):
                quiz_json = json.loads(quiz_json)

            return JSONResponse(content={
                "message": "Challenge kabul edildi!",
                "quiz_match_id": challenge_id,
                "quiz": quiz_json,
                "role": "receiver"
            })

        


        @self.app.post("/reject_challenge")
        async def reject_challenge(request: Request):
            token = request.cookies.get("access_token")

            if not token:
                return self.templates.TemplateResponse("register.html", {"request": request})

            await self.crud.initialize()
            payload = verify_token_from_cookie(request)
            user_id = int(payload["sub"])
            
            data = await request.json()
            challenge_id = int(data.get("id"))

            challenge = await self.crud.read_challenge_by_id(challenge_id)

            if not challenge or challenge.challenge_receiver_id != user_id:
                return JSONResponse(status_code=403, content={"message": "Bu challenge size ait değil."})

            await self.crud.delete_challenge_by_id(challenge_id)

            return JSONResponse(content={"message": "Challenge reddedildi."})



        @self.app.post("/submit_challenge_answers")
        async def submit_challenge_answers(request: Request):
            token = request.cookies.get("access_token")

            if not token:
                return self.templates.TemplateResponse("register.html", {"request": request})
            
            await self.crud.initialize()
            payload = verify_token_from_cookie(request)
            user_id = int(payload["sub"])

            data = await request.json()
            challenge_id = data.get("challenge_id")
            answers = data.get("answers")
            role = data.get("role")  # "sender" veya "receiver"

            if not challenge_id or not answers or role not in ["sender", "receiver"]:
                raise HTTPException(status_code=400, detail="Eksik ya da hatalı veri.")

            challenge = await self.crud.read_challenge_by_id(challenge_id)
            if not challenge:
                raise HTTPException(status_code=404, detail="Challenge bulunamadı.")

            # Doğrulama: role ile user_id eşleşiyor mu
            if role == "sender":
                print(role)
                if challenge.challenge_sender_id != user_id:
                    raise HTTPException(status_code=403, detail="Gönderici siz değilsiniz.")
                challenge.sender_answer_for_challenge = json.dumps(answers)

            elif role == "receiver":
                print(role)
                if challenge.challenge_receiver_id != user_id:
                    raise HTTPException(status_code=403, detail="Alıcı siz değilsiniz.")
                challenge.receiver_answer_for_challenge = json.dumps(answers)

            await self.crud.update_challenge(challenge)

            # Her iki taraf cevapladıysa puan hesapla ve kaydet
            if challenge.sender_answer_for_challenge and challenge.receiver_answer_for_challenge:
                sender_answers = json.loads(challenge.sender_answer_for_challenge)
                receiver_answers = json.loads(challenge.receiver_answer_for_challenge)
                quiz = challenge.quiz_json if isinstance(challenge.quiz_json, dict) else json.loads(challenge.quiz_json)
                corrects = [q["correct_answer"] for q in quiz["questions"]]

                sender_score = sum([1 for s, c in zip(sender_answers, corrects) if s == c])
                receiver_score = sum([1 for r, c in zip(receiver_answers, corrects) if r == c])

                # Puanlama
                if sender_score > receiver_score:
                    print("sender_score > receiver score")
                    await self.crud.update_user_score(challenge.challenge_sender_id, 10)
                elif sender_score < receiver_score:
                    print("sender_score < receiver score")
                    await self.crud.update_user_score(challenge.challenge_receiver_id, 10)
                else:
                    print("sender_score = receiver score")
                    await self.crud.update_user_score(challenge.challenge_sender_id, 1)
                    await self.crud.update_user_score(challenge.challenge_receiver_id, 1)

            return JSONResponse(content={"message": f"{role} cevabı başarıyla kaydedildi."})



        @self.app.get("/get_challenge_messages")
        async def get_challenge_messages(request: Request):
            await self.crud.initialize()
            payload = verify_token_from_cookie(request)
            user_id = int(payload["sub"])

            # Sender veya Receiver olduğu tüm challenge'ları al
            all_challenges = await self.crud.read_challenges_for_user(user_id)

            messages = []
            for ch in all_challenges:
                if not ch.sender_answer_for_challenge or not ch.receiver_answer_for_challenge:
                    continue  # Her iki taraf da cevaplamamışsa geç

                sender_answers = json.loads(ch.sender_answer_for_challenge)
                receiver_answers = json.loads(ch.receiver_answer_for_challenge)
                quiz = ch.quiz_json if isinstance(ch.quiz_json, dict) else json.loads(ch.quiz_json)
                corrects = [q["correct_answer"] for q in quiz["questions"]]

                sender_score = sum([1 for s, c in zip(sender_answers, corrects) if s == c])
                receiver_score = sum([1 for r, c in zip(receiver_answers, corrects) if r == c])

                # Rakibin e-mailini al
                opponent_id = ch.challenge_receiver_id if ch.challenge_sender_id == user_id else ch.challenge_sender_id
                opponent = await self.crud.read_by_id(User, opponent_id)
                opponent_email = opponent["name"] if opponent else "Bilinmeyen"

                if user_id == ch.challenge_sender_id:
                    user_score = sender_score
                    opponent_score = receiver_score
                else:
                    user_score = receiver_score
                    opponent_score = sender_score

                if user_score > opponent_score:
                    outcome = f"{opponent_email} kişisiyle yaptığınız düellodan galip ayrıldınız! +10 puan ✅ ({user_score} - {opponent_score})"
                elif user_score == opponent_score:
                    outcome = f"{opponent_email} ile berabere kaldınız. +1 puan 🤝 ({user_score} - {opponent_score})"
                else:
                    outcome = f"{opponent_email} karşısında maalesef kaybettiniz. 0 puan ❌ ({user_score} - {opponent_score})"

                messages.append(outcome)

            return JSONResponse(content={"messages": messages})


        @self.app.get("/get_global_ranking")
        async def get_global_ranking():
            await self.crud.initialize()
            top_users = await self.crud.get_top_users_by_score(limit=5)
            return top_users
        

        @self.app.get("/get_flashcards")
        async def get_flashcards(request: Request):
            token = request.cookies.get("access_token")
            if not token:
                return self.templates.TemplateResponse("register.html", {"request": request})

            await self.crud.initialize()
            payload = verify_token_from_cookie(request)
            user_id = int(payload["sub"])

            flashcards = await self.crud.get_last_wrong_answers(user_id=user_id)
            
            flashcard_dicts = [
                {
                    "question": f.question,
                    "user_answer": f.user_answer,
                    "correct_answer": f.correct_answer
                }
                for f in flashcards
            ]

            explanations = self.flas_card_agent.generate_advice_for_wrong_answers(flashcard_dicts)

            # Frontend için birleşik JSON
            return JSONResponse(content={
                "flashcards": [
                    {**card, "explanation": explanation}
                    for card, explanation in zip(flashcard_dicts, explanations)
                ]
            })


        @self.app.get("/logout")
        async def logout_user():
            response = RedirectResponse("/", status_code=status.HTTP_302_FOUND)
            response.delete_cookie(key="access_token")
            return response



if __name__ == "__main__":

    pass