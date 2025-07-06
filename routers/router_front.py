from fastapi import APIRouter, Request, Form, status, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import requests

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@router.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    # Appel API backend pour login
    api_url = "http://localhost:8000/auth/login"
    data = {"username": username, "password": password}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(api_url, data=data, headers=headers)
    if resp.status_code != 200:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Identifiants invalides"})
    token = resp.json()["access_token"]
    # Récupérer le rôle de l'utilisateur
    me_url = "http://localhost:8000/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = requests.get(me_url, headers=headers)
    if me_resp.status_code != 200:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Erreur lors de la récupération du profil"})
    user = me_resp.json()
    user_type = user.get("user_type")
    # Redirection selon le rôle
    if user_type == "student":
        response = RedirectResponse(url="/student/home", status_code=status.HTTP_302_FOUND)
    elif user_type == "company":
        response = RedirectResponse(url="/company/home", status_code=status.HTTP_302_FOUND)
    elif user_type == "professional":
        response = RedirectResponse(url="/professional/home", status_code=status.HTTP_302_FOUND)
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Type d'utilisateur inconnu"})
    # Stocker le token dans un cookie (optionnel)
    response.set_cookie(key="access_token", value=token, httponly=True, path="/", samesite="lax")
    return response

@router.get("/student/home", response_class=HTMLResponse)
def student_home(request: Request, access_token: str = Cookie(None)):
    notifications_count = 0
    pending_validations_count = 0
    recent_opportunities = []
    try:
        if access_token:
            headers = {"Authorization": f"Bearer {access_token}"}
            # Récupérer notifications
            notif_resp = requests.get("http://localhost:8000/students/notifications", headers=headers)
            if notif_resp.status_code == 200:
                notifications = notif_resp.json()
                notifications_count = len(notifications)
            # Récupérer validations
            validations_resp = requests.get("http://localhost:8000/skills/my-validations", headers=headers)
            if validations_resp.status_code == 200:
                validations = validations_resp.json()
                pending_validations_count = len([v for v in validations if v.get('status', '').lower() == 'en_attente'])
            # Récupérer les offres récentes des entreprises
            opportunities_resp = requests.get("http://localhost:8000/opportunities/recent", headers=headers)
            if opportunities_resp.status_code == 200:
                recent_opportunities = opportunities_resp.json()
    except Exception:
        pass
    return templates.TemplateResponse("student_home.html", {
        "request": request,
        "notifications_count": notifications_count,
        "pending_validations_count": pending_validations_count,
        "recent_opportunities": recent_opportunities
    })

@router.get("/company/home", response_class=HTMLResponse)
def company_home(request: Request, access_token: str = Cookie(None)):
    notifications_count = 0
    applications_count = 0
    company_opportunities = []
    try:
        if access_token:
            headers = {"Authorization": f"Bearer {access_token}"}
            # Récupérer notifications
            notif_resp = requests.get("http://localhost:8000/companies/notifications", headers=headers)
            if notif_resp.status_code == 200:
                notifications = notif_resp.json()
                notifications_count = len(notifications)
            # Récupérer opportunités de l'entreprise
            opportunities_resp = requests.get("http://localhost:8000/companies/opportunities", headers=headers)
            if opportunities_resp.status_code == 200:
                company_opportunities = opportunities_resp.json()
            # Récupérer candidatures reçues
            applications_resp = requests.get("http://localhost:8000/companies/applications", headers=headers)
            if applications_resp.status_code == 200:
                applications = applications_resp.json()
                applications_count = len(applications)
    except Exception:
        pass
    return templates.TemplateResponse("company_home.html", {
        "request": request,
        "notifications_count": notifications_count,
        "applications_count": applications_count,
        "company_opportunities": company_opportunities
    })

@router.get("/professional/home", response_class=HTMLResponse)
def professional_home(request: Request, access_token: str = Cookie(None)):
    notifications_count = 0
    pending_validation_requests_count = 0
    pending_validation_requests = []
    try:
        if access_token:
            headers = {"Authorization": f"Bearer {access_token}"}
            # Récupérer notifications
            notif_resp = requests.get("http://localhost:8000/professionals/notifications", headers=headers)
            if notif_resp.status_code == 200:
                notifications = notif_resp.json()
                notifications_count = len(notifications)
            # Récupérer demandes de validation en attente
            validation_resp = requests.get("http://localhost:8000/skills/validation-requests/pending", headers=headers)
            if validation_resp.status_code == 200:
                validation_requests = validation_resp.json()
                pending_validation_requests = validation_requests
                pending_validation_requests_count = len(validation_requests)
    except Exception:
        pass
    return templates.TemplateResponse("professional_home.html", {
        "request": request,
        "notifications_count": notifications_count,
        "pending_validation_requests_count": pending_validation_requests_count,
        "pending_validation_requests": pending_validation_requests
    })

