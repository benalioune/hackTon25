from fastapi import APIRouter, Depends, HTTPException
from classes.schemas_dto import Opportunity
from routers.router_auth import get_current_user
from database.firebase import db
from typing import List
from datetime import datetime, timedelta

router = APIRouter(prefix='/opportunities', tags=['Opportunités'])

@router.get('/recent', response_model=List[dict])
async def get_recent_opportunities(current_user: dict = Depends(get_current_user)):
    """Récupère les opportunités récentes publiées par les entreprises"""
    try:
        # Récupérer toutes les opportunités
        opportunities = db.child("opportunities").get().val() or {}
        
        # Filtrer les opportunités récentes (derniers 30 jours)
        recent_date = datetime.now() - timedelta(days=30)
        recent_opportunities = []
        
        for opp_id, opp_data in opportunities.items():
            # Vérifier si l'opportunité a une date de création
            if 'created_at' in opp_data:
                try:
                    # Convertir la date string en datetime
                    if isinstance(opp_data['created_at'], str):
                        opp_date = datetime.fromisoformat(opp_data['created_at'].replace('Z', '+00:00'))
                    else:
                        opp_date = datetime.fromtimestamp(opp_data['created_at'])
                    
                    if opp_date >= recent_date:
                        # Récupérer les informations de l'entreprise
                        company_id = opp_data.get('company_id')
                        company_name = "Entreprise inconnue"
                        if company_id:
                            company_data = db.child("companies").child(company_id).get().val()
                            if company_data:
                                company_name = company_data.get('name', 'Entreprise inconnue')
                        
                        # Préparer l'opportunité avec les informations de l'entreprise
                        opportunity_with_company = {
                            'id': opp_id,
                            'company_name': company_name,
                            'title': opp_data.get('title', ''),
                            'type': opp_data.get('type', ''),
                            'required_skills': opp_data.get('required_skills', []),
                            'created_at': opp_data.get('created_at', ''),
                            'description': opp_data.get('description', ''),
                            'location': opp_data.get('location', ''),
                            'duration': opp_data.get('duration', ''),
                            'compensation': opp_data.get('compensation', '')
                        }
                        recent_opportunities.append(opportunity_with_company)
                except Exception as e:
                    # Si erreur de parsing de date, inclure quand même l'opportunité
                    opportunity_with_company = {
                        'id': opp_id,
                        'company_name': company_name,
                        'title': opp_data.get('title', ''),
                        'type': opp_data.get('type', ''),
                        'required_skills': opp_data.get('required_skills', []),
                        'created_at': opp_data.get('created_at', ''),
                        'description': opp_data.get('description', ''),
                        'location': opp_data.get('location', ''),
                        'duration': opp_data.get('duration', ''),
                        'compensation': opp_data.get('compensation', '')
                    }
                    recent_opportunities.append(opportunity_with_company)
        
        # Trier par date de création (plus récent en premier)
        recent_opportunities.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Limiter à 20 opportunités
        return recent_opportunities[:20]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/{opportunity_id}', response_model=dict)
async def get_opportunity_detail(opportunity_id: str, current_user: dict = Depends(get_current_user)):
    """Récupère les détails d'une opportunité spécifique"""
    try:
        opportunity_data = db.child("opportunities").child(opportunity_id).get().val()
        if not opportunity_data:
            raise HTTPException(status_code=404, detail="Opportunité non trouvée")
        
        # Récupérer les informations de l'entreprise
        company_id = opportunity_data.get('company_id')
        company_name = "Entreprise inconnue"
        company_data = {}
        if company_id:
            company_data = db.child("companies").child(company_id).get().val() or {}
            company_name = company_data.get('name', 'Entreprise inconnue')
        
        # Préparer la réponse avec les informations de l'entreprise
        opportunity_detail = {
            'id': opportunity_id,
            'company_name': company_name,
            'company_data': company_data,
            **opportunity_data
        }
        
        return opportunity_detail
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 