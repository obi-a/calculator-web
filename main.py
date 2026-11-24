# main.py

from contextlib import asynccontextmanager
from math import isfinite
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.database import get_db
from app.database_init import init_db
from app.models.calculation import Calculation
from app.models.user import User
from app.operations import add, subtract, multiply, divide
from app.operations.factory import get_operation
from app.schemas.base import UserCreate
from app.schemas.calculation import CalculationCreate, CalculationRead
from app.schemas.user import Token, UserLogin, UserRead
import uvicorn
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Calculator API", lifespan=lifespan)

# Setup templates directory
templates = Jinja2Templates(directory="templates")

# Pydantic model for request data
class OperationRequest(BaseModel):
    a: float = Field(..., description="The first number")
    b: float = Field(..., description="The second number")

    @field_validator('a', 'b')
    def validate_numbers(cls, value):
        if not isinstance(value, (int, float)):
            raise ValueError('Both a and b must be numbers.')
        return value

# Pydantic model for successful response
class OperationResponse(BaseModel):
    result: float = Field(..., description="The result of the operation")

# Pydantic model for error response
class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")


def error_responses(*status_codes: int):
    return {code: {"model": ErrorResponse} for code in status_codes}


# Custom Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException on {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
        headers=exc.headers,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Extracting error messages
    error_messages = "; ".join([f"{err['loc'][-1]}: {err['msg']}" for err in exc.errors()])
    logger.error(f"ValidationError on {request.url.path}: {error_messages}")
    return JSONResponse(
        status_code=400,
        content={"error": error_messages},
    )

@app.get("/")
async def read_root(request: Request):
    """
    Serve the index.html template.
    """
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/add", response_model=OperationResponse, responses={400: {"model": ErrorResponse}})
async def add_route(operation: OperationRequest):
    """
    Add two numbers.
    """
    try:
        result = add(operation.a, operation.b)
        return OperationResponse(result=result)
    except Exception as e:
        logger.error(f"Add Operation Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/subtract", response_model=OperationResponse, responses={400: {"model": ErrorResponse}})
async def subtract_route(operation: OperationRequest):
    """
    Subtract two numbers.
    """
    try:
        result = subtract(operation.a, operation.b)
        return OperationResponse(result=result)
    except Exception as e:
        logger.error(f"Subtract Operation Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/multiply", response_model=OperationResponse, responses={400: {"model": ErrorResponse}})
async def multiply_route(operation: OperationRequest):
    """
    Multiply two numbers.
    """
    try:
        result = multiply(operation.a, operation.b)
        return OperationResponse(result=result)
    except Exception as e:
        logger.error(f"Multiply Operation Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/divide", response_model=OperationResponse, responses={400: {"model": ErrorResponse}})
async def divide_route(operation: OperationRequest):
    """
    Divide two numbers.
    """
    try:
        result = divide(operation.a, operation.b)
        return OperationResponse(result=result)
    except ValueError as e:
        logger.error(f"Divide Operation Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Divide Operation Internal Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/users/register", response_model=UserRead, status_code=status.HTTP_201_CREATED,
          responses=error_responses(400), tags=["users"])
def register(user_create: UserCreate, db: Session = Depends(get_db)):
    """Validate and persist a user without exposing their password hash."""
    try:
        user = User.register(db, user_create.model_dump())
        db.commit()
        db.refresh(user)
        return user
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        if getattr(exc.orig, "pgcode", None) == "23505":
            raise HTTPException(status_code=400, detail="Username or email already exists") from exc
        raise
    except SQLAlchemyError:
        db.rollback()
        raise


@app.post("/users/login", response_model=Token, responses=error_responses(400, 401), tags=["users"])
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    """Verify a username or email and password, returning a bearer JWT."""
    try:
        auth_result = User.authenticate(db, user_login.username, user_login.password)
    except SQLAlchemyError:
        db.rollback()
        raise
    if auth_result is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_result


def validate_calculation(data: CalculationCreate, current_user: UserRead):
    """Keep ownership fixed and reject results that cannot be returned as JSON."""
    if data.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="user_id must match the authenticated user")
    if not isfinite(get_operation(data.type)(data.a, data.b)):
        raise HTTPException(status_code=400, detail="Calculation result must be finite")


def get_owned_calculation(db: Session, calculation_id: UUID, user_id: UUID) -> Calculation:
    calculation = db.query(Calculation).filter(
        Calculation.id == calculation_id,
        Calculation.user_id == user_id,
    ).first()
    if calculation is None:
        raise HTTPException(status_code=404, detail="Calculation not found")
    return calculation


@app.post("/calculations", response_model=CalculationRead, status_code=status.HTTP_201_CREATED,
          responses=error_responses(400, 401, 403), tags=["calculations"])
def create_calculation(
    data: CalculationCreate,
    current_user: UserRead = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    validate_calculation(data, current_user)
    calculation = Calculation(a=data.a, b=data.b, type=data.type.value, user_id=current_user.id)
    try:
        db.add(calculation)
        db.commit()
        db.refresh(calculation)
        return calculation
    except SQLAlchemyError:
        db.rollback()
        raise


@app.get("/calculations", response_model=list[CalculationRead],
         responses=error_responses(400, 401), tags=["calculations"])
def list_calculations(
    current_user: UserRead = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return db.query(Calculation).filter(Calculation.user_id == current_user.id).all()


@app.get("/calculations/{id}", response_model=CalculationRead,
         responses=error_responses(400, 401, 404), tags=["calculations"])
def read_calculation(
    id: UUID,
    current_user: UserRead = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return get_owned_calculation(db, id, current_user.id)


@app.put("/calculations/{id}", response_model=CalculationRead,
         responses=error_responses(400, 401, 403, 404), tags=["calculations"])
def update_calculation(
    id: UUID,
    data: CalculationCreate,
    current_user: UserRead = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    calculation = get_owned_calculation(db, id, current_user.id)
    validate_calculation(data, current_user)
    try:
        calculation.a = data.a
        calculation.b = data.b
        calculation.type = data.type.value
        db.commit()
        db.refresh(calculation)
        return calculation
    except SQLAlchemyError:
        db.rollback()
        raise


@app.delete("/calculations/{id}", status_code=status.HTTP_204_NO_CONTENT,
            responses=error_responses(400, 401, 404), tags=["calculations"])
def delete_calculation(
    id: UUID,
    current_user: UserRead = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    calculation = get_owned_calculation(db, id, current_user.id)
    try:
        db.delete(calculation)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)


default_openapi = app.openapi


def custom_openapi():
    """Describe validation errors using the same contract as the exception handler."""
    schema = default_openapi()
    for path in schema["paths"].values():
        for operation in path.values():
            responses = operation.get("responses", {})
            validation_content = responses.get("422", {}).get("content", {})
            validation_error = validation_content.get("application/json", {}).get("schema", {})
            if validation_error.get("$ref") == "#/components/schemas/HTTPValidationError":
                del responses["422"]
                responses.setdefault("400", {
                    "description": "Invalid request data",
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}},
                })
    return schema


app.openapi = custom_openapi


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