@router.get("/signup/student", response_class=HTMLResponse)
def signup_student_form(request: Request):
    return templates.TemplateResponse("signup_student.html", {"request": request, "error": None})

@router.post("/signup/student", response_class=HTMLResponse)
def signup_student_submit(request: Request, email: str = Form(...), password: str = Form(...), first_name: str = Form(...), last_name: str = Form(...), school: str = Form(...), formation: str = Form(...), year_of_study: int = Form(...)):
    api_url = "http://localhost:8000/auth/signup/student"
    data = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "school": school,
        "formation": formation,
        "year_of_study": year_of_study,
        "password": password
    }
    resp = requests.post(api_url, json=data)
    if resp.status_code not in (200, 201):
        return templates.TemplateResponse("signup_student.html", {"request": request, "error": resp.json().get("detail", "Erreur lors de l'inscription")})
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

@router.get("/signup/company", response_class=HTMLResponse)
def signup_company_form(request: Request):
    return templates.TemplateResponse("signup_company.html", {"request": request, "error": None})

@router.post("/signup/company", response_class=HTMLResponse)
def signup_company_submit(request: Request, email: str = Form(...), password: str = Form(...), name: str = Form(...), sector: str = Form(...), size: str = Form(...), description: str = Form(...), website: str = Form(None), address: str = Form(None), city: str = Form(...), country: str = Form(...), logo_url: str = Form(None), contact_person: str = Form(...), contact_position: str = Form(...)):
    api_url = "http://localhost:8000/auth/signup/company"
    data = {
        "name": name,
        "sector": sector,
        "size": size,
        "description": description,
        "website": website,
        "address": address,
        "city": city,
        "country": country,
        "logo_url": logo_url,
        "email": email,
        "password": password,
        "contact_person": contact_person,
        "contact_position": contact_position
    }
    resp = requests.post(api_url, json=data)
    if resp.status_code not in (200, 201):
        return templates.TemplateResponse("signup_company.html", {"request": request, "error": resp.json().get("detail", "Erreur lors de l'inscription")})
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

@router.get("/signup/professional", response_class=HTMLResponse)
def signup_professional_form(request: Request):
    return templates.TemplateResponse("signup_professional.html", {"request": request, "error": None})

@router.post("/signup/professional", response_class=HTMLResponse)
def signup_professional_submit(request: Request, email: str = Form(...), password: str = Form(...), first_name: str = Form(...), last_name: str = Form(...), company: str = Form(...), position: str = Form(...), expertise_domains: str = Form(...), years_experience: int = Form(...), phone: str = Form(None), linkedin_url: str = Form(None), bio: str = Form(None)):
    api_url = "http://localhost:8000/auth/signup/professional"
    data = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "company": company,
        "position": position,
        "expertise_domains": [d.strip() for d in (expertise_domains or "").split(",") if d.strip()],
        "years_experience": years_experience,
        "phone": phone,
        "linkedin_url": linkedin_url,
        "bio": bio,
        "password": password
    }
    resp = requests.post(api_url, json=data)
    if resp.status_code not in (200, 201):
        return templates.TemplateResponse("signup_professional.html", {"request": request, "error": resp.json().get("detail", "Erreur lors de l'inscription")})
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response

@router.get('/student/profile', response_class=HTMLResponse)
def student_profile(request: Request, access_token: str = Cookie(None)):
    user_data = None
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get("http://localhost:8000/students/profile", headers=headers)
        if resp.status_code == 200:
            user_data = resp.json()
    return templates.TemplateResponse("student_profile.html", {"request": request, "user": user_data})

@router.get('/student/validations', response_class=HTMLResponse)
def student_validations(request: Request, access_token: str = Cookie(None)):
    validations = []
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get("http://localhost:8000/skills/my-validations", headers=headers)
        if resp.status_code == 200:
            validations = resp.json()
    return templates.TemplateResponse("student_validations.html", {"request": request, "validations": validations})

@router.get('/student/notifications', response_class=HTMLResponse)
def student_notifications(request: Request, access_token: str = Cookie(None)):
    notifications = []
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get("http://localhost:8000/students/notifications", headers=headers)
        if resp.status_code == 200:
            notifications = resp.json()
    return templates.TemplateResponse("student_notifications.html", {"request": request, "notifications": notifications})

