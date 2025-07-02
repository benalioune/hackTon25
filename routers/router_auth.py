from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from firebase_admin import auth
from database.firebase import db, authUser
from classes.schemas_dto import User, StudentCreate, Professional, ProfessionalCreate, CompanyCreate
from datetime import datetime

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='auth/login')

# APIRouter instance
router = APIRouter(prefix='/auth', tags=['Auth'])

# Utilitaire: Vérifie le token et retourne l'utilisateur
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        decoded_token = auth.verify_id_token(token)
        user_data = db.child("users").child(decoded_token['uid']).get().val()
        if not user_data:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        return {**decoded_token, **user_data, 'token': token}
    except Exception:
        raise HTTPException(status_code=401, detail="Token invalide")

# Endpoint générique d'inscription
@router.post('/signup', status_code=201)
async def signup(user_data: User):
    email = user_data.email
    password = user_data.password
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
    try:
        user = auth.create_user(email=email, password=password)
        user_data_dict = {
            "email": email,
            "uid": user.uid,
            "created_at": str(user.user_metadata.creation_timestamp)
        }
        db.child("users").child(user.uid).set(user_data_dict)
        return JSONResponse(content={
            "message": f"User account created successfully for user {user.uid}",
            "user_id": user.uid
        })
    except auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail=f"Account already exists for email {email}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while creating the account: {str(e)}")

# Endpoint d'inscription étudiant
@router.post('/signup/student', status_code=201)
async def signup_student(student_data: StudentCreate):
    try:
        user = auth.create_user(
            email=student_data.email,
            password=student_data.password
        )
        student_dict = student_data.dict()
        student_dict['id'] = user.uid
        student_dict['user_type'] = 'student'
        student_dict['created_at'] = datetime.now().isoformat()
        del student_dict['password']  # Ne pas stocker le mot de passe
        db.child("students").child(user.uid).set(student_dict)
        db.child("users").child(user.uid).set({
            "email": student_data.email,
            "user_type": "student",
            "profile_complete": False
        })
        return {"message": "Compte étudiant créé avec succès", "user_id": user.uid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint d'inscription professionnel
@router.post('/signup/professional', status_code=201)
async def signup_professional(professional_data: ProfessionalCreate):
    try:
        user = auth.create_user(
            email=professional_data.email,
            password=professional_data.password
        )
        professional_dict = professional_data.dict()
        professional_dict['id'] = user.uid
        professional_dict['user_type'] = 'professional'
        professional_dict['created_at'] = datetime.now().isoformat()
        del professional_dict['password']  # Ne pas stocker le mot de passe
        db.child("professionals").child(user.uid).set(professional_dict)
        db.child("users").child(user.uid).set({
            "email": professional_data.email,
            "user_type": "professional",
            "verified": False
        })
        return {"message": "Compte professionnel créé avec succès", "user_id": user.uid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint d'inscription entreprise
@router.post('/signup/company', status_code=201)
async def signup_company(company_data: CompanyCreate):
    try:
        user = auth.create_user(
            email=company_data.email,
            password=company_data.password
        )
        company_dict = company_data.dict()
        company_dict['id'] = user.uid
        company_dict['user_type'] = 'company'
        company_dict['created_at'] = datetime.now().isoformat()
        del company_dict['password']  # Ne pas stocker le mot de passe
        db.child("companies").child(user.uid).set(company_dict)
        db.child("users").child(user.uid).set({
            "email": company_data.email,
            "user_type": "company",
            "verified": False
        })
        return {"message": "Compte entreprise créé avec succès", "user_id": user.uid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint de login (retourne un token Firebase)
@router.post('/login')
async def login(user_credentials: OAuth2PasswordRequestForm = Depends()):
    try:
        user = authUser.sign_in_with_email_and_password(
            email=user_credentials.username,
            password=user_credentials.password
        )
        token = user['idToken']
        return {
            'access_token': token,
            'token_type': 'bearer'
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail='Invalid credentials')

# Endpoint protégé pour tester le token
@router.get('/me')
def secure_endpoint(user_data: dict = Depends(get_current_user)):
    return user_data

@router.get('/my-validations')
async def get_my_validations(current_user: dict = Depends(get_current_user)):
    """Étudiant récupère ses demandes de validation"""
    if current_user.get('user_type') != 'student':
        raise HTTPException(status_code=403, detail="Réservé aux étudiants")
    
    try:
        all_validations = db.child("skill_validations").get().val() or {}
        my_validations = []
        
        for validation_id, validation in all_validations.items():
            if validation.get('student_id') == current_user['uid']:
                validation['id'] = validation_id
                my_validations.append(validation)
        
        # Trier par date de création (plus récent en premier)
        my_validations.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return my_validations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
