import time


def custom_db_crud_handler(func):
    start_time = time.time()
    async def inner(self, *args):
        try:
            result = await func(self, *args)
            end_time = time.time()
            self.logger.info(f"{func.__name__} method is done successfully and it took: {end_time-start_time:.4f} seconds")
            return result
        except Exception as e:
            await self.connection.session.rollback()
            self.logger.error(f"Exception : {e}")
            return False
        finally:
            await self.connection.close_session()
    return inner

def custom_db_connection_handler(func):
    start_time = time.time()
    async def inner(self, *args):
        try:
            await func(self, *args)
            end_time = time.time()
            self.logger.info(f"{func.__name__} method is done successfully and it took : {end_time-start_time:.4f} seconds")
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
    return inner

def connection_handler(func):
    async def inner(self, *args):
        exception_type = None
        counter = 2
        while counter <= 8:
            try:
                print("calling connection function")
                result = await func(self, *args)
                self.logger.info(f"Connection has been established.")
                return result
            except Exception as e:
                self.logger.error(f"Database connection failed: {e}")
                exception_type = e
            time.sleep(counter)
            counter *= 2
        raise exception_type
    return inner



if __name__ == "__main__":
    pass
