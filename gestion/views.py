from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count, Q
from datetime import datetime, date, timedelta
import pandas as pd
from io import BytesIO
import os
import json
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from .models import Societe, Agent, Affectation, HeureTransport, Chauffeur, Course
from .forms import UploadFileForm, AgentForm, AffectationMultipleForm, FiltreForm, ChauffeurForm, AgentModificationForm, ImportAgentForm, SocieteForm, SocieteModificationForm
from .utils import GestionnaireTransport
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from .models import Agent
from django.utils import timezone
import random
from django.contrib.auth.decorators import user_passes_test
def is_admin(user):
    return user.is_authenticated and user.is_staff
@login_required
@csrf_exempt
def corriger_coordonnees_agent(request):
    print("🔍 API appelée avec méthode:", request.method)
    
    if request.method == 'POST':
        try:
            # Vérifier si les données sont en JSON
            if request.content_type == 'application/json':
                print("📊 Données reçues en JSON")
                data = json.loads(request.body.decode('utf-8'))
            else:
                # Sinon, utiliser request.POST pour les données form-data
                print("📊 Données reçues en form-data")
                data = {
                    'agent_id': request.POST.get('agent_id'),
                    'latitude': request.POST.get('latitude'),
                    'longitude': request.POST.get('longitude'),
                    'adresse': request.POST.get('adresse')  # <-- AJOUTEZ CETTE LIGNE !
                }
            
            print("📊 Données parsées:", data)
            
            # Extraction des données
            agent_id = data.get('agent_id')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            adresse = data.get('adresse')  # <-- AJOUTEZ CETTE LIGNE !
            
            # Convertir l'agent_id en entier si c'est une chaîne
            if isinstance(agent_id, str):
                try:
                    agent_id = int(agent_id)
                except ValueError:
                    print(f"❌ Impossible de convertir agent_id: {agent_id}")
                    return JsonResponse({
                        'success': False,
                        'error': 'agent_id doit être un nombre'
                    })
            
            print(f"🔍 Paramètres extraits: agent_id={agent_id}, lat={latitude}, lon={longitude}, adresse={adresse}")
            
            # VALIDATION CORRIGÉE : INCLURE ADRESSE !
            if agent_id is None or latitude is None or longitude is None or adresse is None:
                print(f"❌ Données manquantes! agent_id={agent_id}, latitude={latitude}, longitude={longitude}, adresse={adresse}")
                return JsonResponse({
                    'success': False,
                    'error': 'Données manquantes: agent_id, latitude, longitude ET adresse sont requis'
                })
            
            # Validation supplémentaire : adresse non vide
            if not adresse.strip():
                print(f"❌ Adresse vide!")
                return JsonResponse({
                    'success': False,
                    'error': 'Adresse ne peut pas être vide'
                })
            
            try:
                # Convertir les coordonnées en float
                latitude_float = float(latitude)
                longitude_float = float(longitude)
                
                # Validation des valeurs
                if not (-90 <= latitude_float <= 90):
                    return JsonResponse({
                        'success': False,
                        'error': f'Latitude invalide: {latitude_float} (doit être entre -90 et 90)'
                    })
                
                if not (-180 <= longitude_float <= 180):
                    return JsonResponse({
                        'success': False,
                        'error': f'Longitude invalide: {longitude_float} (doit être entre -180 et 180)'
                    })
                
                print(f"✅ Coordonnées validées: {latitude_float}, {longitude_float}")
                
            except ValueError as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Coordonnées invalides: {str(e)}'
                })
            
            # Récupérer l'agent
            try:
                agent = Agent.objects.get(id=agent_id)
            except Agent.DoesNotExist:
                print(f"❌ Agent avec ID {agent_id} non trouvé")
                return JsonResponse({
                    'success': False,
                    'error': f'Agent avec ID {agent_id} non trouvé'
                })
            
            print(f"✅ Agent trouvé: {agent.nom}")
            print(f"   Ancienne adresse dans DB: '{agent.adresse}'")
            print(f"   Nouvelle adresse reçue: '{adresse}'")
            
            # Sauvegarder l'ancienne position pour logging
            old_latitude = agent.latitude
            old_longitude = agent.longitude
            old_adresse = agent.adresse
            
            # METTRE À JOUR LES COORDONNÉES ET L'ADRESSE - VERSION FORCÉE
            agent.latitude = latitude_float
            agent.longitude = longitude_float
            
            # METTRE À JOUR L'ADRESSE DE FAÇON FORCÉE
            agent.adresse = adresse.strip()
            print(f"✅ Adresse définie sur agent: '{agent.adresse}'")
            
            agent.corrige_manuellement = True
            agent.date_correction_coords = timezone.now()
            
            # Ajouter des notes sur la correction
            notes = []
            if old_latitude and old_longitude:
                notes.append(f"Correction manuelle: {old_latitude:.6f},{old_longitude:.6f} → {latitude_float:.6f},{longitude_float:.6f}")
            else:
                notes.append(f"Première correction: {latitude_float:.6f},{longitude_float:.6f}")
            
            if old_adresse and old_adresse.strip() != adresse.strip():
                notes.append(f"Adresse: {old_adresse[:50]}... → {adresse[:50]}...")
            
            agent.notes_correction = "; ".join(notes)
            
            # SAUVEGARDER AVEC FORCE
            agent.save()
            print(f"✅ Agent sauvegardé avec succès!")
            
            # RAFRAÎCHIR DEPUIS LA BASE POUR VÉRIFIER
            agent.refresh_from_db()
            print(f"✅ Vérification après save - adresse actuelle: '{agent.adresse}'")
            
            return JsonResponse({
                'success': True,
                'message': f'Coordonnées et adresse de {agent.nom} mises à jour',
                'agent': {
                    'id': agent.id,
                    'nom': agent.nom,
                    'latitude': agent.latitude,
                    'longitude': agent.longitude,
                    'adresse': agent.adresse,  # <-- RETOURNEZ LA NOUVELLE ADRESSE
                    'corrige_manuellement': agent.corrige_manuellement,
                    'date_correction': agent.date_correction_coords.strftime("%d/%m/%Y %H:%M") if agent.date_correction_coords else None
                }
            })
            
        except json.JSONDecodeError as e:
            print(f"❌ Erreur de décodage JSON: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Format JSON invalide: {str(e)}'
            })
        except Exception as e:
            print(f"❌ Erreur inattendue: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'error': f'Erreur inattendue: {str(e)}'
            })
    
    print(f"❌ Méthode {request.method} non autorisée")
    return JsonResponse({
        'success': False, 
        'error': 'Méthode non autorisée. Utilisez POST'
    })
@login_required
def index(request):
    "Page d'accueil avec vue d'ensemble"
    
    # Statistiques de base pour l'accueil
    total_agents = Agent.objects.count()
    total_affectations = Affectation.objects.count()
    total_courses = Course.objects.count()
    total_chauffeurs = Chauffeur.objects.filter(actif=True).count()
    total_societes = Societe.objects.count()
    
    # Agents incomplets
    agents_incomplets = Agent.objects.filter(
        Q(adresse__in=['Adresse à compléter', 'Adresse non renseignee', '']) |
        Q(telephone__in=['00000000', 'Telephone non renseigne', '']) |
        (Q(societe__isnull=True) & (Q(societe_texte__in=['', 'Société à compléter', 'Societe non renseignee']) | Q(societe_texte__isnull=True)))
    ).count()
    
    # Calcul des revenus
    total_a_payer = Course.objects.aggregate(
        total=Sum('prix_total')
    )['total'] or 0
    
    # Dernières courses (3 derniers jours)
    trois_jours = datetime.now() - timedelta(days=3)
    courses_recentes = Course.objects.filter(
        date_reelle__gte=trois_jours
    ).order_by('-date_reelle')[:5]
    
    context = {
        'total_agents': total_agents,
        'total_affectations': total_affectations,
        'total_courses': total_courses,
        'total_chauffeurs': total_chauffeurs,
        'total_societes': total_societes,
        'total_a_payer': total_a_payer,
        'agents_incomplets': agents_incomplets,
        'courses_recentes': courses_recentes,
    }
    
    return render(request, 'gestion/index.html', context)

@login_required
def tableau_de_bord(request):
    "Tableau de bord avec statistiques et graphiques"
    
    # Récupérer les paramètres de filtrage
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    
    # Calculer les dates par défaut (début et fin du mois courant)
    aujourd_hui = date.today()
    premier_du_mois = date(aujourd_hui.year, aujourd_hui.month, 1)
    
    if aujourd_hui.month == 12:
        dernier_du_mois = date(aujourd_hui.year + 1, 1, 1) - timedelta(days=1)
    else:
        dernier_du_mois = date(aujourd_hui.year, aujourd_hui.month + 1, 1) - timedelta(days=1)
    
    # Si aucune date n'est fournie, utiliser les valeurs par défaut
    if not date_debut or date_debut == 'None':
        date_debut = premier_du_mois.strftime('%Y-%m-%d')
    
    if not date_fin or date_fin == 'None':
        date_fin = dernier_du_mois.strftime('%Y-%m-%d')
    
    # Statistiques de base
    total_agents = Agent.objects.count()
    total_affectations = Affectation.objects.count()
    total_chauffeurs = Chauffeur.objects.filter(actif=True).count()
    total_societes = Societe.objects.count()
    
    # COURSES VALIDÉES (avec filtrage par date)
    courses_query = Course.objects.filter(statut='validee')
    
    # Appliquer les filtres date
    if date_debut and date_debut != 'None':
        try:
            courses_query = courses_query.filter(date_reelle__gte=date_debut)
        except Exception as e:
            print(f"Erreur filtre date début: {e}")
    
    if date_fin and date_fin != 'None':
        try:
            courses_query = courses_query.filter(date_reelle__lte=date_fin)
        except Exception as e:
            print(f"Erreur filtre date fin: {e}")
    
    total_courses_validees = courses_query.count()
    
    # Agents incomplets
    agents_incomplets = Agent.objects.filter(
        Q(adresse__in=['Adresse à compléter', 'Adresse non renseignee', '']) |
        Q(telephone__in=['00000000', 'Telephone non renseigne', '']) |
        (Q(societe__isnull=True) & (Q(societe_texte__in=['', 'Société à compléter', 'Societe non renseignee']) | Q(societe_texte__isnull=True)))
    ).count()
    
    # Calcul des revenus des courses validées
    total_a_payer = courses_query.aggregate(
        total=Sum('prix_total')
    )['total'] or 0
    
    # Statistiques par type de chauffeur (courses validées seulement)
    courses_taxi = courses_query.filter(chauffeur__type_chauffeur='taxi').count()
    courses_prive = courses_query.filter(chauffeur__type_chauffeur='prive').count()
    courses_societe = courses_query.filter(chauffeur__type_chauffeur='societe').count()
    
    # Statistiques par type de transport
    ramassages_count = courses_query.filter(type_transport='ramassage').count()
    departs_count = courses_query.filter(type_transport='depart').count()
    
    # Top 5 sociétés (pour les courses validées)
    top_societes = Societe.objects.annotate(
        count=Count('agent__affectation__course', filter=Q(agent__affectation__course__statut='validee'))
    ).order_by('-count')[:5]
    
    # Dernières courses validées (7 derniers jours)
    sept_jours = datetime.now() - timedelta(days=7)
    courses_recentes = courses_query.filter(
        date_reelle__gte=sept_jours
    ).order_by('-date_reelle')[:10]
    
    # Statistiques hebdomadaires des courses validées
    debut_semaine = aujourd_hui - timedelta(days=aujourd_hui.weekday())
    
    jours_semaine = []
    courses_par_jour = []
    for i in range(7):
        jour = debut_semaine + timedelta(days=i)
        jours_semaine.append(jour.strftime('%a'))
        count = courses_query.filter(date_reelle=jour).count()
        courses_par_jour.append(count)
    
    # Prochaines courses (aujourd'hui) - validées
    courses_aujourdhui = courses_query.filter(date_reelle=aujourd_hui).count()
    
    # Pourcentage d'agents complets
    taux_completude = 0
    if total_agents > 0:
        taux_completude = round(((total_agents - agents_incomplets) / total_agents) * 100, 1)
    
    # Statistiques des 30 derniers jours
    trente_jours = aujourd_hui - timedelta(days=30)
    courses_30jours = courses_query.filter(date_reelle__gte=trente_jours).count()
    revenus_30jours = courses_query.filter(date_reelle__gte=trente_jours).aggregate(
        total=Sum('prix_total')
    )['total'] or 0
    
    context = {
        # Statistiques principales
        'total_agents': total_agents,
        'total_affectations': total_affectations,
        'total_courses': total_courses_validees,
        'total_chauffeurs': total_chauffeurs,
        'total_societes': total_societes,
        'total_a_payer': total_a_payer,
        'agents_incomplets': agents_incomplets,
        'taux_completude': taux_completude,
        
        # Filtres date
        'date_debut': date_debut,
        'date_fin': date_fin,
        
        # Répartitions
        'courses_taxi': courses_taxi,
        'courses_prive': courses_prive,
        'courses_societe': courses_societe,
        'ramassages_count': ramassages_count,
        'departs_count': departs_count,
        
        # Données pour graphiques
        'top_societes': list(top_societes),
        'courses_recentes': courses_recentes,
        'jours_semaine': jours_semaine,
        'courses_par_jour': courses_par_jour,
        'courses_aujourdhui': courses_aujourdhui,
        
        # Statistiques avancées
        'courses_30jours': courses_30jours,
        'revenus_30jours': revenus_30jours,
        
        # Dates
        'aujourd_hui': aujourd_hui,
        'debut_semaine': debut_semaine,
        'premier_du_mois': premier_du_mois,
        'dernier_du_mois': dernier_du_mois,
    }
    
    return render(request, 'gestion/tableau_de_bord.html', context)
