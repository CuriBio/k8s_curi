from pydantic import BaseModel
from pydantic import constr, validator

class LoginError(Exception):
    pass

class RegistrationError(Exception):
    pass

