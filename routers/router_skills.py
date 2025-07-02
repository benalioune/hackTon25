from fastapi import APIRouter, Depends, HTTPException
from classes.schemas_dto import SkillValidationRequest, SkillValidation, ValidationStatus, CompetenceLevel
from routers.router_auth import get_current_user
from database.firebase import db
from datetime import datetime
import uuid
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix='/skills', tags=['Validation des Compétences'])

# Nouveau schéma d'entrée sans student_id
class SkillValidationRequestNoId(BaseModel):
    skill_name: str
    level_claimed: CompetenceLevel
    evidence_description: str
    portfolio_links: Optional[List[str]] = None
    project_description: Optional[str] = None

async def notify_relevant_professionals(skill_name: str):
    """Notifie les professionnels compétents dans le domaine de la compétence"""
    try:
        # Récupérer tous les professionnels
        professionals = db.child("professionals").get().val() or {}
        
        relevant_professionals = []
        for prof_id, prof_data in professionals.items():
            expertise_domains = prof_data.get('expertise_domains', [])
            # Vérifier si la compétence correspond aux domaines d'expertise
            if any(domain.lower() in skill_name.lower() or skill_name.lower() in domain.lower() 
                   for domain in expertise_domains):
                relevant_professionals.append(prof_id)
        
        # Créer des notifications pour les professionnels pertinents
        for prof_id in relevant_professionals:
            notification_id = str(uuid.uuid4())
            notification_data = {
                "id": notification_id,
                "professional_id": prof_id,
                "type": "skill_validation_request",
                "skill_name": skill_name,
                "message": f"Nouvelle demande de validation pour la compétence : {skill_name}",
                "created_at": datetime.now().isoformat(),
                "read": False
            }
            db.child("notifications").child(notification_id).set(notification_data)
            
        return len(relevant_professionals)
    except Exception as e:
        print(f"Erreur lors de la notification des professionnels: {str(e)}")
        return 0

@router.post('/validation-request', response_model=SkillValidation, status_code=201)
async def request_skill_validation(
    request_data: SkillValidationRequestNoId,
    current_user: dict = Depends(get_current_user)
):
    """Étudiant demande la validation d'une compétence (student_id injecté automatiquement)"""
    if current_user.get('user_type') != 'student':
        raise HTTPException(status_code=403, detail="Réservé aux étudiants")
    
    try:
        validation_id = str(uuid.uuid4())
        validation = SkillValidation(
            id=validation_id,
            created_at=datetime.now(),
            student_id=current_user['uid'],
            **request_data.dict()
        )
        
        # Convertir datetime en string pour Firebase
        validation_dict = validation.dict()
        validation_dict['created_at'] = validation_dict['created_at'].isoformat()
        
        db.child("skill_validations").child(validation_id).set(validation_dict)
        
        # Notifier les professionnels compétents
        notified_count = await notify_relevant_professionals(request_data.skill_name)
        
        return validation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/pending-validations')
async def get_pending_validations(current_user: dict = Depends(get_current_user)):
    """Professionnel récupère les validations en attente dans son domaine"""
    if current_user.get('user_type') != 'professional':
        raise HTTPException(status_code=403, detail="Réservé aux professionnels")
    
    try:
        professional_data = db.child("professionals").child(current_user['uid']).get().val()
        if not professional_data:
            raise HTTPException(status_code=404, detail="Profil professionnel non trouvé")
            
        expertise_domains = professional_data.get('expertise_domains', [])
        
        all_validations = db.child("skill_validations").get().val() or {}
        pending_validations = []
        
        for validation_id, validation in all_validations.items():
            if (validation.get('status') == ValidationStatus.EN_ATTENTE and 
                any(domain.lower() in validation.get('skill_name', '').lower() or 
                    validation.get('skill_name', '').lower() in domain.lower() 
                    for domain in expertise_domains)):
                validation['id'] = validation_id
                pending_validations.append(validation)
        
        return pending_validations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch('/validate/{validation_id}')
async def validate_skill(
    validation_id: str,
    validated_level: CompetenceLevel,
    feedback: str,
    current_user: dict = Depends(get_current_user)
):
    """Professionnel valide une compétence"""
    if current_user.get('user_type') != 'professional':
        raise HTTPException(status_code=403, detail="Réservé aux professionnels")
    
    try:
        # Vérifier que la validation existe
        validation = db.child("skill_validations").child(validation_id).get().val()
        if not validation:
            raise HTTPException(status_code=404, detail="Demande de validation non trouvée")
        
        # Mettre à jour la validation
        update_data = {
            'status': ValidationStatus.VALIDEE,
            'professional_id': current_user['uid'],
            'validated_level': validated_level,
            'professional_feedback': feedback,
            'validation_date': datetime.now().isoformat()
        }
        
        db.child("skill_validations").child(validation_id).update(update_data)
        
        # Mettre à jour le profil étudiant
        student_id = validation['student_id']
        skill_name = validation['skill_name']
        
        db.child("students").child(student_id).child("validated_skills").child(skill_name).set(validated_level)
        
        # Mettre à jour les statistiques du professionnel
        current_count = db.child("professionals").child(current_user['uid']).child("validation_count").get().val() or 0
        db.child("professionals").child(current_user['uid']).update({"validation_count": current_count + 1})
        
        return {"message": "Compétence validée avec succès"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

@router.delete('/validation-request/{validation_id}')
async def cancel_validation_request(
    validation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Étudiant annule sa demande de validation (si en attente)"""
    if current_user.get('user_type') != 'student':
        raise HTTPException(status_code=403, detail="Réservé aux étudiants")
    
    try:
        validation = db.child("skill_validations").child(validation_id).get().val()
        if not validation:
            raise HTTPException(status_code=404, detail="Demande de validation non trouvée")
        
        if validation.get('student_id') != current_user['uid']:
            raise HTTPException(status_code=403, detail="Non autorisé à supprimer cette demande")
        
        if validation.get('status') != ValidationStatus.EN_ATTENTE:
            raise HTTPException(status_code=400, detail="Impossible d'annuler une demande déjà traitée")
        
        db.child("skill_validations").child(validation_id).remove()
        return {"message": "Demande de validation annulée avec succès"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
