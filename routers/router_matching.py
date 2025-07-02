from fastapi import APIRouter, Depends, HTTPException
from classes.schemas_dto import Opportunity, OpportunityBase, Application
from routers.router_auth import get_current_user
from database.firebase import db
from typing import List
from datetime import datetime
import uuid

router = APIRouter(prefix='/matching', tags=['Mise en Relation'])

@router.post('/opportunities', response_model=Opportunity, status_code=201)
async def create_opportunity(
    opportunity_data: OpportunityBase,
    current_user: dict = Depends(get_current_user)
):
    """Entreprise crée une opportunité"""
    if current_user.get('user_type') != 'company':
        raise HTTPException(status_code=403, detail="Réservé aux entreprises")
    
    try:
        opportunity_id = str(uuid.uuid4())
        opportunity = Opportunity(
            id=opportunity_id,
            created_at=datetime.now(),
            **opportunity_data.dict()
        )
        
        # Convertir datetime en string pour Firebase
        opportunity_dict = opportunity.dict()
        opportunity_dict['created_at'] = opportunity_dict['created_at'].isoformat()
        
        db.child("opportunities").child(opportunity_id).set(opportunity_dict)
        
        # Notifier les étudiants correspondants
        await notify_matching_students(opportunity)
        
        return opportunity
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/recommendations')
async def get_student_recommendations(current_user: dict = Depends(get_current_user)):
    """Étudiant récupère les opportunités recommandées"""
    if current_user.get('user_type') != 'student':
        raise HTTPException(status_code=403, detail="Réservé aux étudiants")
    
    try:
        student_data = db.child("students").child(current_user['uid']).get().val()
        validated_skills = student_data.get('validated_skills', {})
        
        all_opportunities = db.child("opportunities").get().val() or {}
        recommendations = []
        
        for opp_id, opportunity in all_opportunities.items():
            required_skills = opportunity.get('required_skills', [])
            match_score = calculate_match_score(validated_skills, required_skills)
            
            if match_score > 0.3:  # Seuil de correspondance
                opportunity['match_score'] = match_score
                recommendations.append(opportunity)
        
        # Trier par score de correspondance
        recommendations.sort(key=lambda x: x['match_score'], reverse=True)
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def calculate_match_score(student_skills: dict, required_skills: list) -> float:
    """Calcule le score de correspondance entre compétences étudiant et exigences"""
    if not required_skills:
        return 0.0
    
    matched_skills = 0
    for skill in required_skills:
        if skill in student_skills:
            # Bonus selon le niveau validé
            level_bonus = {
                'débutant': 0.25,
                'intermédiaire': 0.5,
                'avancé': 0.75,
                'expert': 1.0
            }
            matched_skills += level_bonus.get(student_skills[skill], 0)
    
    return matched_skills / len(required_skills)

# Fonction pour notifier les étudiants correspondant à une opportunité
async def notify_matching_students(opportunity):
    try:
        students = db.child("students").get().val() or {}
        required_skills = opportunity.required_skills if hasattr(opportunity, 'required_skills') else opportunity.get('required_skills', [])
        notified_students = []
        for student_id, student_data in students.items():
            student_skills = student_data.get('validated_skills', {})
            if any(skill in student_skills for skill in required_skills):
                notification_id = str(uuid.uuid4())
                notification_data = {
                    "id": notification_id,
                    "student_id": student_id,
                    "type": "opportunity_match",
                    "opportunity_id": opportunity.id,
                    "message": f"Nouvelle opportunité correspondant à vos compétences : {opportunity.title}",
                    "created_at": datetime.now().isoformat(),
                    "read": False
                }
                db.child("notifications").child(notification_id).set(notification_data)
                notified_students.append(student_id)
        return len(notified_students)
    except Exception as e:
        print(f"Erreur lors de la notification des étudiants: {str(e)}")
        return 0