@router.get('/student/validation-request', response_class=HTMLResponse)
def student_validation_request_form(request: Request):
    return templates.TemplateResponse("student_validation_request.html", {"request": request, "error": None})

@router.post('/student/validation-request', response_class=HTMLResponse)
def student_validation_request_submit(request: Request, skill_name: str = Form(...), level_claimed: str = Form(...), evidence_description: str = Form(...), portfolio_links: str = Form(None), project_description: str = Form(None), access_token: str = Cookie(None)):
    error = None
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
        data = {
            "skill_name": skill_name,
            "level_claimed": level_claimed,
            "evidence_description": evidence_description,
            "portfolio_links": [l.strip() for l in (portfolio_links or '').split(',') if l.strip()],
            "project_description": project_description
        }
        resp = requests.post("http://localhost:8000/skills/validation-request", json=data, headers=headers)
        if resp.status_code not in (200, 201):
            error = resp.json().get("detail", "Erreur lors de la demande de validation")
        else:
            return RedirectResponse(url="/student/validations", status_code=status.HTTP_302_FOUND)
    else:
        error = "Non authentifié"
    return templates.TemplateResponse("student_validation_request.html", {"request": request, "error": error})

@router.get('/student/recommendations', response_class=HTMLResponse)
def student_recommendations(request: Request, access_token: str = Cookie(None)):
    recommendations = []
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get("http://localhost:8000/matching/recommendations", headers=headers)
        if resp.status_code == 200:
            recommendations = resp.json()
    return templates.TemplateResponse("student_recommendations.html", {"request": request, "recommendations": recommendations})

@router.get('/student/opportunity/{opportunity_id}', response_class=HTMLResponse)
def student_opportunity_detail(request: Request, opportunity_id: str, access_token: str = Cookie(None)):
    opportunity = None
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get(f"http://localhost:8000/opportunities/{opportunity_id}", headers=headers)
        if resp.status_code == 200:
            opportunity = resp.json()
    return templates.TemplateResponse("student_opportunity_detail.html", {"request": request, "opportunity": opportunity})

# Routes pour les professionnels
@router.get('/professional/profile', response_class=HTMLResponse)
def professional_profile(request: Request, access_token: str = Cookie(None)):
    user_data = None
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get("http://localhost:8000/professionals/profile", headers=headers)
        if resp.status_code == 200:
            user_data = resp.json()
    return templates.TemplateResponse("professional_profile.html", {"request": request, "user": user_data})

@router.get('/professional/validation-requests', response_class=HTMLResponse)
def professional_validation_requests(request: Request, access_token: str = Cookie(None)):
    validation_requests = []
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get("http://localhost:8000/skills/validation-requests/pending", headers=headers)
        if resp.status_code == 200:
            validation_requests = resp.json()
    return templates.TemplateResponse("professional_validation_requests.html", {"request": request, "validation_requests": validation_requests})

@router.get('/professional/validation-request/{request_id}', response_class=HTMLResponse)
def professional_validation_request_detail(request: Request, request_id: str, access_token: str = Cookie(None)):
    validation_request = None
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get(f"http://localhost:8000/skills/validation-requests/{request_id}", headers=headers)
        if resp.status_code == 200:
            validation_request = resp.json()
    return templates.TemplateResponse("professional_validation_request_detail.html", {"request": request, "validation_request": validation_request})

# Routes pour les entreprises
@router.get('/company/profile', response_class=HTMLResponse)
def company_profile(request: Request, access_token: str = Cookie(None)):
    user_data = None
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get("http://localhost:8000/companies/profile", headers=headers)
        if resp.status_code == 200:
            user_data = resp.json()
    return templates.TemplateResponse("company_profile.html", {"request": request, "user": user_data})

@router.get('/company/opportunities', response_class=HTMLResponse)
def company_opportunities(request: Request, access_token: str = Cookie(None)):
    opportunities = []
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get("http://localhost:8000/companies/opportunities", headers=headers)
        if resp.status_code == 200:
            opportunities = resp.json()
    return templates.TemplateResponse("company_opportunities.html", {"request": request, "opportunities": opportunities})

@router.get('/company/create-opportunity', response_class=HTMLResponse)
def company_create_opportunity_form(request: Request):
    return templates.TemplateResponse("company_create_opportunity.html", {"request": request, "error": None})

@router.get('/company/applications', response_class=HTMLResponse)
def company_applications(request: Request, access_token: str = Cookie(None)):
    applications = []
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get("http://localhost:8000/companies/applications", headers=headers)
        if resp.status_code == 200:
            applications = resp.json()
    return templates.TemplateResponse("company_applications.html", {"request": request, "applications": applications}) 