from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.connection import Connection
from typing import Union
from app.logger import Logger
from sqlalchemy import select, desc
from app.models.models import QuestionAnswer, Challenges, UserScore, User, WrongAnswer
from app.handler import custom_db_crud_handler
import asyncio


@dataclass
class CRUDOperations:

    database_type: str
    db_username: str
    db_password: str
    db_host: str
    db_port: str
    db_name: str
    logger: Logger

    async def initialize(self):
        self.connection = Connection(database_type = self.database_type,
                                     db_username = self.db_username,
                                     db_password = self.db_password,
                                     db_host = self.db_host,
                                     db_port = self.db_port,
                                     db_name = self.db_name,
                                     logger = self.logger)
        await self.connection.create_engine()
        await self.connection.connect()
        await self.connection.create_session()

    @custom_db_crud_handler
    async def create(self, obj: any) -> bool:
        """
        Adds the given object to the database asynchronously.

        Args:
            obj (any): The object to be added to the database.

        Returns:
            bool: True if the operation is successful, False if an error occurs.
        """
        self.connection.session.add(obj)
        await self.connection.session.commit()
        self.logger.info(f"the data: {obj} is added into the database.")

    
    @custom_db_crud_handler
    async def create_challenge(self, challenge: Challenges) -> Challenges:
        """
        Creates a new Challenge entry in the database and returns the object with ID.

        Args:
            challenge (Challenges): The challenge instance to add.

        Returns:
            Challenges: The created challenge with ID populated.
        """
        self.connection.session.add(challenge)
        await self.connection.session.commit()
        await self.connection.session.refresh(challenge)  # Challenge nesnesine ID'yi yükler
        self.logger.info(f"Challenge created: {challenge}")
        return challenge
    

    @custom_db_crud_handler
    async def update_challenge(self, challenge: Challenges) -> bool:
        """
        Updates a Challenge entry in the database.

        Args:
            challenge (Challenges): The challenge object with updated fields.

        Returns:
            bool: True if successful, False otherwise.
        """
        await self.connection.session.merge(challenge)  # Merge güncel halini DB’ye yazar
        await self.connection.session.commit()
        self.logger.info(f"Challenge updated successfully: ID {challenge.id}")
        return True


    @custom_db_crud_handler
    async def read_by_id(self, model: any, obj_id: int) -> Union[bool, dict]:
        """
        Retrieves a record from the database by its ID asynchronously.

        Args:
            model (any): The model to query.
            obj_id (int): The ID of the object to retrieve.

        Returns:
            Union[bool, dict]: The retrieved object if found, or False if an error occurs.
        """
        result = await self.connection.session.get(model, obj_id)
        await self.connection.close_session()
        self.logger.info(f"Data read successfully: {result.to_dict()}")
        return result.to_dict()
    
    @custom_db_crud_handler
    async def read_challenge_by_id(self, challenge_id: int):
        """
        Retrieves a Challenge object by its ID.

        Args:
            challenge_id (int): The ID of the challenge.

        Returns:
            Challenges | None: The Challenge object if found, None otherwise.
        """
        challenge = await self.connection.session.get(Challenges, challenge_id)
        await self.connection.close_session()

        if challenge:
            self.logger.info(f"Challenge found: {challenge}")
        else:
            self.logger.info(f"No challenge found with ID: {challenge_id}")

        return challenge


    @custom_db_crud_handler
    async def read_all(self, model: any) -> Union[list, bool]:
        """
        Retrieves all records of the given model asynchronously.

        Args:
            model (any): The model to query.

        Returns:
            Union[list, bool]: A list of retrieved objects if successful, or False if an error occurs.
        """
        result = await self.connection.session.execute(model.__table__.select())
        await self.connection.close_session()
        self.logger.info(f"Data read successfully: {result.to_dict()}")
        return result.all()

    @custom_db_crud_handler
    async def update(self, model: any, obj_id: int, new_data: dict) -> bool:
        """
        Updates a record in the database based on its ID asynchronously.

        Args:
            model (any): The model in which the record exists.
            obj_id (int): The ID of the object to be updated.
            new_data (dict): The new data containing updated values.

        Returns:
            bool: True if the update is successful, False if an error occurs.
        """
        new_data = new_data.to_dict()
        object_will_be_change = await self.connection.session.get(model, obj_id)

        if object_will_be_change is None:
            self.logger.info("Object not found.")
            return False

        for key, value in new_data.items():
            setattr(object_will_be_change, key, value)

        await self.connection.session.commit()
        await self.connection.close_session()
        self.logger.info(f"Data is updated successfully from: {object_will_be_change.to_dict()}, to: {new_data}")

    @custom_db_crud_handler
    async def delete_by_id(self, model: any, obj_id: int) -> bool:
        """
        Deletes a record from the database based on its ID asynchronously.

        Args:
            model (any): The model from which the record should be deleted.
            obj_id (int): The ID of the object to delete.

        Returns:
            bool: True if the deletion is successful, False if an error occurs.
        """
        obj = await self.connection.session.get(model, obj_id)
        if obj:
            await self.connection.session.delete(obj)
            await self.connection.session.commit()
            self.logger.info(f"Data is deleted successfully: {obj.to_dict()}")
            return True
        else:
            self.logger.info(f"Could not find any record with ID {obj_id}")
            return False
    
    @custom_db_crud_handler
    async def delete_challenge_by_id(self, challenge_id: int) -> bool:
        """
        Deletes a Challenge record by its ID.

        Args:
            challenge_id (int): ID of the challenge to delete.

        Returns:
            bool: True if deleted, False if not found or failed.
        """
        challenge = await self.connection.session.get(Challenges, challenge_id)
        
        if challenge:
            await self.connection.session.delete(challenge)
            await self.connection.session.commit()
            await self.connection.close_session()
            self.logger.info(f"Challenge deleted successfully: ID {challenge_id}")
            return True
        else:
            self.logger.info(f"No Challenge found with ID {challenge_id}")
            await self.connection.close_session()
            return False
        
    
    @custom_db_crud_handler
    async def mark_challenge_as_accepted(self, challenge_id: int, user_id: int) -> bool:
        """
        Marks a challenge as accepted by receiver if the user is the receiver.

        Args:
            challenge_id (int): ID of the challenge to accept.
            user_id (int): ID of the receiver (for validation).

        Returns:
            bool: True if successfully marked, False otherwise.
        """
        stmt = select(Challenges).where(Challenges.id == challenge_id)
        result = await self.connection.session.execute(stmt)
        challenge = result.scalar_one_or_none()

        if not challenge or challenge.challenge_receiver_id != user_id:
            await self.connection.close_session()
            return False

        challenge.accepted_receiver = True
        await self.connection.session.commit()
        await self.connection.close_session()
        self.logger.info(f"Challenge {challenge_id} accepted by user {user_id}")
        return True
    
        
    @custom_db_crud_handler
    async def read_by_email(self, model: any, email: str):
        """
        Retrieves a record from the database by email asynchronously.

        Args:
            model (any): The model to query.
            email (str): The email address to search for.

        Returns:
            Union[bool, any]: The matched object if found, or False if not found or error occurs.
        """
        stmt = select(model).where(model.email == email)
        result = await self.connection.session.execute(stmt)
        user = result.scalar_one_or_none()

        await self.connection.close_session()

        if user:
            self.logger.info(f"User with email '{email}' found: {user.to_dict()}")
        else:
            self.logger.info(f"No user found with email: {email}")

        return user
    
    @custom_db_crud_handler
    async def get_last_n_conversation(self, user_id: int, n: int = 5):
        async with self.connection.session() as session:
            result = await session.execute(
                select(QuestionAnswer)
                .where(QuestionAnswer.user_id == user_id)
                .order_by(desc(QuestionAnswer.created_at))
                .limit(n)
            )
            return result.scalars().all()


    @custom_db_crud_handler
    async def read_challenges(self, filters: dict = None) -> Union[list, bool]:
        """
        Retrieves challenges from the database with optional filtering.

        Args:
            filters (dict, optional): Filter conditions as a dictionary. Defaults to None.

        Returns:
            Union[list, bool]: List of Challenges objects or False if error.
        """
        stmt = select(Challenges)

        if filters:
            for key, value in filters.items():
                stmt = stmt.where(getattr(Challenges, key) == value)

        result = await self.connection.session.execute(stmt)
        challenges = result.scalars().all()

        await self.connection.close_session()

        self.logger.info(f"Challenges read with filters: {filters}. Found: {len(challenges)} records.")
        return challenges
    
    @custom_db_crud_handler
    async def read_challenges_for_user(self, user_id: int):
        query = (
            select(Challenges)
            .where(
                or_(
                    Challenges.challenge_sender_id == user_id,
                    Challenges.challenge_receiver_id == user_id
                )
            )
        )
        result = await self.connection.session.execute(query)
        return result.scalars().all()
    
    @custom_db_crud_handler
    async def get_or_create_user_score(self, user_id: int):
        score = await self.connection.session.get(UserScore, user_id)
        if score is None:
            score = UserScore(user_id=user_id, total_score=0)
            self.connection.session.add(score)
            await self.connection.session.commit()
            await self.connection.session.refresh(score)
        return score

    @custom_db_crud_handler
    async def update_user_score(self, user_id: int, points: int):
        async with self.connection.session as session:
            async with session.begin():
                result = await session.execute(select(UserScore).where(UserScore.user_id == user_id))
                user_score = result.scalar_one_or_none()
                
                if user_score is None:
                    # Eğer kullanıcıya ait skor yoksa hata döndür veya yeni skor oluştur
                    raise ValueError(f"No UserScore found for user_id: {user_id}")

                user_score.total_score += points
                await session.commit()
                return user_score.total_score
    
    @custom_db_crud_handler
    async def get_user_score_by_id(self, user_id: int) -> int:
        score = await self.connection.session.get(UserScore, user_id)
        await self.connection.close_session()
        return score.total_score if score else 0
    
    @custom_db_crud_handler
    async def get_top_users_by_score(self, limit: int = 5):
        """
        Retrieves top N users sorted by their total_score in descending order.
        """
        stmt = (
            select(UserScore.user_id, User.username, User.email, UserScore.total_score)
            .join(User, User.id == UserScore.user_id)
            .order_by(UserScore.total_score.desc())
            .limit(limit)
        )

        result = await self.connection.session.execute(stmt)
        rows = result.all()
        await self.connection.close_session()

        top_users = [
            {
                "user_id": row.user_id,
                "username": row.username,
                "email": row.email,
                "score": row.total_score
            }
            for row in rows
        ]

        self.logger.info(f"Top {limit} users retrieved for global ranking.")
        return top_users
    

    @custom_db_crud_handler
    async def get_last_wrong_answers(self, user_id: int, limit: int = 5):
        """
        Retrieves the last `limit` wrong answers for a specific user.

        Args:
            user_id (int): ID of the user.
            limit (int): Number of records to retrieve (default 5).

        Returns:
            List[WrongAnswer]: List of WrongAnswer objects.
        """
        stmt = (
            select(WrongAnswer)
            .where(WrongAnswer.user_id == user_id)
            .order_by(desc(WrongAnswer.created_at))  # veya created_at varsa onunla sırala
            .limit(limit)
        )
        result = await self.connection.session.execute(stmt)
        return result.scalars().all()
    

    @custom_db_crud_handler
    async def get_last_3_conversations_by_user(self, user_id: int) -> str:
        """
        Retrieves the last 3 question-answer pairs for a given user_id and returns
        them as a single concatenated string.

        Args:
            user_id (int): ID of the user.

        Returns:
            str: Combined string of the last 3 "Q: ... A: ..." entries.
        """
        stmt = (
            select(QuestionAnswer)
            .where(QuestionAnswer.user_id == user_id)
            .order_by(desc(QuestionAnswer.created_at))
            .limit(3)
        )

        result = await self.connection.session.execute(stmt)
        qa_list = result.scalars().all()
        await self.connection.close_session()

        combined = "\n\n".join([f"Q: {qa.question}\nA: {qa.answer}" for qa in qa_list])
        self.logger.info(f"Combined last 3 conversations retrieved for user_id {user_id}")
        return combined
    




async def main(crud):
    await crud.initialize()
    user= User(name = "Akif", age = 25)
    print(crud)
    #await crud.create(user)
    x = await crud.read_by_id(User,6)
    print(x)


if __name__ == "__main__":
    from app.logger import Logger
    from app.connection import Connection
    from models.models import User

    logger_dict = {
        "filepath": "./logs/database.log",
        "rotation": "50MB"
    }

    logger = Logger(**logger_dict)
    logger.debug("############ DATABASE CONNECTION CONFIGURATIONS ############")
    logger.debug(logger_dict)

    parameter_dict = {
        "database_type": "postgresql",
        "db_username": "postgres",
        "db_password": "admin",
        "db_host": "localhost",
        "db_port": "5432",
        "db_name": "workplace"
    }
    #connection = Connection()
    crud = CRUDOperations(**parameter_dict,logger = logger)
    asyncio.run(main(crud))