@login_required
def upload_files(request):
    gestionnaire = GestionnaireTransport()
    if request.method == 'POST' and 'action' in request.POST:
        if request.POST['action'] == 'clear_file':
            # Supprimer le fichier de la session
            if 'uploaded_file' in request.session:
                file_path = request.session['uploaded_file'].get('path')
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
                
                del request.session['uploaded_file']
                request.session['planning_charge'] = False
                messages.info(request, '🗑️ Fichier supprimé de la session')
            return redirect('upload')
    
    # Récupérer les infos du fichier uploadé depuis la session
    uploaded_file_info = request.session.get('uploaded_file', None)
    planning_charge = request.session.get('planning_charge', False)
    
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            fichier_planning = request.FILES['fichier_planning']
            
            try:
                # Sauvegarder temporairement le fichier
                temp_path = os.path.join(settings.MEDIA_ROOT, 'temp_planning.xlsx')
                with open(temp_path, 'wb+') as destination:
                    for chunk in fichier_planning.chunks():
                        destination.write(chunk)
                
                # Tester la lecture du fichier
                import pandas as pd
                try:
                    # Lire les premières lignes pour vérifier le format
                    df_test = pd.read_excel(temp_path, nrows=3)
                    file_is_valid = True
                    row_count = len(df_test)
                except Exception as e:
                    file_is_valid = False
                    error_message = str(e)
                
                if file_is_valid:
                    if gestionnaire.charger_planning(fichier_planning):
                        # Stocker les infos du fichier dans la session
                        request.session['uploaded_file'] = {
                            'name': fichier_planning.name,
                            'size': fichier_planning.size,
                            'content_type': fichier_planning.content_type,
                            'row_count': row_count,
                            'upload_time': datetime.now().isoformat(),
                            'path': temp_path
                        }
                        request.session['planning_charge'] = True
                        
                        # IMPORTANT: Sauvegarder les dates dans la session
                        if gestionnaire.dates_par_jour:
                            request.session['gestionnaire_dates'] = gestionnaire.dates_par_jour
                            print(f"📅 Dates sauvegardées dans session après upload: {gestionnaire.dates_par_jour}")
                        
                        messages.success(request, f'✅ Fichier {fichier_planning.name} uploadé avec succès! ({row_count} lignes détectées)')
                        
                        # Charger automatiquement le fichier agents par défaut s'il existe
                        info_path = os.path.join(settings.BASE_DIR, 'info.xlsx')
                        if os.path.exists(info_path):
                            gestionnaire.charger_agents(info_path)
                            messages.info(request, '📂 Fichier info.xlsx chargé automatiquement')
                        else:
                            messages.warning(request, '⚠️ Fichier info.xlsx non trouvé. Vous pouvez importer les agents depuis la section "Gestion Agents".')
                        
                        # Rediriger vers la même page pour afficher les infos
                        return redirect('upload')
                    else:
                        messages.error(request, '❌ Erreur lors du chargement du planning dans le gestionnaire')
                else:
                    messages.error(request, f'❌ Fichier invalide : {error_message}')
                    
            except Exception as e:
                messages.error(request, f'❌ Erreur lors du traitement du fichier : {str(e)}')
        else:
            messages.error(request, '❌ Formulaire invalide')
    else:
        form = UploadFileForm()
    
    context = {
        'form': form,
        'uploaded_file': uploaded_file_info,
        'planning_charge': planning_charge,
    }
    return render(request, 'gestion/upload.html', context)

@login_required
def liste_transports(request):
  
    # Vérifier si un planning est chargé
    if not request.session.get('planning_charge'):
        messages.warning(request, "Veuillez d'abord charger un fichier de planning")
        return redirect('upload')
    
    gestionnaire = GestionnaireTransport()
    
    # Essayer de recharger le planning
    planning_charge = False
    if gestionnaire.recharger_planning_depuis_session():
        planning_charge = True
        gestionnaire.dates_par_jour = request.session.get('gestionnaire_dates', {})
    else:
        messages.error(request, 'Erreur de chargement du planning. Veuillez recharger le fichier.')
        return redirect('upload')
    
    # Charger les agents
    temp_agents_path = os.path.join(settings.BASE_DIR, 'temp_agents.xlsx')
    if os.path.exists(temp_agents_path):
        gestionnaire.charger_agents(temp_agents_path)
    else:
        info_path = os.path.join(settings.BASE_DIR, 'info.xlsx')
        if os.path.exists(info_path):
            gestionnaire.charger_agents(info_path)
        else:
            messages.warning(request, 'Aucun fichier agents trouvé. Les informations seront incomplètes.')
    
    liste_transports = []
    form = FiltreForm(request.GET or None)
    
    if form.is_valid():
        # FORCER le nettoyage des données
        jour_selectionne = form.cleaned_data.get('jour', 'Tous')
        type_transport_selectionne = form.cleaned_data.get('type_transport', 'tous')
        
        # DEBUG: Afficher les valeurs
        print(f"DEBUG - Filtres: Jour={jour_selectionne}, Type={type_transport_selectionne}")
        
        if not gestionnaire.df_planning.empty:
            # Créer un faux objet form avec les données nettoyées
            class FiltreFormSimple:
                def __init__(self, jour, type_transport, heure_ete=False, filtre_agents='tous'):
                    self.cleaned_data = {
                        'jour': jour,
                        'type_transport': type_transport,
                        'heure_ete': heure_ete,
                        'filtre_agents': filtre_agents
                    }
            
            # Passer les données GET pour les heures spécifiques
            request.GET._mutable = True
            form_simple = FiltreFormSimple(
                jour_selectionne,
                type_transport_selectionne,
                form.cleaned_data.get('heure_ete', False),
                form.cleaned_data.get('filtre_agents', 'tous')
            )
            
            # Ajouter les données GET au form_simple pour récupérer les heures cochées
            form_simple.data = request.GET
            
            liste_transports = gestionnaire.traiter_donnees(form_simple)
            
            print(f"DEBUG - {len(liste_transports)} transports trouvés")
    
    # Grouper par type de transport pour l'affichage
    ramassages = [t for t in liste_transports if t['type_transport'] == 'ramassage']
    departs = [t for t in liste_transports if t['type_transport'] == 'depart']
    
    # Récupérer les heures configurées
    heures_ramassage_config = gestionnaire.get_heures_config('ramassage')
    heures_depart_config = gestionnaire.get_heures_config('depart')
    
    # Compter les agents incomplets
    agents_incomplets = sum(1 for t in liste_transports if not t.get('est_complet', True))
    
    context = {
        'form': form,
        'liste_transports': liste_transports,
        'ramassages': ramassages,
        'departs': departs,
        'dates_par_jour': gestionnaire.dates_par_jour,
        'heures_ramassage_config': heures_ramassage_config,
        'heures_depart_config': heures_depart_config,
        'agents_incomplets': agents_incomplets,
        'planning_charge': planning_charge,
    }
    return render(request, 'gestion/liste_transports.html', context)

# Dans views.py - remplacer la fonction generer_pdf actuelle par :

