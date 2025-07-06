# import du framework
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse

# Import des routers
import routers.router_auth
import routers.router_skills
import routers.router_matching
import routers.router_students
import routers.router_professionals
import routers.router_companies
import routers.router_opportunities
import routers.router_front

# Documentation
from documentation.description import api_description

# Initialisation de l'API
app = FastAPI(
    title="StudyConnect - Plateforme de Validation et Mise en Relation",
    description=api_description,
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ajouter les routers dédiés
app.include_router(routers.router_auth.router)
app.include_router(routers.router_skills.router)
app.include_router(routers.router_matching.router)
app.include_router(routers.router_students.router)
app.include_router(routers.router_professionals.router)
app.include_router(routers.router_companies.router)
app.include_router(routers.router_opportunities.router)
app.include_router(routers.router_front.router)

# Route racine
templates = Jinja2Templates(directory="templates")
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

# Route de santé de l'API
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "StudyConnect API"}
