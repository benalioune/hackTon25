from fastapi import APIRouter, Depends, HTTPException
from classes.schemas_dto import Student, StudentBase
from routers.router_auth import get_current_user
from database.firebase import db
from typing import List

router = APIRouter(prefix='/students', tags=['Étudiants'])

@router.get('/profile', response_model=Student)
async def get_student_profile(current_user: dict = Depends(get_current_user)):
    """Récupère le profil de l'étudiant connecté"""
    if current_user.get('user_type') != 'student':
        raise HTTPException(status_code=403, detail="Réservé aux étudiants")
    
    try:
        student_data = db.child("students").child(current_user['uid']).get().val()
        if not student_data:
            raise HTTPException(status_code=404, detail="Profil étudiant non trouvé")
        return Student(**student_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch('/profile')
async def update_student_profile(
    profile_data: StudentBase,
    current_user: dict = Depends(get_current_user)
):
    """Met à jour le profil de l'étudiant"""
    if current_user.get('user_type') != 'student':
        raise HTTPException(status_code=403, detail="Réservé aux étudiants")
    
    try:
        db.child("students").child(current_user['uid']).update(profile_data.dict())
        return {"message": "Profil mis à jour avec succès"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/notifications')
async def get_student_notifications(current_user: dict = Depends(get_current_user)):
    """Récupère les notifications de l'étudiant connecté"""
    if current_user.get('user_type') != 'student':
        raise HTTPException(status_code=403, detail="Réservé aux étudiants")
    try:
        all_notifications = db.child("notifications").get().val() or {}
        my_notifications = [notif for notif in all_notifications.values() if notif.get('student_id') == current_user['uid']]
        # Trier par date de création (plus récent en premier)
        my_notifications.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return my_notifications
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