@login_required
def generer_pdf(request):
 
    if not request.session.get('planning_charge'):
        messages.warning(request, "Veuillez d'abord charger un fichier de planning")
        return redirect('upload')
    
    # Récupérer TOUS les paramètres GET
    jour = request.GET.get('jour', 'Tous')
    type_transport = request.GET.get('type_transport', 'tous')
    heure_ete = request.GET.get('heure_ete', 'false') == 'on'
    filtre_agents = request.GET.get('filtre_agents', 'tous')
    heure_specifique = request.GET.get('heure_specifique', '')
    
    print(f"DEBUG PDF - Paramètres: jour={jour}, type={type_transport}, heure_ete={heure_ete}")
    
    # Créer la réponse PDF
    response = HttpResponse(content_type='application/pdf')
    filename = f"liste_transports_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Titre principal
    titre = Paragraph(f"LISTE DES TRANSPORTS", styles['Title'])
    elements.append(titre)
    
    # Sous-titre avec date
    sous_titre = Paragraph(
        f"Généré le : {datetime.now().strftime('%d/%m/%Y à %H:%M')}", 
        styles['Heading3']
    )
    elements.append(sous_titre)
    
    # Filtres appliqués
    filtres_text = f"Filtres appliqués : "
    filtres_list = []
    if jour != 'Tous':
        filtres_list.append(f"Jour: {jour}")
    if type_transport != 'tous':
        filtres_list.append(f"Type: {type_transport}")
    if heure_ete:
        filtres_list.append("Heure d'été activée")
    if heure_specifique:
        filtres_list.append(f"Heure spécifique: {heure_specifique}h")
    if filtre_agents != 'tous':
        filtres_list.append(f"Agents: {filtre_agents}")
    
    if filtres_list:
        filtres_text += ", ".join(filtres_list)
    else:
        filtres_text += "Aucun filtre (tous les transports)"
    
    filtres_para = Paragraph(filtres_text, styles['Normal'])
    elements.append(filtres_para)
    elements.append(Paragraph("<br/>", styles['Normal']))
    
    # Recharger les données exactement comme dans liste_transports
    gestionnaire = GestionnaireTransport()
    if gestionnaire.recharger_planning_depuis_session():
        gestionnaire.dates_par_jour = request.session.get('gestionnaire_dates', {})
        
        # Charger les agents
        temp_agents_path = os.path.join(settings.BASE_DIR, 'temp_agents.xlsx')
        if os.path.exists(temp_agents_path):
            gestionnaire.charger_agents(temp_agents_path)
        else:
            info_path = os.path.join(settings.BASE_DIR, 'info.xlsx')
            if os.path.exists(info_path):
                gestionnaire.charger_agents(info_path)
        
        # Créer un form avec les mêmes paramètres
        class FiltreFormPDF:
            def __init__(self, jour, type_transport, heure_ete, filtre_agents, heure_specifique):
                self.cleaned_data = {
                    'jour': jour,
                    'type_transport': type_transport,
                    'heure_ete': heure_ete,
                    'filtre_agents': filtre_agents
                }
                self.data = {
                    'heure_specifique': heure_specifique
                }
        
        form_pdf = FiltreFormPDF(jour, type_transport, heure_ete, filtre_agents, heure_specifique)
        liste_transports = gestionnaire.traiter_donnees(form_pdf)
        
        if liste_transports:
            # Grouper par jour ET par type de transport
            jours_ordre = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
            transports_par_jour = {}
            
            for transport in liste_transports:
                jour_nom = transport['jour']
                if jour_nom not in transports_par_jour:
                    transports_par_jour[jour_nom] = {'ramassage': [], 'depart': []}
                transports_par_jour[jour_nom][transport['type_transport']].append(transport)
            
            # Trier les jours dans l'ordre
            jours_tries = sorted(
                transports_par_jour.keys(), 
                key=lambda x: jours_ordre.index(x) if x in jours_ordre else 99
            )
            
            for jour_nom in jours_tries:
                transports = transports_par_jour[jour_nom]
                
                # Titre du jour avec date réelle
                date_reelle = gestionnaire.dates_par_jour.get(jour_nom, 'Date non définie')
                titre_jour = Paragraph(
                    f"<b>{jour_nom.upper()} - {date_reelle}</b>", 
                    styles['Heading2']
                )
                elements.append(titre_jour)
                elements.append(Paragraph("<br/>", styles['Normal']))
                
                # RAMASSAGES
                if transports['ramassage']:
                    elements.append(Paragraph("<b>RAMASSAGES :</b>", styles['Heading3']))
                    
                    # Créer le tableau des ramassages
                    data_ramassage = [
                        ['Agent', 'Heure', 'Adresse', 'Téléphone', 'Société', 'Statut']
                    ]
                    
                    for transport in sorted(transports['ramassage'], key=lambda x: x['heure']):
                        statut = "Complet" if transport.get('est_complet', False) else "Incomplet"
                        data_ramassage.append([
                            transport['agent'],
                            f"{transport['heure_affichage']}",
                            transport['adresse'][:50] + "..." if len(transport['adresse']) > 50 else transport['adresse'],
                            transport['telephone'],
                            transport['societe'],
                            statut
                        ])
                    
                    # Style du tableau
                    style_ramassage = TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0fff0')),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
                    ])
                    
                    table_ramassage = Table(data_ramassage, colWidths=[4*cm, 2*cm, 6*cm, 3*cm, 3*cm, 2*cm])
                    table_ramassage.setStyle(style_ramassage)
                    elements.append(table_ramassage)
                    elements.append(Paragraph("<br/><br/>", styles['Normal']))
                
                # DÉPARTS
                if transports['depart']:
                    elements.append(Paragraph("<b>DÉPARTS :</b>", styles['Heading3']))
                    
                    # Créer le tableau des départs
                    data_depart = [
                        ['Agent', 'Heure', 'Adresse', 'Téléphone', 'Société', 'Statut']
                    ]
                    
                    for transport in sorted(transports['depart'], key=lambda x: x['heure']):
                        statut = "Complet" if transport.get('est_complet', False) else "Incomplet"
                        data_depart.append([
                            transport['agent'],
                            f"{transport['heure_affichage']}",
                            transport['adresse'][:50] + "..." if len(transport['adresse']) > 50 else transport['adresse'],
                            transport['telephone'],
                            transport['societe'],
                            statut
                        ])
                    
                    # Style du tableau
                    style_depart = TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ffc107')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fffdf0')),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
                    ])
                    
                    table_depart = Table(data_depart, colWidths=[4*cm, 2*cm, 6*cm, 3*cm, 3*cm, 2*cm])
                    table_depart.setStyle(style_depart)
                    elements.append(table_depart)
                    elements.append(Paragraph("<br/><br/>", styles['Normal']))
                
                # Séparateur entre les jours
                elements.append(Paragraph("_" * 100, styles['Normal']))
                elements.append(Paragraph("<br/><br/>", styles['Normal']))
            
            # Résumé statistique
            elements.append(Paragraph("<b>RÉSUMÉ STATISTIQUE</b>", styles['Heading2']))
            
            total_agents = len(liste_transports)
            agents_complets = sum(1 for t in liste_transports if t.get('est_complet', False))
            agents_incomplets = total_agents - agents_complets
            total_ramassages = len([t for t in liste_transports if t['type_transport'] == 'ramassage'])
            total_departs = len([t for t in liste_transports if t['type_transport'] == 'depart'])
            
            resume_data = [
                ['Total agents', str(total_agents)],
                ['Agents complets', str(agents_complets)],
                ['Agents incomplets', str(agents_incomplets)],
                ['Ramassages', str(total_ramassages)],
                ['Départs', str(total_departs)],
            ]
            
            style_resume = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ])
            
            table_resume = Table(resume_data, colWidths=[8*cm, 8*cm])
            table_resume.setStyle(style_resume)
            elements.append(table_resume)
            
        else:
            elements.append(Paragraph(
                "<b>AUCUN TRANSPORT TROUVÉ</b><br/>Aucun agent ne correspond aux critères de filtrage.", 
                styles['Heading3']
            ))
    
    else:
        elements.append(Paragraph(
            "ERREUR : Impossible de charger le planning. Veuillez recharger le fichier EMS.xlsx.", 
            styles['Heading3']
        ))
    
    # Pied de page
    elements.append(Paragraph("<br/><br/>", styles['Normal']))
    footer = Paragraph(
        f"Document généré automatiquement par le Système de Gestion Transport | Page 1/1", 
        styles['Normal']
    )
    elements.append(footer)
    
    # Générer le PDF
    try:
        doc.build(elements)
        return response
    except Exception as e:
        print(f"❌ Erreur génération PDF: {e}")
        messages.error(request, f"Erreur lors de la génération du PDF: {str(e)}")
        return redirect('liste_transports')
@login_required
def gestion_chauffeurs(request):
    # ========== FILTRAGE PAR DATE ==========
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    
    # Calculer les dates par défaut (début et fin du mois courant)
    aujourd_hui = date.today()
    premier_du_mois = date(aujourd_hui.year, aujourd_hui.month, 1)
    
    # Dernier jour du mois
    if aujourd_hui.month == 12:
        dernier_du_mois = date(aujourd_hui.year + 1, 1, 1) - timedelta(days=1)
    else:
        dernier_du_mois = date(aujourd_hui.year, aujourd_hui.month + 1, 1) - timedelta(days=1)
    
    # Si aucune date n'est fournie, utiliser les valeurs par défaut
    if not date_debut or date_debut == 'None':
        date_debut = premier_du_mois.strftime('%Y-%m-%d')
    
    if not date_fin or date_fin == 'None':
        date_fin = dernier_du_mois.strftime('%Y-%m-%d')
    # Récupérer les courses AVEC FILTRAGE
    courses_query = Course.objects.all().order_by('-date_reelle', 'heure')
    
    # Appliquer les filtres date
    if date_debut and date_debut != 'None':
        try:
            courses_query = courses_query.filter(date_reelle__gte=date_debut)
        except Exception as e:
            print(f"Erreur filtre date début: {e}")
    
    if date_fin and date_fin != 'None':
        try:
            courses_query = courses_query.filter(date_reelle__lte=date_fin)
        except Exception as e:
            print(f"Erreur filtre date fin: {e}")
    
    # ========== CALCUL DU PRIX TOTAL ==========
    total_prix_courses = 0.0
    courses_filtrees = []
    
    for course in courses_query:
        courses_filtrees.append(course)
        
        # Calculer le prix de la course
        if course.prix_total and course.prix_total > 0:
            total_prix_courses += float(course.prix_total)
        else:
            # Si pas de prix défini, utiliser le prix par défaut selon le type de chauffeur
            if course.chauffeur.type_chauffeur == 'taxi':
                total_prix_courses += getattr(settings, 'PRIX_COURSE_TAXI', 15.0)
            elif course.chauffeur.type_chauffeur == 'prive':
                total_prix_courses += getattr(settings, 'PRIX_COURSE_CHAUFFEUR', 10.0)
    
    # ========== FORMULAIRE D'AFFECTATION ==========
    chauffeurs_disponibles = Chauffeur.objects.filter(actif=True).order_by('nom')
    
    if request.method == 'POST':
        form = AffectationMultipleForm(request.POST)
        if form.is_valid():
            chauffeur = form.cleaned_data['chauffeur']
            heure = form.cleaned_data['heure']
            type_transport = form.cleaned_data['type_transport']
            jour = form.cleaned_data['jour']
            agents_json = form.cleaned_data['agents']
            prix_personnalise = request.POST.get('prix', '').strip()  # Récupérer le prix personnalisé
            
            try:
                agents_noms = json.loads(agents_json)
            except json.JSONDecodeError:
                agents_noms = []
                messages.error(request, 'Erreur dans la sélection des agents')
            
            gestionnaire = GestionnaireTransport()
            gestionnaire.dates_par_jour = request.session.get('gestionnaire_dates', {})
            date_reelle_str = gestionnaire.dates_par_jour.get(jour, date.today().strftime("%d/%m/%Y"))
            
            try:
                date_reelle = datetime.strptime(date_reelle_str, "%d/%m/%Y").date()
            except:
                date_reelle = date.today()
            
            # VÉRIFICATION : Vérifier si des agents sont déjà affectés ce jour
            agents_deja_affectes = []
            for agent_nom in agents_noms:
                try:
                    agent = Agent.objects.get(nom=agent_nom)
                    existe_deja = Affectation.objects.filter(
                        agent=agent,
                        date_reelle=date_reelle
                    ).exists()
                    
                    if existe_deja:
                        agents_deja_affectes.append(agent_nom)
                        
                except Agent.DoesNotExist:
                    continue
            
            # Si des agents sont déjà affectés, afficher un message d'erreur
            if agents_deja_affectes:
                messages.error(request, 
                    f"Certains agents sont déjà affectés le {date_reelle_str} : {', '.join(agents_deja_affectes)}")
                return redirect('chauffeurs')
            
            # ========== GESTION DU PRIX - CORRECTION CRITIQUE ==========
            prix_total_final = 0.0

            # DÉTERMINER LE PRIX À UTILISER
            if prix_personnalise and prix_personnalise.strip():
                try:
                    prix_total_final = float(prix_personnalise)
                    print(f"✅ Prix personnalisé utilisé: {prix_total_final}")
                except ValueError:
        # Prix automatique selon le type de chauffeur si le prix personnalisé est invalide
                    if chauffeur.type_chauffeur == 'taxi':
                        prix_total_final = getattr(settings, 'PRIX_COURSE_TAXI', 15.0)
                    elif chauffeur.type_chauffeur == 'prive':
                        prix_total_final = getattr(settings, 'PRIX_COURSE_CHAUFFEUR', 10.0)
                    else:
                        prix_total_final = getattr(settings, 'PRIX_COURSE_SOCIETE', 0.0)
                    messages.warning(request, f"Prix invalide. Utilisation du prix par défaut: {prix_total_final}")
            else:
    # Prix automatique selon le type de chauffeur - UTILISER LE PRIX DU CHAUFFEUR
                if chauffeur.prix_course_par_defaut and chauffeur.prix_course_par_defaut > 0:
                    prix_total_final = float(chauffeur.prix_course_par_defaut)
                    print(f"💰 Prix chauffeur: {prix_total_final} (Type: {chauffeur.type_chauffeur})")
                else:
        # Fallback aux prix par défaut
                    if chauffeur.type_chauffeur == 'taxi':
                        prix_total_final = getattr(settings, 'PRIX_COURSE_TAXI', 15.0)
                    elif chauffeur.type_chauffeur == 'prive':
                        prix_total_final = getattr(settings, 'PRIX_COURSE_CHAUFFEUR', 10.0)
                    else:
                        prix_total_final = getattr(settings, 'PRIX_COURSE_SOCIETE', 0.0)
                    print(f"💰 Prix automatique (fallback): {prix_total_final} (Type: {chauffeur.type_chauffeur})")            
            # Identifier les sociétés uniques parmi les agents
            societes_dans_course = {}
            for agent_nom in agents_noms:
                try:
                    agent = Agent.objects.get(nom=agent_nom)
                    societe_nom = agent.get_societe_display()
                    if societe_nom and societe_nom != "Non spécifié":
                        if societe_nom not in societes_dans_course:
                            societes_dans_course[societe_nom] = 0
                        societes_dans_course[societe_nom] += 1
                except Agent.DoesNotExist:
                    # Créer l'agent temporairement pour obtenir la société
                    societe_nom = "Société à compléter"
                    if societe_nom not in societes_dans_course:
                        societes_dans_course[societe_nom] = 0
                    societes_dans_course[societe_nom] += 1
            
            print(f"📊 Sociétés dans la course: {societes_dans_course}")
            print(f"📊 Nombre de sociétés: {len(societes_dans_course)}")
            
            # Créer ou mettre à jour la course
            course, created = Course.objects.get_or_create(
                chauffeur=chauffeur,
                type_transport=type_transport,
                heure=heure,
                jour=jour,
                date_reelle=date_reelle,
                defaults={
                    'prix_total': prix_total_final
                }
            )
            
            # Si la course existe déjà, mettre à jour le prix SI un prix personnalisé est fourni
            if not created and prix_personnalise and prix_personnalise.strip():
                course.prix_total = prix_total_final
                course.save()
                print(f"📝 Course existante mise à jour avec prix: {prix_total_final}")
            
            # Créer les affectations avec calcul du prix par société
            affectations_creees = 0
            
            for agent_nom in agents_noms:
                try:
                    agent, created_agent = Agent.objects.get_or_create(
                        nom=agent_nom,
                        defaults={
                            'adresse': 'Adresse à compléter',
                            'telephone': '00000000',
                            'societe_texte': 'Société à compléter'
                        }
                    )
                    
                    # Calculer le prix par société
                    societe_nom = agent.get_societe_display()
                    prix_par_societe = 0.0
                    
                    if societes_dans_course and len(societes_dans_course) > 0:
                        prix_par_societe = prix_total_final / len(societes_dans_course)
                    
                    print(f"💰 {agent.nom} - Société: {societe_nom} - Prix société: {prix_par_societe}")
                    
                    # Vérifier une dernière fois (double sécurité)
                    existe_deja = Affectation.objects.filter(
                        course=course,
                        agent=agent
                    ).exists()
                    
                    if not existe_deja:
                        affectation = Affectation(
                            course=course,
                            chauffeur=chauffeur,
                            heure=heure,
                            agent=agent,
                            type_transport=type_transport,
                            jour=jour,
                            date_reelle=date_reelle,
                            prix_course=prix_total_final,
                            prix_societe=round(prix_par_societe, 3)  # CORRECTION: Stocker le prix par société
                        )
                        affectation.save()
                        affectations_creees += 1
                    
                except Exception as e:
                    print(f"Erreur avec l'agent {agent_nom}: {str(e)}")
                    messages.error(request, f"Erreur avec l'agent {agent_nom}: {str(e)}")
            
            if affectations_creees > 0:
                messages.success(request, f'{affectations_creees} affectation(s) créée(s) avec succès!')
            else:
                messages.warning(request, 'Aucune nouvelle affectation créée')
            
            return redirect('chauffeurs')
        else:
            messages.error(request, 'Veuillez corriger les erreurs dans le formulaire')
    else:
        form = AffectationMultipleForm()
    
    # Formulaire pour ajouter un chauffeur
    form_chauffeur = ChauffeurForm()
    
    context = {
        'courses': courses_filtrees,
        'total_courses': len(courses_filtrees),
        'total_affectations': Affectation.objects.count(),
        'chauffeurs_disponibles': chauffeurs_disponibles,
        'form': form,
        'form_chauffeur': form_chauffeur,
        # Variables pour le filtrage date
        'date_debut': date_debut,
        'date_fin': date_fin,
        'total_prix_courses': round(total_prix_courses, 2),
        # Dates par défaut pour le template
        'aujourd_hui_mois_debut': premier_du_mois.strftime('%Y-%m-%d'),
        'aujourd_hui_mois_fin': dernier_du_mois.strftime('%Y-%m-%d'),
    }
    
    return render(request, 'gestion/chauffeurs.html', context)
@login_required
def api_liste_societes(request):
   
    societes = Societe.objects.all().order_by('nom').values('id', 'nom')
    return JsonResponse(list(societes), safe=False)

@login_required
def api_modifier_agent(request):
   
    if request.method == 'POST':
        try:
            nom = request.POST.get('nom')
            adresse = request.POST.get('adresse')
            telephone = request.POST.get('telephone')
            societe_id = request.POST.get('societe_id')
            societe_texte = request.POST.get('societe_texte')
            voiture_personnelle = request.POST.get('voiture_personnelle') == 'on'
            
            # Rechercher ou créer l'agent
            agent, created = Agent.objects.get_or_create(
                nom=nom,
                defaults={
                    'adresse': adresse,
                    'telephone': telephone,
                    'voiture_personnelle': voiture_personnelle
                }
            )
            
            if not created:
                # Mettre à jour l'agent existant
                agent.adresse = adresse
                agent.telephone = telephone
                agent.voiture_personnelle = voiture_personnelle
                
                # Gérer la société
                if societe_id:
                    try:
                        societe = Societe.objects.get(id=societe_id)
                        agent.societe = societe
                        agent.societe_texte = None
                    except Societe.DoesNotExist:
                        agent.societe = None
                        agent.societe_texte = societe_texte
                elif societe_texte:
                    agent.societe = None
                    agent.societe_texte = societe_texte
                else:
                    agent.societe = None
                    agent.societe_texte = None
                
                agent.save()
            
            return JsonResponse({'success': True, 'message': 'Agent mis à jour avec succès'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
@login_required
def supprimer_agents_multiple(request):
   
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            agent_ids = data.get('agent_ids', [])
            
            # Supprimer les agents
            deleted_count, _ = Agent.objects.filter(id__in=agent_ids).delete()
            
            return JsonResponse({
                'success': True,
                'deleted': deleted_count,
                'message': f'{deleted_count} agent(s) supprimé(s) avec succès'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@login_required
def ajouter_chauffeur(request):
    "Vue pour ajouter un chauffeur via AJAX"
    if request.method == 'POST':
        form = ChauffeurForm(request.POST)
        if form.is_valid():
            chauffeur = form.save()
            return JsonResponse({
                'success': True,
                'chauffeur_id': chauffeur.id,
                'chauffeur_nom': chauffeur.nom,
                'type_chauffeur': chauffeur.type_chauffeur,
                'prix_par_defaut': float(chauffeur.prix_course_par_defaut)
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    return JsonResponse({'success': False, 'errors': 'Méthode non autorisée'})

@login_required
def supprimer_affectation(request, id):
    affectation = get_object_or_404(Affectation, id=id)
    affectation.delete()
    messages.success(request, 'Affectation supprimée avec succès')
    return redirect('chauffeurs')

@login_required
def supprimer_course(request, id):
    course = get_object_or_404(Course, id=id)
    nb_affectations = course.affectation_set.count()
    course.delete()
    messages.success(request, f'Course et {nb_affectations} affectation(s) supprimée(s) avec succès')
    return redirect('chauffeurs')

@login_required
def get_agents_non_affectes(request):
    jour = request.GET.get('jour', '')
    type_transport = request.GET.get('type_transport', '')
    heure = request.GET.get('heure', '')
    
    print(f"🔍 API Appelée - Jour: {jour}, Type: {type_transport}, Heure: {heure}")
    
    if not jour or not type_transport or not heure:
        return JsonResponse([], safe=False)
    
    try:
        # Convertir l'heure en entier
        heure_int = int(heure)
        
        # CORRECTION : Pour les heures 0-3 (nuit), chercher aussi 24-27
        heures_a_chercher = [heure_int]
        if heure_int in [0, 1, 2, 3]:
            heures_a_chercher.append(heure_int + 24)  # Chercher aussi 24h, 25h, etc.
        
        print(f"🕒 Heures à chercher: {heures_a_chercher}")
        
        # Recharger le planning
        gestionnaire = GestionnaireTransport()
        if not gestionnaire.recharger_planning_depuis_session():
            return JsonResponse([], safe=False)
        
        gestionnaire.dates_par_jour = request.session.get('gestionnaire_dates', {})
        
        # Charger les agents
        temp_agents_path = os.path.join(settings.BASE_DIR, 'temp_agents.xlsx')
        if os.path.exists(temp_agents_path):
            gestionnaire.charger_agents(temp_agents_path)
        else:
            info_path = os.path.join(settings.BASE_DIR, 'info.xlsx')
            if os.path.exists(info_path):
                gestionnaire.charger_agents(info_path)
        
        # Obtenir la date réelle
        date_reelle = gestionnaire.dates_par_jour.get(jour, '')
        if not date_reelle:
            return JsonResponse([], safe=False)
        
        date_obj = datetime.strptime(date_reelle, "%d/%m/%Y").date()
        
        # 1. AGENTS PRIMAIRES : Ceux programmés à cette heure exacte
        class FiltreFormAPI:
            def __init__(self, jour, type_transport):
                self.cleaned_data = {
                    'jour': jour,
                    'type_transport': type_transport,
                    'heure_ete': False,
                    'filtre_agents': 'tous'
                }
        
        form_api = FiltreFormAPI(jour, type_transport)
        tous_agents_jour = gestionnaire.traiter_donnees(form_api)
        
        agents_principaux = []
        for transport in tous_agents_jour:
            # CORRECTION : Chercher dans toutes les heures (incluant 24h+)
            if (transport['heure'] in heures_a_chercher or 
                (transport['heure'] >= 24 and (transport['heure'] - 24) in heures_a_chercher)):
                if transport['type_transport'] == type_transport:
                    agents_principaux.append(transport['agent'])
        
        print(f"🎯 Agents principaux ({heure}h): {agents_principaux}")
        
        # 2. AGENTS SECONDAIRES : Tous les agents du planning ce jour (autres heures)
        agents_secondaires = []
        for transport in tous_agents_jour:
            if (transport['agent'] not in agents_principaux and 
                transport['type_transport'] == type_transport):
                agents_secondaires.append({
                    'nom': transport['agent'],
                    'heure_reelle': transport['heure'],
                    'heure_affichee': transport['heure_affichage']
                })
        
        print(f"🔄 Agents secondaires: {len(agents_secondaires)}")
        
        # 3. Filtrer les agents déjà affectés CE JOUR
        agents_deja_affectes = Affectation.objects.filter(
            date_reelle=date_obj
        ).values_list('agent__nom', flat=True)
        
        # 4. Combiner et filtrer
        tous_agents_disponibles = []
        
        # Ajouter les agents principaux (non déjà affectés)
        for agent in agents_principaux:
            if agent not in agents_deja_affectes:
                tous_agents_disponibles.append({
                    'nom': agent,
                    'type': 'principal',
                    'heure': heure_int,
                    'info': f"{type_transport} {heure}h (programmé)"
                })
        
        # Ajouter les agents secondaires (non déjà affectés)
        for agent_data in agents_secondaires:
            if agent_data['nom'] not in agents_deja_affectes:
                tous_agents_disponibles.append({
                    'nom': agent_data['nom'],
                    'type': 'secondaire',
                    'heure': agent_data['heure_reelle'],
                    'info': f"{type_transport} {agent_data['heure_affichee']} (autre horaire)"
                })
        
        # 5. Trier par nom
        tous_agents_disponibles.sort(key=lambda x: x['nom'])
        
        print(f"✅ Total agents disponibles: {len(tous_agents_disponibles)}")
        
        # Retourner en JSON
        return JsonResponse(tous_agents_disponibles, safe=False)
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse([], safe=False)
@login_required
def get_heures_par_type(request):
   
    type_transport = request.GET.get('type_transport', '')
    
    if not type_transport:
        return JsonResponse([], safe=False)
    
    try:
        # Récupérer les heures actives de la base de données
        heures = HeureTransport.objects.filter(
            type_transport=type_transport,
            active=True
        ).order_by('ordre', 'heure')
        
        # Formater pour le select
        options = [{'value': heure.heure, 'text': heure.libelle} for heure in heures]
        
        return JsonResponse(options, safe=False)
        
    except Exception as e:
        print(f"Erreur get_heures_par_type: {str(e)}")
        # Fallback : valeurs par défaut
        if type_transport == 'ramassage':
            options = [
                {'value': 6, 'text': 'Ramassage 6h'},
                {'value': 7, 'text': 'Ramassage 7h'},
                {'value': 8, 'text': 'Ramassage 8h'},
                {'value': 22, 'text': 'Ramassage 22h'}
            ]
        else:
            options = [
                {'value': 22, 'text': 'Départ 22h'},
                {'value': 23, 'text': 'Départ 23h'},
                {'value': 0, 'text': 'Départ 0h'},
                {'value': 1, 'text': 'Départ 1h'},
                {'value': 2, 'text': 'Départ 2h'},
                {'value': 3, 'text': 'Départ 3h'}
            ]
        
        return JsonResponse(options, safe=False)
@login_required
def api_carte_course(request, course_id):
    try:
        print(f"🚀 Début api_carte_course pour course_id: {course_id}")
        
        course = get_object_or_404(Course, id=course_id)
        print(f"✅ Course trouvée: {course.chauffeur.nom} - {course.date_reelle}")
        
        # ============ POINT DE DÉPART FIXE ============
        point_depart_fixe = {
            'nom': 'DÉPART FIXE - Complexe Zaoui',
            'adresse': "rue rabat complexe zaoui sousse 4000",
            'latitude': 35.8342,
            'longitude': 10.6296,
            'societe': 'POINT DE DÉPART',
            'telephone': '',
            'type_transport': 'depart',
            'heure': course.heure,
            'ordre': 0,
            'agent_id': 0,
            'corrige_manuellement': True
        }
        
        affectations = Affectation.objects.filter(course=course).select_related('agent')
        print(f"📊 {affectations.count()} affectations trouvées")
        
        # Préparer les données pour la carte
        points = []
        positions_utilisees = set()
        
        for affectation in affectations:
            agent = affectation.agent
            
            print(f"👤 Agent: ID={agent.id}, Nom={agent.nom}")
            print(f"📌 Adresse: {agent.adresse}")
            
            # ============ CORRECTION CRITIQUE ICI ============
            # Gestion des adresses incomplètes
            adresse_corrigee = agent.adresse
            latitude_finale = None
            longitude_finale = None
            
            # Dictionnaire de correspondance quartier -> coordonnées
            correspondances_quartiers = {
                'riadh': (35.8085, 10.5920, 'Hay Riadh, Sousse, Tunisie'),
                'cite riadh': (35.8085, 10.5920, 'Hay Riadh, Sousse, Tunisie'),
                'riadh 1': (35.8085, 10.5920, 'Riadh 1, Sousse, Tunisie'),
                'riadh 2': (35.8110, 10.5880, 'Riadh 2, Sousse, Tunisie'),
                'riadh 3': (35.8050, 10.5850, 'Riadh 3, Sousse, Tunisie'),
                'ghodrane': (35.8120, 10.6120, 'Cite Ghodrane, Sousse, Tunisie'),
                'cite ghodrane': (35.8120, 10.6120, 'Cite Ghodrane, Sousse, Tunisie'),
                'cite jawhara': (35.8256, 10.6084, 'Cite Jawhara, Sousse, Tunisie'),
                'sahloul': (35.8350, 10.5960, 'Sahloul, Sousse, Tunisie'),
                'sahloul 1': (35.8350, 10.5960, 'Sahloul 1, Sousse, Tunisie'),
                'sahloul 2': (35.8385, 10.5930, 'Sahloul 2, Sousse, Tunisie'),
                'khezama': (35.8525, 10.6150, 'Khezama Est, Sousse, Tunisie'),
                'khezama est': (35.8525, 10.6150, 'Khezama Est, Sousse, Tunisie'),
                'taffala': (35.8170, 10.6130, 'Taffala, Sousse, Tunisie'),
                'akouda': (35.8680, 10.5650, 'Akouda, Sousse, Tunisie'),
                'Hammam Sousse': (35.8580, 10.5980, 'Hammam Sousse, Sousse, Tunisie'),
                'Khezama Ouest': (35.8485, 10.6050, 'Khezama Ouest, Sousse, Tunisie'),
                'Sidi Abdelhamid': (35.7950, 10.6350, 'Sidi Abdelhamid, Sousse, Tunisie'),
                'medina': (35.8275, 10.6392, 'Medina Sousse, Tunisie'),
                'boujaafar': (35.8340, 10.6400, 'Boujaafar, Sousse, Tunisie'),
                'Kalaa Kebira': (35.8660, 10.5360, 'BKalaa Kebira, Sousse, Tunisie'),
                'Kalaa Seghira': (35.8200, 10.5600, 'Kalaa Seghira, Sousse, Tunisie'),
                'Msaken Centre': (35.7300, 10.5850, 'Msaken Centre, Sousse, Tunisie'),
                'Msaken Ennour': (35.7350, 10.5750, 'Msaken Ennour, Sousse, Tunisie'),
                'Chatt Meriem': (35.9180, 10.5900, 'Chatt Meriem, Sousse, Tunisie'),

            }
            
            adresse_lower = agent.adresse.lower().strip()
            
            # Vérifier si l'adresse correspond à un quartier connu
            quartier_trouve = None
            for quartier, (lat_q, lon_q, adresse_q) in correspondances_quartiers.items():
                if quartier in adresse_lower:
                    quartier_trouve = (lat_q, lon_q, adresse_q)
                    break
            
            if quartier_trouve:
                # Utiliser les coordonnées du quartier avec un petit décalage aléatoire
                import random
                lat_q, lon_q, adresse_q = quartier_trouve
                latitude_finale = lat_q + random.uniform(-0.002, 0.002)
                longitude_finale = lon_q + random.uniform(-0.002, 0.002)
                adresse_corrigee = adresse_q
                print(f"✅ Quartier identifié: {quartier} → {adresse_q}")
            elif agent.latitude and agent.longitude:
                # Utiliser les coordonnées existantes si elles sont valides
                latitude_finale = agent.latitude
                longitude_finale = agent.longitude
                print(f"✅ Coordonnées DB: {latitude_finale}, {longitude_finale}")
            else:
                # Géocoder l'adresse
                try:
                    from gestion.geolocalisation.utils import GeolocalisationManager
                    geo_manager = GeolocalisationManager()
                    result = geo_manager.geocode_adresse(agent.adresse)
                    
                    if result['success']:
                        latitude_finale = result['latitude']
                        longitude_finale = result['longitude']
                        adresse_corrigee = result.get('adresse_formatee', agent.adresse)
                        
                        # Sauvegarder dans la base pour plus tard
                        agent.latitude = latitude_finale
                        agent.longitude = longitude_finale
                        agent.adresse_geocodee = adresse_corrigee
                        agent.derniere_geolocalisation = datetime.now()
                        agent.save()
                        print(f"✅ Géocodage réussi: {latitude_finale}, {longitude_finale}")
                    else:
                        # Fallback: centre de Sousse
                        latitude_finale = 35.8256
                        longitude_finale = 10.6415
                        print(f"⚠️ Géocodage échoué, fallback centre Sousse")
                        
                except Exception as e:
                    print(f"❌ Erreur géocodage: {e}")
                    latitude_finale = 35.8256
                    longitude_finale = 10.6415
            
            # Assurer qu'on a des coordonnées
            if not latitude_finale or not longitude_finale:
                latitude_finale = 35.8256
                longitude_finale = 10.6415
            
            point = {
                'nom': agent.nom,
                'adresse': adresse_corrigee,
                'latitude': latitude_finale,
                'longitude': longitude_finale,
                'societe': agent.get_societe_display(),
                'telephone': agent.telephone,
                'type_transport': affectation.type_transport,
                'heure': affectation.heure,
                'ordre': len(points) + 1,
                'agent_id': agent.id,
                'corrige_manuellement': agent.corrige_manuellement,
                'date_correction': agent.date_correction_coords.strftime("%d/%m/%Y %H:%M") if agent.date_correction_coords else None
            }
            
            # Ajouter un décalage pour éviter la superposition exacte
            position_key = f"{point['latitude']:.4f},{point['longitude']:.4f}"
            if position_key in positions_utilisees:
                import random
                point['latitude'] += random.uniform(-0.0005, 0.0005)
                point['longitude'] += random.uniform(-0.0005, 0.0005)
                point['decalage_auto'] = True
                print(f"⚠️ Décalage appliqué pour éviter superposition: {agent.nom}")
            
            positions_utilisees.add(f"{point['latitude']:.4f},{point['longitude']:.4f}")
            points.append(point)
            print(f"✅ Point ajouté: {agent.nom} - lat: {point['latitude']:.6f}, lon: {point['longitude']:.6f}")
        
        # Reste du code reste inchangé...
        if points:
            print("🔧 Tentative d'optimisation...")
            try:
                from gestion.geolocalisation.utils import GeolocalisationManager
                geo_manager = GeolocalisationManager()
                
                # Créer l'itinéraire optimisé
                print("📐 Optimisation de l'itineraire...")
                itineraire_optimise = geo_manager.optimiser_itineraire(points)
                
                # Ajouter le point de départ fixe à l'itinéraire
                print("📍 Ajout du point de départ fixe à l'itineraire...")
                itineraire_optimise['itineraire'].insert(0, point_depart_fixe)
                
                # Mettre à jour les ordres de visite
                for i, point in enumerate(itineraire_optimise['itineraire']):
                    point['ordre_visite'] = i + 1
                
                # Ajuster le nombre total de points
                itineraire_optimise['nombre_points'] = len(itineraire_optimise['itineraire'])
                itineraire_optimise['point_depart_fixe'] = point_depart_fixe['nom']
                
                # Recalculer la distance avec le point de départ
                if len(itineraire_optimise['itineraire']) > 1:
                    from geopy.distance import geodesic
                    depart = (point_depart_fixe['latitude'], point_depart_fixe['longitude'])
                    premier_agent = (
                        itineraire_optimise['itineraire'][1]['latitude'], 
                        itineraire_optimise['itineraire'][1]['longitude']
                    )
                    distance_depart = geodesic(depart, premier_agent).kilometers
                    
                    itineraire_optimise['distance_totale'] = round(
                        itineraire_optimise.get('distance_totale', 0) + distance_depart, 2
                    )
                
                print(f"✅ Itinéraire optimisé: {len(itineraire_optimise.get('itineraire', []))} points")
                print(f"📏 Distance totale: {itineraire_optimise['distance_totale']} km")
                
                # Générer la carte
                print("🖼️ Génération de la carte...")
                titre_carte = f"{course.get_type_transport_display()} {course.heure}h - {course.chauffeur.nom} - Départ: Complexe Zaoui"
                carte_resultat = geo_manager.creer_carte_itineraire(
                    itineraire_optimise, 
                    titre=titre_carte
                )
                
                if carte_resultat:
                    print(f"✅ Carte générée: {carte_resultat.get('url')}")
                else:
                    print("⚠️ Carte non générée")
                
                response_data = {
                    'success': True,
                    'course_id': course.id,
                    'chauffeur': course.chauffeur.nom,
                    'type_transport': course.get_type_transport_display(),
                    'heure': course.heure,
                    'date': course.date_reelle.strftime("%d/%m/%Y"),
                    'jour': course.jour,
                    'nombre_agents': len(points),
                    'points': points,
                    'itineraire': itineraire_optimise,
                    'carte_url': carte_resultat['url'] if carte_resultat else None,
                    'distance_totale': itineraire_optimise.get('distance_totale', 0),
                    'temps_estime': round(itineraire_optimise.get('distance_totale', 0) / 40 * 60, 1),
                    'point_depart': point_depart_fixe,
                    'debug_info': {
                        'affectations_count': affectations.count(),
                        'points_count': len(points),
                        'itineraire_count': len(itineraire_optimise.get('itineraire', [])),
                        'agents_missing_coords': len([p for p in points if p.get('geocode_auto', False)])
                    }
                }
                
                print(f"📤 Envoi réponse: {len(str(response_data))} bytes")
                return JsonResponse(response_data)
                
            except Exception as e:
                print(f"❌ Erreur génération carte: {e}")
                import traceback
                traceback.print_exc()
                return JsonResponse({
                    'success': False,
                    'error': f"Erreur génération carte: {str(e)}",
                    'details': traceback.format_exc()
                })
        else:
            print("❌ Aucun point avec coordonnées")
            # Même sans points, afficher le point de départ
            itineraire_depart_seul = {
                'itineraire': [point_depart_fixe],
                'nombre_points': 1,
                'distance_totale': 0,
                'point_depart_fixe': point_depart_fixe['nom']
            }
            
            return JsonResponse({
                'success': True,
                'course_id': course.id,
                'chauffeur': course.chauffeur.nom,
                'type_transport': course.get_type_transport_display(),
                'heure': course.heure,
                'date': course.date_reelle.strftime("%d/%m/%Y"),
                'jour': course.jour,
                'nombre_agents': 0,
                'points': [],
                'itineraire': itineraire_depart_seul,
                'carte_url': None,
                'distance_totale': 0,
                'temps_estime': 0,
                'point_depart': point_depart_fixe,
                'message': 'Course sans agents - affichage du point de départ uniquement'
            })
            
    except Exception as e:
        print(f"❌ Erreur API carte: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
@login_required
@user_passes_test(is_admin)
def valider_course_admin(request, course_id):
    
    if request.method == 'POST':
        course = get_object_or_404(Course, id=course_id)
        notes = request.POST.get('notes', '')
        
        if course.valider_par_admin(notes):
            messages.success(request, f'Course {course} validée avec succès')
        else:
            messages.error(request, 'Erreur lors de la validation')
        
        return redirect('chauffeurs')
    
    return redirect('chauffeurs')

@login_required
@user_passes_test(is_admin)
def refuser_course_admin(request, course_id):
 
    if request.method == 'POST':
        course = get_object_or_404(Course, id=course_id)
        notes = request.POST.get('notes', '')
        
        if course.refuser_par_admin(notes):
            messages.success(request, f'Course {course} refusée')
        else:
            messages.error(request, 'Erreur lors du refus')
        
        return redirect('chauffeurs')
    
    return redirect('chauffeurs')
@login_required
@user_passes_test(is_admin)
def courses_en_attente_validation(request):
   
    courses = Course.objects.filter(
        statut='demande_validation'
    ).order_by('-demande_validation_at', 'date_reelle')

# Dans la fonction rapport_paie, remplacez cette partie :

@user_passes_test(is_admin)
def rapport_paie(request):
    # Récupérer les dates de filtrage
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    
    # Calculer les dates par défaut
    aujourd_hui = date.today()
    premier_du_mois = date(aujourd_hui.year, aujourd_hui.month, 1)
    
    if aujourd_hui.month == 12:
        dernier_du_mois = date(aujourd_hui.year + 1, 1, 1) - timedelta(days=1)
    else:
        dernier_du_mois = date(aujourd_hui.year, aujourd_hui.month + 1, 1) - timedelta(days=1)
    
    # Si aucune date n'est fournie, utiliser les valeurs par défaut
    if not date_debut or date_debut == 'None':
        date_debut = premier_du_mois.strftime('%Y-%m-%d')
    
    if not date_fin or date_fin == 'None':
        date_fin = dernier_du_mois.strftime('%Y-%m-%d')
    
    # Filtrer les courses PAR DATE ET PAR STATUT "validée"
    courses_query = Course.objects.filter(statut='validee')
    
    if date_debut and date_debut != 'None':
        courses_query = courses_query.filter(date_reelle__gte=date_debut)
    if date_fin and date_fin != 'None':
        courses_query = courses_query.filter(date_reelle__lte=date_fin)
    
    # Séparer les courses par type de chauffeur
    courses_taxi = courses_query.filter(chauffeur__type_chauffeur='taxi')
    courses_prive = courses_query.filter(chauffeur__type_chauffeur='prive')
    
    # Dictionnaires pour regrouper par société
    societes_taxi_dict = {}
    societes_prive_dict = {}
    
    # CORRECTION CRITIQUE : TRAITEMENT DES COURSES TAXI
    for course in courses_taxi.select_related('chauffeur').prefetch_related('affectation_set__agent'):
        # PRIORITÉ 1 : Utiliser le prix de la course créée via l'interface chauffeurs
        prix_course_valide = None
        
        # Vérifier si un prix a été défini lors de la création de la course
        if course.prix_total and course.prix_total > 0:
            prix_course_valide = course.prix_total
        else:
            # PRIORITÉ 2 : Vérifier si le chauffeur a un prix par défaut
            if course.chauffeur.prix_course_par_defaut and course.chauffeur.prix_course_par_defaut > 0:
                prix_course_valide = course.chauffeur.prix_course_par_defaut
            else:
                # PRIORITÉ 3 : Utiliser les prix par défaut du système
                if course.chauffeur.type_chauffeur == 'taxi':
                    prix_course_valide = getattr(settings, 'PRIX_COURSE_TAXI', 15.0)
                elif course.chauffeur.type_chauffeur == 'prive':
                    prix_course_valide = getattr(settings, 'PRIX_COURSE_CHAUFFEUR', 10.0)
                else:
                    prix_course_valide = getattr(settings, 'PRIX_COURSE_SOCIETE', 0.0)
        
        # Récupérer toutes les affectations de cette course
        affectations = course.affectation_set.all()
        
        if not affectations.exists():
            continue  # Pas d'agents, on saute
            
        # Grouper les sociétés manuellement
        societes_dans_course = {}
        for affectation in affectations:
            societe_nom = affectation.agent.get_societe_display()
            if societe_nom and societe_nom != "Non spécifié":
                if societe_nom not in societes_dans_course:
                    societes_dans_course[societe_nom] = 0
                societes_dans_course[societe_nom] += 1
        
        if not societes_dans_course:
            continue  # Pas de sociétés identifiées
            
        # Calculer le prix par société avec le prix valide
        from decimal import Decimal
        prix_par_societe = Decimal(str(prix_course_valide)) / Decimal(str(len(societes_dans_course)))
        
        for societe, nb_agents in societes_dans_course.items():
            if societe not in societes_taxi_dict:
                societes_taxi_dict[societe] = {
                    'societe': societe,
                    'nb_courses': 0,
                    'prix_total': Decimal('0.0'),
                    'total_agents': 0
                }
            
            societes_taxi_dict[societe]['total_agents'] += nb_agents
            societes_taxi_dict[societe]['nb_courses'] += 1
            societes_taxi_dict[societe]['prix_total'] += prix_par_societe
    
    # CORRECTION CRITIQUE : TRAITEMENT DES COURSES PRIVÉ (même logique)
    for course in courses_prive.select_related('chauffeur').prefetch_related('affectation_set__agent'):
        # PRIORITÉ 1 : Utiliser le prix de la course créée via l'interface chauffeurs
        prix_course_valide = None
        
        # Vérifier si un prix a été défini lors de la création de la course
        if course.prix_total and course.prix_total > 0:
            prix_course_valide = course.prix_total
        else:
            # PRIORITÉ 2 : Vérifier si le chauffeur a un prix par défaut
            if course.chauffeur.prix_course_par_defaut and course.chauffeur.prix_course_par_defaut > 0:
                prix_course_valide = course.chauffeur.prix_course_par_defaut
            else:
                # PRIORITÉ 3 : Utiliser les prix par défaut du système
                if course.chauffeur.type_chauffeur == 'taxi':
                    prix_course_valide = getattr(settings, 'PRIX_COURSE_TAXI', 15.0)
                elif course.chauffeur.type_chauffeur == 'prive':
                    prix_course_valide = getattr(settings, 'PRIX_COURSE_CHAUFFEUR', 10.0)
                else:
                    prix_course_valide = getattr(settings, 'PRIX_COURSE_SOCIETE', 0.0)
        
        # Récupérer toutes les affectations de cette course
        affectations = course.affectation_set.all()
        
        if not affectations.exists():
            continue  # Pas d'agents, on saute
            
        # Grouper les sociétés manuellement
        societes_dans_course = {}
        for affectation in affectations:
            societe_nom = affectation.agent.get_societe_display()
            if societe_nom and societe_nom != "Non spécifié":
                if societe_nom not in societes_dans_course:
                    societes_dans_course[societe_nom] = 0
                societes_dans_course[societe_nom] += 1
        
        if not societes_dans_course:
            continue  # Pas de sociétés identifiées
            
        # Calculer le prix par société avec le prix valide
        from decimal import Decimal
        prix_par_societe = Decimal(str(prix_course_valide)) / Decimal(str(len(societes_dans_course)))
        
        for societe, nb_agents in societes_dans_course.items():
            if societe not in societes_prive_dict:
                societes_prive_dict[societe] = {
                    'societe': societe,
                    'nb_courses': 0,
                    'prix_total': Decimal('0.0'),
                    'total_agents': 0
                }
            
            societes_prive_dict[societe]['total_agents'] += nb_agents
            societes_prive_dict[societe]['nb_courses'] += 1
            societes_prive_dict[societe]['prix_total'] += prix_par_societe
    
    # Convertir les dictionnaires en listes et arrondir correctement
    stats_taxi = []
    for societe_data in societes_taxi_dict.values():
        societe_data['prix_total'] = float(round(societe_data['prix_total'], 2))
        stats_taxi.append(societe_data)
    
    stats_prive = []
    for societe_data in societes_prive_dict.values():
        societe_data['prix_total'] = float(round(societe_data['prix_total'], 2))
        stats_prive.append(societe_data)
    
    # Trier par prix décroissant
    stats_taxi.sort(key=lambda x: x['prix_total'], reverse=True)
    stats_prive.sort(key=lambda x: x['prix_total'], reverse=True)
    
    # Totaux généraux avec calcul précis
    total_courses = courses_query.count()
    total_affectations = Affectation.objects.filter(course__in=courses_query).count()
    
    # Calculer les totaux avec Decimal
    total_taxi = sum(Decimal(str(stat['prix_total'])) for stat in stats_taxi)
    total_prive = sum(Decimal(str(stat['prix_total'])) for stat in stats_prive)
    total_a_payer = total_taxi + total_prive
    
    # Convertir en float pour l'affichage (arrondi à 2 décimales)
    total_taxi_float = float(round(total_taxi, 2))
    total_prive_float = float(round(total_prive, 2))
    total_a_payer_float = float(round(total_a_payer, 2))
    
    context = {
        'total_courses': total_courses,
        'total_affectations': total_affectations,
        'total_a_payer': total_a_payer_float,
        'stats_taxi': stats_taxi,
        'stats_prive': stats_prive,
        'total_taxi': total_taxi_float,
        'total_prive': total_prive_float,
        'date_debut': date_debut,
        'date_fin': date_fin,
        # Dates par défaut pour le template
        'aujourd_hui_mois_debut': premier_du_mois.strftime('%Y-%m-%d'),
        'aujourd_hui_mois_fin': dernier_du_mois.strftime('%Y-%m-%d'),
    }
    return render(request, 'gestion/paie.html', context)
@user_passes_test(is_admin)
def detail_societe_paie(request, societe_nom):
    # Récupérer les paramètres de filtrage
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    type_chauffeur = request.GET.get('type_chauffeur', 'tous')
    
    # Calculer les dates par défaut (début et fin du mois courant)
    aujourd_hui = date.today()
    premier_du_mois = date(aujourd_hui.year, aujourd_hui.month, 1)
    
    # Dernier jour du mois
    if aujourd_hui.month == 12:
        dernier_du_mois = date(aujourd_hui.year + 1, 1, 1) - timedelta(days=1)
    else:
        dernier_du_mois = date(aujourd_hui.year, aujourd_hui.month + 1, 1) - timedelta(days=1)
    
    # Si aucune date n'est fournie, utiliser les valeurs par défaut
    if not date_debut or date_debut == 'None':
        date_debut = premier_du_mois.strftime('%Y-%m-%d')
    
    if not date_fin or date_fin == 'None':
        date_fin = dernier_du_mois.strftime('%Y-%m-%d')
    
    # Récupérer l'objet Société
    societe_obj = None
    try:
        societe_obj = Societe.objects.filter(nom__iexact=societe_nom).first()
        if not societe_obj:
            societe_obj = Societe.objects.filter(nom__icontains=societe_nom).first()
    except Exception as e:
        print(f"Erreur recherche société '{societe_nom}': {e}")

    # CORRECTION CRITIQUE : Filtrer les COURSES d'abord, pas les affectations
    # Ne prendre que les courses avec statut 'validee'
    courses_query = Course.objects.filter(statut='validee')
    
    # Appliquer les filtres date sur les courses
    if date_debut and date_debut != 'None':
        try:
            courses_query = courses_query.filter(date_reelle__gte=date_debut)
        except Exception as e:
            print(f"Erreur filtre date_debut: {e}")
    
    if date_fin and date_fin != 'None':
        try:
            courses_query = courses_query.filter(date_reelle__lte=date_fin)
        except Exception as e:
            print(f"Erreur filtre date_fin: {e}")
    
    # Filtrer par type de chauffeur
    if type_chauffeur != 'tous':
        courses_query = courses_query.filter(chauffeur__type_chauffeur=type_chauffeur)
    
    # Récupérer les ID des courses filtrées
    courses_ids = courses_query.values_list('id', flat=True)
    
    # CORRECTION : Maintenant filtrer les affectations liées à ces courses
    affectations_query = Affectation.objects.filter(course_id__in=courses_ids)
    
    # CORRECTION : Filtrer manuellement par société
    affectations_filtrees = []
    for affectation in affectations_query.select_related('course', 'chauffeur', 'agent'):
        if affectation.agent.get_societe_display() == societe_nom:
            affectations_filtrees.append(affectation)
    
    affectations = affectations_filtrees
    
    # Charger le planning
    gestionnaire = GestionnaireTransport()
    planning_charge = False
    
    if request.session.get('planning_charge'):
        if gestionnaire.recharger_planning_depuis_session():
            planning_charge = True
            gestionnaire.dates_par_jour = request.session.get('gestionnaire_dates', {})
            
            temp_agents_path = os.path.join(settings.BASE_DIR, 'temp_agents.xlsx')
            if os.path.exists(temp_agents_path):
                gestionnaire.charger_agents(temp_agents_path)
            else:
                info_path = os.path.join(settings.BASE_DIR, 'info.xlsx')
                if os.path.exists(info_path):
                    gestionnaire.charger_agents(info_path)
    
    # **CORRECTION CRITIQUE ICI : Calcul du prix total AVEC LE VRAI PRIX DE LA COURSE**
    prix_total = 0
    affectations_avec_details = []
    courses_traitees = set()
    
    for affectation in affectations:
        course = affectation.course
        agent_nom = affectation.agent.nom
        
        # Récupérer le planning réel
        planning_reel = "Non disponible"
        if planning_charge and gestionnaire.df_planning is not None:
            for index, agent_row in gestionnaire.df_planning.iterrows():
                if pd.notna(agent_row['Salarie']) and str(agent_row['Salarie']).strip() == agent_nom:
                    jour_planning = affectation.jour
                    if jour_planning in agent_row:
                        planning_cell = agent_row[jour_planning]
                        if pd.notna(planning_cell):
                            planning_reel = str(planning_cell).strip()
                    break
        
        # **CORRECTION : UTILISER LE PRIX RÉEL DE LA COURSE, PAS LE PRIX PAR DÉFAUT DU CHAUFFEUR**
        prix_par_societe = 0
        if course and course.id not in courses_traitees:
            # Vérifier que la course est validée (double sécurité)
            if course.statut == 'validee':
                # **PRIORITÉ 1 : Utiliser le prix réel de la course (celui défini lors de l'affectation)**
                prix_course = course.prix_total if course.prix_total and course.prix_total > 0 else course.get_prix_course()
                
                # Compter le nombre de sociétés UNIQUES dans cette course
                societes_dans_course = set()
                for aff in course.affectation_set.all():
                    societe_nom_agent = aff.agent.get_societe_display()
                    if societe_nom_agent and societe_nom_agent != "Non spécifié":
                        societes_dans_course.add(societe_nom_agent)
                
                if societes_dans_course:
                    # Répartir le prix réel de la course entre les sociétés
                    prix_par_societe = prix_course / len(societes_dans_course)
                    prix_total += prix_par_societe
                
                courses_traitees.add(course.id)
        
        # Ajouter les détails
        affectation.planning_reel = planning_reel
        affectation.prix_par_societe = round(prix_par_societe, 3)
        affectations_avec_details.append(affectation)
    
    # Calculer les totaux
    total_courses = len(courses_traitees)
    total_affectations = len(affectations_avec_details)
    
    # Convertir "None" en None pour l'affichage
    date_debut_display = date_debut if date_debut != 'None' else None
    date_fin_display = date_fin if date_fin != 'None' else None
    
    context = {
        'societe_nom': societe_nom,
        'societe_obj': societe_obj,
        'affectations': affectations_avec_details,
        'total_courses': total_courses,
        'total_affectations': total_affectations,
        'prix_total': round(prix_total, 3),
        'date_debut': date_debut_display,
        'date_fin': date_fin_display,
        'type_chauffeur': type_chauffeur,
        # Dates par défaut pour le template
        'aujourd_hui_mois_debut': premier_du_mois.strftime('%Y-%m-%d'),
        'aujourd_hui_mois_fin': dernier_du_mois.strftime('%Y-%m-%d'),
        # Optionnel : ajouter la date d'aujourd'hui
        'aujourd_hui': aujourd_hui.strftime('%Y-%m-%d'),
    }
    return render(request, 'gestion/detail_societe_paie.html', context)

@login_required
def gestion_agents(request):
    "Page principale de gestion des agents"
    filtre = request.GET.get('filtre', 'tous')
    
    # Filtrer les agents selon le filtre sélectionné
    if filtre == 'complets':
        agents = Agent.objects.filter(
            ~Q(adresse__in=['Adresse à compléter', 'Adresse non renseignee', '']) &
            ~Q(telephone__in=['00000000', 'Telephone non renseigne', '']) &
            (Q(societe__isnull=False) | 
             (~Q(societe_texte__in=['', 'Société à compléter', 'Societe non renseignee']) & 
              Q(societe_texte__isnull=False)))
        ).order_by('nom')
    elif filtre == 'incomplets':
        agents = Agent.objects.filter(
            Q(adresse__in=['Adresse à compléter', 'Adresse non renseignee', '']) |
            Q(telephone__in=['00000000', 'Telephone non renseigne', '']) |
            (Q(societe__isnull=True) & 
             (Q(societe_texte__in=['', 'Société à compléter', 'Societe non renseignee']) | 
              Q(societe_texte__isnull=True)))
        ).order_by('nom')
    else:
        agents = Agent.objects.all().order_by('nom')
    
    # Statistiques
    total_agents = Agent.objects.count()
    
    # Agents complets (logique inverse des incomplets)
    agents_complets = Agent.objects.filter(
        ~Q(adresse__in=['Adresse à compléter', 'Adresse non renseignee', '']) &
        ~Q(telephone__in=['00000000', 'Telephone non renseigne', '']) &
        (Q(societe__isnull=False) | 
         (~Q(societe_texte__in=['', 'Société à compléter', 'Societe non renseignee']) & 
          Q(societe_texte__isnull=False)))
    ).count()
    
    agents_incomplets = total_agents - agents_complets
    
    # Ajouter la liste des sociétés au contexte
    societes_list = Societe.objects.all().order_by('nom')
    
    if request.method == 'POST':
        form = AgentForm(request.POST)
        if form.is_valid():
            agent = form.save(commit=False)
            
            # Gérer la société
            societe_select = form.cleaned_data.get('societe_select')
            societe_texte = form.cleaned_data.get('societe_texte')
            
            if societe_select:
                agent.societe = societe_select
                agent.societe_texte = None
            elif societe_texte:
                # Chercher si la société existe déjà
                societe_existante = Societe.objects.filter(nom__iexact=societe_texte).first()
                if societe_existante:
                    agent.societe = societe_existante
                    agent.societe_texte = None
                else:
                    agent.societe = None
                    agent.societe_texte = societe_texte
            else:
                agent.societe = None
                agent.societe_texte = None
            
            agent.save()
            messages.success(request, 'Agent ajouté avec succès')
            return redirect('agents')
        else:
            messages.error(request, 'Erreur dans le formulaire')
    else:
        form = AgentForm()
    
    context = {
        'agents': agents,
        'form': form,
        'societes_list': societes_list,
        'filtre_actuel': filtre,
        'total_agents': total_agents,
        'agents_complets': agents_complets,
        'agents_incomplets': agents_incomplets,
    }
    return render(request, 'gestion/agents.html', context)

@login_required
def modifier_agent(request, id):
  
    agent = get_object_or_404(Agent, id=id)
    
    # Charger la liste des sociétés pour le template
    societes_list = Societe.objects.all().order_by('nom')
    
    if request.method == 'POST':
        form = AgentModificationForm(request.POST, instance=agent)
        if form.is_valid():
            agent = form.save(commit=False)
            
            # Gérer la société
            societe_select = form.cleaned_data.get('societe_select')
            societe_texte = form.cleaned_data.get('societe_texte')
            
            if societe_select:
                agent.societe = societe_select
                agent.societe_texte = None
            elif societe_texte:
                # Chercher si la société existe déjà
                societe_existante = Societe.objects.filter(nom__iexact=societe_texte).first()
                if societe_existante:
                    agent.societe = societe_existante
                    agent.societe_texte = None
                else:
                    agent.societe = None
                    agent.societe_texte = societe_texte
            else:
                agent.societe = None
                agent.societe_texte = None
            
            agent.save()
            messages.success(request, f'Agent {agent.nom} modifié avec succès')
            return redirect('agents')
        else:
            messages.error(request, 'Erreur dans le formulaire')
    else:
        form = AgentModificationForm(instance=agent)
    
    context = {
        'form': form,
        'agent': agent,
        'societes_list': societes_list,  # AJOUTÉ
    }
    return render(request, 'gestion/modifier_agent.html', context)
@login_required
def supprimer_agent(request, id):
    "Supprimer un agent"
    agent = get_object_or_404(Agent, id=id)
    nom_agent = agent.nom
    agent.delete()
    messages.success(request, f'Agent {nom_agent} supprimé avec succès')
    return redirect('agents')

@login_required
def detail_agent(request, id):
    "Page de détail d'un agent avec ses affectations"
    agent = get_object_or_404(Agent, id=id)
    affectations = Affectation.objects.filter(agent=agent).select_related('chauffeur', 'course').order_by('-date_reelle', 'heure')
    
    context = {
        'agent': agent,
        'affectations': affectations
    }
    return render(request, 'gestion/detail_agent.html', context)

@login_required
def importer_agents(request):
    "Page d'importation d'agents depuis Excel"
    if request.method == 'POST':
        form = ImportAgentForm(request.POST, request.FILES)
        if form.is_valid():
            fichier = request.FILES['fichier_excel']
            try:
                df = pd.read_excel(fichier)
                agents_crees = 0
                agents_modifies = 0
                erreurs = []
                
                for index, row in df.iterrows():
                    nom = row.get('voyant', '')
                    if nom:
                        try:
                            # Vérifier si l'agent existe déjà
                            agent, created = Agent.objects.get_or_create(
                                nom=nom,
                                defaults={
                                    'adresse': row.get('adresse', ''),
                                    'telephone': str(row.get('Mobile', '')),
                                    'societe_texte': row.get('societe', ''),
                                    'voiture_personnelle': row.get('voiture', '').lower() in ['oui', 'yes', 'true', '1'],
                                }
                            )
                            
                            if created:
                                agents_crees += 1
                            else:
                                # Mettre à jour l'agent existant
                                agent.adresse = row.get('adresse', agent.adresse)
                                agent.telephone = str(row.get('Mobile', agent.telephone))
                                agent.societe_texte = row.get('societe', agent.societe_texte)
                                agent.voiture_personnelle = row.get('voiture', '').lower() in ['oui', 'yes', 'true', '1']
                                agent.save()
                                agents_modifies += 1
                                
                        except Exception as e:
                            erreurs.append(f"Ligne {index + 2}: {str(e)}")
                
                if erreurs:
                    messages.warning(request, f"{agents_crees} créés, {agents_modifies} modifiés, mais {len(erreurs)} erreurs")
                    for erreur in erreurs[:5]:  # Afficher seulement les 5 premières erreurs
                        messages.error(request, erreur)
                else:
                    messages.success(request, f"{agents_crees} agents créés, {agents_modifies} agents modifiés avec succès!")
                
                return redirect('agents')
                    
            except Exception as e:
                messages.error(request, f"Erreur lors de l'import: {str(e)}")
    
    else:
        form = ImportAgentForm()
    
    context = {
        'form': form
    }
    return render(request, 'gestion/importer_agents.html', context)

@login_required
def gestion_societes(request):
    "Page principale de gestion des sociétés"
    societes = Societe.objects.all().order_by('nom')
    
    # Statistiques
    total_societes = societes.count()
    societes_avec_matricule = societes.filter(matricule_fiscale__isnull=False).exclude(matricule_fiscale='').count()
    
    if request.method == 'POST':
        form = SocieteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Société ajoutée avec succès')
            return redirect('societes')
        else:
            messages.error(request, 'Erreur dans le formulaire')
    else:
        form = SocieteForm()
    
    context = {
        'societes': societes,
        'form': form,
        'total_societes': total_societes,
        'societes_avec_matricule': societes_avec_matricule,
    }
    return render(request, 'gestion/societes.html', context)

@login_required
def modifier_societe(request, id):
    "Page de modification d'une société spécifique"
    societe = get_object_or_404(Societe, id=id)
    
    if request.method == 'POST':
        form = SocieteModificationForm(request.POST, instance=societe)
        if form.is_valid():
            form.save()
            messages.success(request, f'Société {societe.nom} modifiée avec succès')
            return redirect('societes')
        else:
            messages.error(request, 'Erreur dans le formulaire')
    else:
        form = SocieteModificationForm(instance=societe)
    
    # Compter les agents de cette société
    agents_count = societe.agent_set.count()
    affectations_count = Affectation.objects.filter(agent__societe=societe).count()
    
    context = {
        'form': form,
        'societe': societe,
        'agents_count': agents_count,
        'affectations_count': affectations_count,
    }
    return render(request, 'gestion/modifier_societe.html', context)
@login_required
def get_agents_du_planning(request):
   
    jour = request.GET.get('jour', '')
    type_transport = request.GET.get('type_transport', '')
    heure = request.GET.get('heure', '')
    
    if not jour or not type_transport or not heure:
        return JsonResponse({'agents': []})
    
    try:
        # Utiliser le MÊME gestionnaire que dans liste_transports
        gestionnaire = GestionnaireTransport()
        if not gestionnaire.recharger_planning_depuis_session():
            return JsonResponse({'agents': []})
        
        gestionnaire.dates_par_jour = request.session.get('gestionnaire_dates', {})
        
        # Charger les agents
        temp_agents_path = os.path.join(settings.BASE_DIR, 'temp_agents.xlsx')
        if os.path.exists(temp_agents_path):
            gestionnaire.charger_agents(temp_agents_path)
        else:
            info_path = os.path.join(settings.BASE_DIR, 'info.xlsx')
            if os.path.exists(info_path):
                gestionnaire.charger_agents(info_path)
        
        # Créer un faux formulaire de filtre
        class FiltreFormPlanning:
            def __init__(self, jour, type_transport, heure):
                self.cleaned_data = {
                    'jour': jour,
                    'type_transport': type_transport,
                    'heure_ete': False,
                    'filtre_agents': 'tous'
                }
        
        form_filtre = FiltreFormPlanning(jour, type_transport, heure)
        
        # Obtenir la liste des transports
        liste_transports = gestionnaire.traiter_donnees(form_filtre)
        
        # Filtrer pour l'heure spécifique
        agents_heure_specifique = []
        for transport in liste_transports:
            if transport['heure'] == int(heure):
                agents_heure_specifique.append(transport['agent'])
        
        # Retourner les noms d'agents uniques
        agents_uniques = list(set(agents_heure_specifique))
        
        return JsonResponse({'agents': agents_uniques})
        
    except Exception as e:
        print(f"❌ Erreur get_agents_du_planning: {str(e)}")
        return JsonResponse({'agents': []})
@login_required
def supprimer_societe(request, id):
    "Supprimer une société"
    societe = get_object_or_404(Societe, id=id)
    nom_societe = societe.nom
    
    # Vérifier s'il y a des agents associés
    agents_count = societe.agent_set.count()
    if agents_count > 0:
        messages.error(request, f'Impossible de supprimer {nom_societe} : {agents_count} agent(s) y sont associés')
        return redirect('societes')
    
    societe.delete()
    messages.success(request, f'Société {nom_societe} supprimée avec succès')
    return redirect('societes')
@login_required
def api_ajouter_societe_rapide(request):
    
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            nom = data.get('nom', '').strip()
            
            if not nom:
                return JsonResponse({'success': False, 'error': 'Le nom de la société est requis'})
            
            # Vérifier si la société existe déjà
            societe_existante = Societe.objects.filter(nom__iexact=nom).first()
            if societe_existante:
                return JsonResponse({
                    'success': True, 
                    'societe_id': societe_existante.id,
                    'message': 'Société déjà existante'
                })
            
            # Créer la nouvelle société
            nouvelle_societe = Societe.objects.create(
                nom=nom,
                matricule_fiscale='',
                adresse='',
                telephone='',
                email=''
            )
            
            return JsonResponse({
                'success': True, 
                'societe_id': nouvelle_societe.id,
                'societe_nom': nouvelle_societe.nom,
                'message': 'Société créée avec succès'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
@login_required
def detail_societe(request, id):
    "Page de détail d'une société avec ses agents"
    societe = get_object_or_404(Societe, id=id)
    agents = Agent.objects.filter(societe=societe).order_by('nom')
    affectations = Affectation.objects.filter(agent__societe=societe).select_related('agent', 'chauffeur', 'course').order_by('-date_reelle', 'heure')
    
    # Statistiques
    total_agents = agents.count()
    total_affectations = affectations.count()
    
    # Calcul du coût total des transports
    cout_total = 0
    for affectation in affectations:
        if affectation.course:
            cout_total += affectation.course.get_prix_par_societe()
    
    context = {
        'societe': societe,
        'agents': agents,
        'affectations': affectations,
        'total_agents': total_agents,
        'total_affectations': total_affectations,
        'cout_total': cout_total,
    }
    return render(request, 'gestion/detail_societe.html', context)
def is_admin(user):
    return user.is_authenticated and user.is_staff
@login_required
def demander_validation_course(request, course_id):
   
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            notes = data.get('notes', '')
            
            course = get_object_or_404(Course, id=course_id)
            
            # Vérifier que l'utilisateur a le droit de demander la validation
            # (par exemple, le chauffeur qui a créé la course)
            
            if course.demander_validation(notes):
                return JsonResponse({'success': True, 'message': 'Demande de validation envoyée'})
            else:
                return JsonResponse({'success': False, 'error': 'Impossible de demander la validation'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@login_required
def get_course_details(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    return JsonResponse({
        'success': True,
        'course': {
            'id': course.id,
            'chauffeur_id': course.chauffeur.id,
            'chauffeur_nom': course.chauffeur.nom,
            'heure': course.heure,
            'type_transport': course.type_transport,
            'jour': course.jour,
            'date_reelle': course.date_reelle.strftime('%Y-%m-%d'),
            'statut': course.statut,
            'notes': course.notes_validation or '',
            'prix_total': float(course.prix_total) if course.prix_total else 0.0,
            'prix': float(course.prix_total) if course.prix_total else float(course.get_prix_course()),
            'validee': course.est_validee(),
            'validee_at': course.validee_at.strftime('%d/%m/%Y %H:%M') if course.validee_at else None,
            'validee_par': course.validee_par.username if course.validee_par else None
        }
    })
@login_required
def modifier_course(request, course_id):
   
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            
            course = get_object_or_404(Course, id=course_id)
            
            # Vérifier les permissions
            
            # Mettre à jour les champs modifiables
            if 'chauffeur_id' in data:
                try:
                    chauffeur = Chauffeur.objects.get(id=data['chauffeur_id'])
                    course.chauffeur = chauffeur
                except Chauffeur.DoesNotExist:
                    pass
            
            if 'heure' in data:
                try:
                    course.heure = int(data['heure'])
                except (ValueError, TypeError):
                    pass
            
            if 'type_transport' in data and data['type_transport'] in ['ramassage', 'depart']:
                course.type_transport = data['type_transport']
            
            if 'jour' in data:
                course.jour = data['jour']
            
            if 'date_reelle' in data:
                try:
                    course.date_reelle = datetime.strptime(data['date_reelle'], '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass
            
            # CORRECTION CRITIQUE : Mettre à jour le prix
            if 'prix' in data and data['prix']:
                try:
                    prix_total = float(data['prix'])
                    if prix_total > 0:
                        course.prix_total = prix_total
                        print(f"💰 Prix mis à jour: {prix_total} TND")
                except (ValueError, TypeError) as e:
                    print(f"Erreur conversion prix: {e}")
            
            if 'notes' in data:
                course.notes_validation = data['notes']
            
            course.save()
            
            # Mettre à jour aussi les affectations liées
            for affectation in course.affectation_set.all():
                affectation.prix_course = course.prix_total if course.prix_total > 0 else course.get_prix_course()
                affectation.save()
            
            return JsonResponse({'success': True, 'message': 'Course modifiée avec succès'})
            
        except Exception as e:
            print(f"❌ Erreur modification course: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
@login_required
@user_passes_test(is_admin)
def courses_en_attente_validation(request):
    
    courses = Course.objects.filter(
        statut='demande_validation'
    ).order_by('-demande_validation_at', 'date_reelle')
    
    context = {
        'courses': courses,
        'page_title': 'Courses en attente de validation'
    }
    
    return render(request, 'gestion/courses_validation.html', context)
