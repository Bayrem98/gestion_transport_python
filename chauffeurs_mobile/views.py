# Vues API pour l'interface mobile
# VERSION COMPLÈTE AVEC TOUTES LES FONCTIONS

import json
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q

try:
    # Essayer d'importer depuis votre structure d'app
    from django.apps import apps
    
    # Récupérer les modèles de manière dynamique
    Chauffeur = apps.get_model('gestion', 'Chauffeur')
    Course = apps.get_model('gestion', 'Course')
    Agent = apps.get_model('gestion', 'Agent')
    Affectation = apps.get_model('gestion', 'Affectation')
    
    MODELS_IMPORTED = True
    print("✅ Modèles importés via apps.get_model()")
except Exception as e:
    print(f"❌ Erreur import modèles: {e}")
    MODELS_IMPORTED = False
    
    # Classes fallback pour éviter les crashs
    class Chauffeur:
        objects = type('Manager', (), {
            'get': lambda self, **kwargs: None,
            'filter': lambda self, **kwargs: type('QuerySet', (), {
                'first': lambda self: None,
                'all': lambda self: [],
                'count': lambda self: 0
            })()
        })()

# ============================================
# VUES D'INTERFACE WEB
# ============================================

def mobile_login_view(request):
    """Page de connexion"""
    return render(request, 'chauffeurs_mobile/login.html')

def mobile_dashboard_view(request):
    """Page dashboard"""
    return render(request, 'chauffeurs_mobile/dashboard.html')

def mobile_selection_view(request):
    """Page sélection agents"""
    return render(request, 'chauffeurs_mobile/selection.html')

def mobile_reservation_view(request):
    """Page web pour les réservations J+1"""
    return render(request, 'chauffeurs_mobile/reservation.html')

def mobile_historique_view(request):
    """Page historique"""
    return render(request, 'chauffeurs_mobile/historique.html')

def mobile_profile_view(request):
    """Page profil"""
    return render(request, 'chauffeurs_mobile/profile.html')

def mobile_super_dashboard_view(request):
    """Page Super Dashboard"""
    return render(request, 'chauffeurs_mobile/super_dashboard.html')

def mobile_super_chauffeur_detail_view(request, chauffeur_id):
    """Page web pour voir le détail d'un chauffeur"""
    return render(request, 'chauffeurs_mobile/super_chauffeur_detail.html')


def force_logout_all_devices(chauffeur_id):
    """Force la déconnexion de tous les appareils d'un chauffeur"""
    try:
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        
        deleted_count = 0
        for session in Session.objects.filter(expire_date__gt=timezone.now()):
            session_data = session.get_decoded()
            if session_data.get('chauffeur_id') == chauffeur_id:
                session.delete()
                deleted_count += 1
        
        print(f"🚪 Déconnexion forcée: {deleted_count} session(s) fermée(s) pour chauffeur {chauffeur_id}")
        return deleted_count
        
    except Exception as e:
        print(f"⚠️ Erreur déconnexion forcée: {e}")
        return 0
def force_logout_chauffeur(chauffeur_id, current_session_key=None):
    """
    Force la déconnexion de tous les appareils d'un chauffeur
    Retourne le nombre de sessions supprimées
    """
    try:
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        
        deleted_count = 0
        
        # Récupérer toutes les sessions non expirées
        sessions = Session.objects.filter(expire_date__gt=timezone.now())
        
        for session in sessions:
            try:
                session_data = session.get_decoded()
                
                # Vérifier si c'est la session du chauffeur
                if session_data.get('chauffeur_id') == chauffeur_id:
                    
                    # Éviter de supprimer la session courante si spécifiée
                    if current_session_key and session.session_key == current_session_key:
                        print(f"  ⏭️ Session courante conservée: {session.session_key[:10]}...")
                        continue
                    
                    # Supprimer la session
                    session.delete()
                    deleted_count += 1
                    print(f"  🚪 Session supprimée: {session.session_key[:10]}...")
                    
            except Exception as e:
                print(f"  ⚠️ Erreur session {session.session_key[:10]}: {e}")
                continue
        
        print(f"✅ {deleted_count} session(s) supprimée(s) pour chauffeur {chauffeur_id}")
        return deleted_count
        
    except Exception as e:
        print(f"❌ Erreur déconnexion forcée: {e}")
        import traceback
        traceback.print_exc()
        return 0
# ============================================
# API ENDPOINTS
# ============================================
@csrf_exempt
@require_GET
def api_export_historique(request):
    """API pour exporter l'historique en CSV"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        # Récupérer toutes les courses du chauffeur
        courses = Course.objects.filter(chauffeur_id=chauffeur_id).order_by('-date_reelle', '-heure')
        
        # Créer la réponse CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="historique_courses_{datetime.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response, delimiter=';')
        
        # En-têtes
        writer.writerow(['Date', 'Heure', 'Type', 'Statut', 'Nb Agents', 'Prix (€)', 'Notes'])
        
        # Données
        for course in courses:
            nb_agents = Affectation.objects.filter(course=course).count()
            prix = course.get_prix_course() if hasattr(course, 'get_prix_course') else 0
            
            writer.writerow([
                course.date_reelle.strftime('%d/%m/%Y'),
                f"{course.heure}h",
                'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                course.get_statut_display(),
                nb_agents,
                f"{float(prix):.2f}",
                course.notes_validation or ''
            ])
        
        return response
        
    except Exception as e:
        print(f"❌ Erreur export: {e}")
        return JsonResponse({'success': False, 'error': str(e)})
@csrf_exempt
@require_GET
def api_profile(request):
    """API pour récupérer les données du profil - VERSION CORRIGÉE"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        # Récupérer les modèles
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        Course = apps.get_model('gestion', 'Course')
        
        # Récupérer le chauffeur
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        
        print(f"👤 Profil demandé pour: {chauffeur.nom} (ID: {chauffeur_id})")
        
        # ========== VÉRIFICATION DES CHAMPS ==========
        print("🔍 Vérification des champs:")
        
        # Liste de tous les champs possibles
        champs_possibles = [
            'nom', 'telephone', 'numero_voiture', 'type_chauffeur',
            'actif', 'adresse', 'email', 'societe', 'numero_identite',
            'prix_course_par_defaut', 'statut', 'created_at'
        ]
        
        profile_data = {}
        
        for champ in champs_possibles:
            if hasattr(chauffeur, champ):
                valeur = getattr(chauffeur, champ)
                # Convertir les valeurs spéciales
                if champ == 'created_at' and valeur:
                    valeur = valeur.strftime('%d/%m/%Y')
                profile_data[champ] = valeur
                print(f"  ✅ {champ}: {valeur}")
            else:
                profile_data[champ] = ''
                print(f"  ⚠️ {champ}: NON DISPONIBLE")
        
        # Alias pour compatibilité
        profile_data['vehicule'] = profile_data.get('numero_voiture', '')
        # ============================================
        
        # Statistiques
        total_courses = Course.objects.filter(chauffeur_id=chauffeur_id).count()
        courses_validees = Course.objects.filter(chauffeur_id=chauffeur_id, statut='validee').count()
        
        # Calcul du revenu total
        courses = Course.objects.filter(chauffeur_id=chauffeur_id, statut='validee')
        revenu_total = 0
        for course in courses:
            try:
                if hasattr(course, 'prix_total') and course.prix_total:
                    prix = float(course.prix_total)
                elif hasattr(course, 'get_prix_course'):
                    prix = float(course.get_prix_course() or 0)
                else:
                    prix = 0
                revenu_total += prix
            except (ValueError, TypeError):
                continue
        
        return JsonResponse({
            'success': True,
            'profile': profile_data,
            'stats': {
                'total_courses': total_courses,
                'courses_validees': courses_validees,
                'revenu_total': round(revenu_total, 2),
                'moyenne_mensuelle': round(revenu_total / 12, 2) if revenu_total > 0 else 0,
            }
        })
        
    except Exception as e:
        print(f"❌ Erreur profil: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_POST
def api_profile_update(request):
    """API pour mettre à jour le profil - VERSION COMPLÈTE"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        data = json.loads(request.body)
        print(f"📝 Mise à jour profil pour chauffeur {chauffeur_id}")
        print(f"📦 Données reçues: {data}")
        
        # Récupérer le chauffeur
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        
        print(f"✅ Chauffeur trouvé: {chauffeur.nom}")
        
        # ========== TOUS LES CHAMPS POSSIBLES ==========
        # Mapping: champ_interface -> champ_modele
        champs_mapping = {
            'nom': 'nom',
            'telephone': 'telephone',
            'vehicule': 'numero_voiture',  # 'vehicule' dans l'interface = 'numero_voiture' en DB
            'adresse': 'adresse',
            'email': 'email',
            'societe': 'societe'
        }
        
        modifications = []
        
        for champ_interface, champ_modele in champs_mapping.items():
            if champ_interface in data and data[champ_interface] is not None:
                nouvelle_valeur = str(data[champ_interface]).strip()
                
                # Vérifier si le champ existe dans le modèle
                if hasattr(chauffeur, champ_modele):
                    ancienne_valeur = getattr(chauffeur, champ_modele, '') or ''
                    
                    if nouvelle_valeur != ancienne_valeur:
                        setattr(chauffeur, champ_modele, nouvelle_valeur)
                        modifications.append(champ_interface)
                        print(f"✅ {champ_interface} ({champ_modele}): '{ancienne_valeur}' -> '{nouvelle_valeur}'")
                else:
                    print(f"⚠️ Champ {champ_modele} n'existe pas dans le modèle")
        
        # Sauvegarder si modifications
        if modifications:
            chauffeur.save()
            print(f"💾 Profil sauvegardé: {len(modifications)} modification(s)")
            
            # Mettre à jour la session
            if 'nom' in modifications:
                request.session['chauffeur_nom'] = chauffeur.nom
                request.session.save()
            
            # Préparer réponse
            response_data = {
                'success': True,
                'message': f'Profil mis à jour ({len(modifications)} modification(s))',
                'modifications': modifications,
            }
            
            # Ajouter les données mises à jour
            updated_profile = {}
            for champ_interface, champ_modele in champs_mapping.items():
                if hasattr(chauffeur, champ_modele):
                    updated_profile[champ_interface] = getattr(chauffeur, champ_modele, '')
            
            response_data['profile'] = updated_profile
            
            return JsonResponse(response_data)
        else:
            return JsonResponse({
                'success': True,
                'message': 'Aucune modification nécessaire',
                'modifications': []
            })
        
    except Exception as e:
        print(f"❌ Erreur mise à jour profil: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Erreur serveur: {str(e)}'
        }, status=500)
@csrf_exempt
@require_POST
def api_change_password(request):
    """API pour changer le mot de passe du chauffeur - VERSION CORRIGÉE"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        data = json.loads(request.body)
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        print(f"🔐 API changement mot de passe pour chauffeur {chauffeur_id}")
        print(f"📦 Données reçues: current='{current_password}', new='{new_password}', confirm='{confirm_password}'")
        
        # Validation des données
        if not current_password or not new_password or not confirm_password:
            return JsonResponse({
                'success': False,
                'error': 'Tous les champs sont requis'
            })
        
        if new_password != confirm_password:
            return JsonResponse({
                'success': False,
                'error': 'Les nouveaux mots de passe ne correspondent pas'
            })
        
        # Validation renforcée
        if len(new_password) < 8:
            return JsonResponse({
                'success': False, 
                'error': 'Le mot de passe doit faire au moins 8 caractères'
            })
        
        if not any(char.isdigit() for char in new_password):
            return JsonResponse({
                'success': False,
                'error': 'Le mot de passe doit contenir au moins un chiffre (0-9)'
            })
        
        if not any(char.isalpha() for char in new_password):
            return JsonResponse({
                'success': False,
                'error': 'Le mot de passe doit contenir au moins une lettre'
            })
        
        # Récupérer le chauffeur
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        
        try:
            chauffeur = Chauffeur.objects.get(id=chauffeur_id)
            print(f"✅ Chauffeur trouvé: {chauffeur.nom} (ID: {chauffeur.id})")
        except Chauffeur.DoesNotExist:
            print(f"❌ Chauffeur {chauffeur_id} non trouvé")
            return JsonResponse({
                'success': False,
                'error': 'Chauffeur non trouvé'
            }, status=404)
        
        # ========== VÉRIFICATION MOT DE PASSE ACTUEL ==========
        import hashlib
        current_hash = hashlib.sha256(current_password.encode()).hexdigest()
        
        print(f"🔑 Hash actuel calculé: {current_hash}")
        print(f"🔑 Hash stocké en DB: {chauffeur.mobile_password}")
        
        # Si pas de mot de passe défini (première fois)
        if not chauffeur.mobile_password:
            print(f"⚠️ Premier mot de passe pour {chauffeur.nom}")
            # On accepte n'importe quel mot de passe actuel pour la première configuration
            pass  # Continuer
        elif chauffeur.mobile_password != current_hash:
            print(f"❌ Hash ne correspond pas!")
            return JsonResponse({
                'success': False,
                'error': 'Mot de passe actuel incorrect'
            })
        # ======================================================
        
        # Vérifier que le nouveau est différent de l'ancien
        new_hash = hashlib.sha256(new_password.encode()).hexdigest()
        
        if chauffeur.mobile_password == new_hash:
            return JsonResponse({
                'success': False,
                'error': "Le nouveau mot de passe doit être différent de l'ancien"
            })
        
        # ========== CHANGEMENT DE MOT DE PASSE ==========
        print(f"💾 Sauvegarde nouveau mot de passe...")
        chauffeur.mobile_password = new_hash
        chauffeur.save()  # ICI, la méthode save() de votre modèle sera appelée
        print(f"✅ Mot de passe changé avec succès pour {chauffeur.nom}")
        # ===============================================
        
        # ========== DÉCONNEXION FORCÉE ==========
        print(f"🚪 Déconnexion forcée en cours...")
        
        # 1. Flusher la session courante IMMÉDIATEMENT
        request.session.flush()
        print("🧹 Session courante flushée")
        
        # 2. Supprimer TOUTES les sessions de la base de données
        try:
            from django.contrib.sessions.models import Session
            from django.utils import timezone
            
            sessions_deleted = 0
            active_sessions = Session.objects.filter(expire_date__gt=timezone.now())
            
            for session in active_sessions:
                try:
                    session_data = session.get_decoded()
                    if session_data.get('chauffeur_id') == chauffeur_id:
                        session.delete()
                        sessions_deleted += 1
                except Exception as e:
                    print(f"  ⚠️ Erreur session: {e}")
                    continue
            
            print(f"🗑️  {sessions_deleted} session(s) supprimée(s) de la DB")
            
        except Exception as e:
            print(f"⚠️ Erreur suppression sessions DB: {e}")
        # ========================================
        
        return JsonResponse({
            'success': True,
            'message': 'Mot de passe changé avec succès. Vous avez été déconnecté.',
            'redirect_to_login': True,
            'logout_forced': True
        })
        
    except Exception as e:
        print(f"❌ ERREUR FATALE dans api_change_password: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Erreur serveur: {str(e)}'
        }, status=500)
@csrf_exempt
@require_POST
def api_login(request):
    """Connexion avec vérification du mot de passe"""
    try:
        data = json.loads(request.body)
        telephone = data.get('telephone', '').strip()
        password = data.get('password', '')
        
        if not telephone or not password:
            return JsonResponse({
                'success': False,
                'message': 'Téléphone et mot de passe requis'
            })
        
        # Récupérer le modèle Chauffeur
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        
        # Chercher le chauffeur
        chauffeur = Chauffeur.objects.filter(
            telephone=telephone,
            actif=True
        ).first()
        
        if not chauffeur:
            return JsonResponse({
                'success': False,
                'message': 'Chauffeur non trouvé ou inactif'
            })
        
        # Vérifier le mot de passe
        if hasattr(chauffeur, 'mobile_password'):
            if chauffeur.mobile_password:
                import hashlib
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                
                if chauffeur.mobile_password != password_hash:
                    return JsonResponse({
                        'success': False,
                        'message': 'Mot de passe incorrect'
                    })
        
        # Authentification réussie
        request.session['chauffeur_id'] = chauffeur.id
        request.session['chauffeur_nom'] = chauffeur.nom
        request.session['telephone'] = telephone
        request.session.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Connecté avec succès',
            'chauffeur': {
                'id': chauffeur.id,
                'nom': chauffeur.nom,
                'telephone': chauffeur.telephone,
                'type_chauffeur': getattr(chauffeur, 'type_chauffeur', 'taxi'),
                'vehicule': getattr(chauffeur, 'numero_voiture', 'Non spécifié')
            }
        })
            
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        })

# API de déconnexion
@csrf_exempt
@require_POST
def api_logout(request):
    """API de déconnexion"""
    request.session.flush()
    return JsonResponse({'success': True, 'message': 'Déconnecté'})

# API dashboard
@csrf_exempt
@require_GET
def api_dashboard(request):
    """API dashboard - Courses d'aujourd'hui seulement"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({
            'success': False,
            'message': 'Session expirée',
            'redirect': '/mobile/login/'
        }, status=401)
    
    try:
        # Récupérer les modèles
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        # Récupérer le chauffeur
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        is_super_chauffeur = getattr(chauffeur, 'super_chauffeur', False)        
        # Date d'aujourd'hui
        aujourd_hui = timezone.now().date()
        
        print(f"📊 Dashboard pour chauffeur {chauffeur_id} - Date: {aujourd_hui}")
        
        # 1. Courses d'aujourd'hui (tous statuts)
        courses_aujourdhui = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            date_reelle=aujourd_hui
        ).order_by('heure')
        
        print(f"📅 Courses aujourd'hui: {courses_aujourdhui.count()}")
        
        # 2. Courses VALIDÉES (toutes dates)
        courses_validees = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            statut__in=['validee', 'payee']
        )
        
        print(f"✅ Courses validées: {courses_validees.count()}")
        
        # 3. Courses EN ATTENTE (aujourd'hui)
        courses_attente = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            date_reelle=aujourd_hui,
            statut='en_attente'
        )
        
        print(f"⏳ Courses en attente: {courses_attente.count()}")
        
        # 4. Courses ANNULÉES (aujourd'hui)
        courses_annulees = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            date_reelle=aujourd_hui,
            statut='annulee'
        )
        
        print(f"❌ Courses annulées: {courses_annulees.count()}")
        
        # 5. Calculer le revenu des courses validées
        revenu_total = 0
        for course in courses_validees:
            try:
                # Essayer différentes façons de récupérer le prix
                if hasattr(course, 'prix_total') and course.prix_total:
                    prix = float(course.prix_total)
                elif hasattr(course, 'get_prix_course'):
                    prix = float(course.get_prix_course() or 0)
                elif hasattr(course, 'prix_course') and course.prix_course:
                    prix = float(course.prix_course)
                else:
                    prix = 0
                
                revenu_total += prix
                print(f"💰 Course {course.id} - Prix: {prix} €")
            except (ValueError, TypeError, AttributeError) as e:
                print(f"⚠️ Erreur prix course {course.id}: {e}")
                continue
        
        print(f"💰 Revenu total validé: {revenu_total} €")
        
        # 6. Préparer les données du dashboard
        courses_data = []
        for course in courses_aujourdhui:
            nb_agents = Affectation.objects.filter(course=course).count()
            
            # Déterminer le texte du statut
            statut_display = course.statut
            if hasattr(course, 'get_statut_display'):
                statut_display = course.get_statut_display()
            
            courses_data.append({
                'id': course.id,
                'type': course.type_transport,
                'type_display': 'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                'heure': course.heure,
                'heure_display': f"{course.heure:02d}:00",
                'nb_agents': nb_agents,
                'statut': course.statut,
                'statut_display': statut_display,
                'date': course.date_reelle.strftime('%d/%m/%Y'),
                'prix': float(course.get_prix_course() or 0) if hasattr(course, 'get_prix_course') else 0,
            })
        
        # 7. Construire la réponse
        response_data = {
            'success': True,
            'chauffeur': {
                'id': chauffeur.id,
                'nom': chauffeur.nom,
                'telephone': chauffeur.telephone,
                'vehicule': getattr(chauffeur, 'numero_voiture', 'Non spécifié'),
                'type_chauffeur': getattr(chauffeur, 'type_chauffeur', 'taxi'),
                'actif': chauffeur.actif,
                'super_chauffeur': getattr(chauffeur, 'super_chauffeur', False),  # <-- AJOUTEZ CETTE LIGNE
            },            'dashboard': {
                'date': aujourd_hui.strftime('%d/%m/%Y'),
                'heure_actuelle': timezone.now().strftime('%H:%M'),
                'stats': {
                    'total_courses': courses_aujourdhui.count(),
                    'courses_validees': courses_validees.count(),
                    'courses_attente': courses_attente.count(),
                    'courses_annulees': courses_annulees.count(),
                    'revenu_valide': round(revenu_total, 2),
                    'revenu_valide_display': f"{round(revenu_total, 2):.2f} €",
                },
                'courses_aujourdhui': courses_data
            }
        }
        
        # Debug: afficher la réponse
        print(f"📤 Réponse dashboard: {json.dumps(response_data, indent=2, default=str)}")
        
        return JsonResponse(response_data)
        
    except Chauffeur.DoesNotExist:
        print(f"❌ Chauffeur {chauffeur_id} non trouvé")
        return JsonResponse({
            'success': False,
            'message': 'Chauffeur non trouvé'
        }, status=404)
        
    except Exception as e:
        print(f"❌ ERREUR api_dashboard: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': f'Erreur serveur: {str(e)}'
        }, status=500)
@csrf_exempt
@require_GET
def api_reservations_demain(request):
    """API pour voir les réservations de demain"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        from datetime import date, timedelta
        
        print(f"📅 API réservations demain appelée pour chauffeur {chauffeur_id}")
        
        # Récupérer les modèles AVEC GESTION D'ERREUR
        try:
            from django.apps import apps
            Chauffeur = apps.get_model('gestion', 'Chauffeur')
            Reservation = apps.get_model('gestion', 'Reservation')
            HeureTransport = apps.get_model('gestion', 'HeureTransport')
            print("✅ Modèles importés avec succès")
        except Exception as e:
            print(f"❌ Erreur import modèles: {e}")
            # Fallback : utiliser des imports directs
            try:
                from gestion.models import Chauffeur, Reservation, HeureTransport
                print("✅ Modèles importés directement")
            except Exception as e2:
                print(f"❌ Erreur import direct: {e2}")
                return JsonResponse({
                    'success': False, 
                    'error': f'Erreur import modèles: {e2}',
                    'details': 'Vérifiez que les modèles existent dans gestion/models.py'
                })
        
        demain = date.today() + timedelta(days=1)
        print(f"📅 Date de demain: {demain}")
        
        # Récupérer le chauffeur
        try:
            chauffeur = Chauffeur.objects.get(id=chauffeur_id)
            print(f"👤 Chauffeur trouvé: {chauffeur.nom}")
        except Chauffeur.DoesNotExist:
            print(f"❌ Chauffeur {chauffeur_id} non trouvé")
            return JsonResponse({
                'success': False,
                'error': 'Chauffeur non trouvé'
            })
        
        # Récupérer les réservations existantes pour demain
        reservations_demain = Reservation.objects.filter(
            date_reservation=demain
        ).select_related('agent', 'heure_transport')
        
        print(f"📋 {reservations_demain.count()} réservation(s) trouvée(s) pour demain")
        
        # Récupérer les heures dynamiques configurées
        heures_ramassage = HeureTransport.objects.filter(
            type_transport='ramassage',
            active=True
        ).order_by('ordre')
        
        heures_depart = HeureTransport.objects.filter(
            type_transport='depart', 
            active=True
        ).order_by('ordre')
        
        print(f"⏰ {heures_ramassage.count()} heure(s) ramassage, {heures_depart.count()} heure(s) départ")
        
        # Préparer la réponse
        response_data = {
            'success': True,
            'date_demain': demain.strftime('%Y-%m-%d'),
            'date_demain_display': demain.strftime('%d/%m/%Y'),
            'chauffeur': {
                'id': chauffeur.id,
                'nom': chauffeur.nom,
            },
            'heures_ramassage': [
                {'id': h.id, 'heure': h.heure, 'libelle': h.libelle}
                for h in heures_ramassage
            ],
            'heures_depart': [
                {'id': h.id, 'heure': h.heure, 'libelle': h.libelle}
                for h in heures_depart
            ],
            'reservations_existantes': [
                {
                    'id': r.id,
                    'agent_id': r.agent.id,
                    'agent_nom': r.agent.nom,
                    'chauffeur_id': r.chauffeur.id,
                    'chauffeur_nom': r.chauffeur.nom,
                    'type_transport': r.type_transport,
                    'heure_id': r.heure_transport.id,
                    'heure_libelle': r.heure_transport.libelle,
                    'statut': r.statut,
                    'est_mienne': r.chauffeur.id == chauffeur_id
                }
                for r in reservations_demain
            ]
        }
        
        print(f"📤 Envoi réponse: {len(str(response_data))} bytes")
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"❌ Erreur api_reservations_demain: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': str(e),
            'traceback': traceback.format_exc()
        })
@csrf_exempt
@require_POST
def api_reserver_agent(request):
    """API pour réserver un agent - VERSION CORRIGÉE AVEC VÉRIFICATION PLANNING"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        data = json.loads(request.body)
        agent_id = data.get('agent_id')
        type_transport = data.get('type_transport')
        heure_id = data.get('heure_id')
        notes = data.get('notes', '')
        
        if not all([agent_id, type_transport, heure_id]):
            return JsonResponse({'success': False, 'error': 'Données manquantes'})
        
        from datetime import date, timedelta
        
        # Récupérer les modèles
        try:
            Reservation = apps.get_model('gestion', 'Reservation')
            Agent = apps.get_model('gestion', 'Agent')
            Chauffeur = apps.get_model('gestion', 'Chauffeur')
            HeureTransport = apps.get_model('gestion', 'HeureTransport')
        except Exception as e:
            print(f"❌ Erreur import modèles: {e}")
            return JsonResponse({
                'success': False, 
                'error': 'Configuration incomplète'
            })
        
        demain = date.today() + timedelta(days=1)
        
        # ========== NOUVELLE VÉRIFICATION CRITIQUE ==========
        # 1. Récupérer l'agent
        try:
            agent = Agent.objects.get(id=agent_id)
            print(f"👤 Agent trouvé: {agent.nom}")
        except Agent.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Agent non trouvé'})
        
        # 2. Vérifier si l'agent est programmé pour demain
        # Convertir demain en jour de semaine
        jours_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        jour_semaine = jours_fr[demain.weekday()]
        
        # 3. Charger le planning EMS.xlsx
        try:
            from gestion.utils import GestionnaireTransport
            
            gestionnaire = GestionnaireTransport()
            
            # Recharger le planning depuis la session
            if not gestionnaire.recharger_planning_depuis_session():
                print("⚠️ Planning non chargé dans la session")
                return JsonResponse({
                    'success': False,
                    'error': "Planning non chargé. Veuillez d'abord charger le planning EMS.xlsx"
                })
            
            # 4. Vérifier si l'agent est dans le planning pour demain
            planning_agent = None
            for planning_data in gestionnaire.planning.values():
                if isinstance(planning_data, dict):
                    for agent_data in planning_data.get('agents', []):
                        if isinstance(agent_data, dict) and agent_data.get('nom') == agent.nom:
                            planning_agent = agent_data
                            break
                    if planning_agent:
                        break
            
            if not planning_agent:
                print(f"❌ Agent {agent.nom} NON PROGRAMMÉ pour demain ({jour_semaine})")
                return JsonResponse({
                    'success': False,
                    'error': f'Agent {agent.nom} non programmé pour {jour_semaine}'
                })
            
            # 5. Vérifier le type de transport et l'heure
            heure_transport = HeureTransport.objects.get(id=heure_id)
            heure_valeur = heure_transport.heure
            
            print(f"🔍 Vérification: Agent {agent.nom}, {jour_semaine}, {type_transport}, {heure_valeur}h")
            
            # Simuler une recherche dans le planning
            class FiltreFormPlanning:
                def __init__(self, jour, type_transport, heure_valeur):
                    self.cleaned_data = {
                        'jour': jour,
                        'type_transport': type_transport,
                        'heure_ete': False,
                        'filtre_agents': 'tous'
                    }
                    self.data = {'heure_specifique': str(heure_valeur)}
            
            form_filtre = FiltreFormPlanning(jour_semaine, type_transport, heure_valeur)
            liste_transports = gestionnaire.traiter_donnees(form_filtre)
            
            # Vérifier si l'agent est dans la liste filtrée
            agent_programme = False
            for transport in liste_transports:
                if transport.get('agent') == agent.nom:
                    agent_programme = True
                    break
            
            if not agent_programme:
                print(f"❌ Agent {agent.nom} non programmé pour {type_transport} à {heure_valeur}h")
                return JsonResponse({
                    'success': False,
                    'error': f'Agent {agent.nom} non programmé pour {type_transport} à {heure_valeur}h'
                })
            
            print(f"✅ Agent {agent.nom} programmé pour {jour_semaine} {type_transport} {heure_valeur}h")
            
        except Exception as e:
            print(f"⚠️ Erreur vérification planning: {e}")
            import traceback
            traceback.print_exc()
            # On continue quand même, mais c'est un risque
            # return JsonResponse({'success': False, 'error': f'Erreur vérification planning: {str(e)}'})
        # ======================================================
        
        # **SOLUTION CRITIQUE** : Vérifier TOUTES les réservations, sans filtrer par statut
        reservation_existante = Reservation.objects.filter(
            agent_id=agent_id,
            date_reservation=demain,
            heure_transport_id=heure_id,
            type_transport=type_transport
        ).first()
        
        print(f"🔍 Réservation existante recherchée pour agent {agent_id}, date {demain}, heure {heure_id}, type {type_transport}")
        print(f"   Trouvée: {reservation_existante is not None}")
        
        if reservation_existante:
            print(f"   Détails: ID {reservation_existante.id}, Statut: {reservation_existante.statut}, Chauffeur: {reservation_existante.chauffeur.nom if reservation_existante.chauffeur else 'None'}")
            
            if reservation_existante.statut == 'annulee':
                # **CAS 1** : Réservation annulée - On peut la réactiver
                reservation_existante.chauffeur_id = chauffeur_id
                reservation_existante.statut = 'reservee'
                reservation_existante.notes = notes
                reservation_existante.updated_at = timezone.now()
                reservation_existante.save()
                
                print(f"✅ Réservation annulée réactivée: ID {reservation_existante.id}")
                
                return JsonResponse({
                    'success': True,
                    'message': 'Réservation effectuée avec succès',
                    'reservation_id': reservation_existante.id,
                    'reactivated': True
                })
                
            elif reservation_existante.statut in ['reservee', 'confirmee']:
                # **CAS 2** : Réservation active
                if reservation_existante.chauffeur_id == int(chauffeur_id):
                    return JsonResponse({
                        'success': False,
                        'error': 'Vous avez déjà réservé cet agent'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'Déjà réservé par le chauffeur {reservation_existante.chauffeur.nom}',
                        'chauffeur_reservant': reservation_existante.chauffeur.nom
                    })
            else:
                # **CAS 3** : Autre statut inattendu
                print(f"⚠️ Statut inattendu: {reservation_existante.statut}")
                return JsonResponse({
                    'success': False,
                    'error': f'Réservation existante avec statut inattendu: {reservation_existante.statut}'
                })
        
        # **CAS 4** : Pas de réservation existante - Créer une nouvelle
        try:
            reservation = Reservation.objects.create(
                chauffeur_id=chauffeur_id,
                agent_id=agent_id,
                date_reservation=demain,
                type_transport=type_transport,
                heure_transport_id=heure_id,
                notes=notes,
                statut='reservee'
            )
            
            print(f"✅ Nouvelle réservation créée: ID {reservation.id}")
            
            return JsonResponse({
                'success': True,
                'message': 'Réservation effectuée avec succès',
                'reservation_id': reservation.id,
                'reactivated': False
            })
            
        except Exception as e:
            # **CAS 5** : Erreur de contrainte UNIQUE (devrait être capturée plus tôt)
            print(f"❌ Erreur création: {e}")
            
            # Dernière tentative : rechercher à nouveau
            reservation_cachee = Reservation.objects.filter(
                agent_id=agent_id,
                date_reservation=demain,
                heure_transport_id=heure_id,
                type_transport=type_transport
            ).first()
            
            if reservation_cachee:
                return JsonResponse({
                    'success': False,
                    'error': f'Réservation cachée trouvée! Statut: {reservation_cachee.statut}, Chauffeur: {reservation_cachee.chauffeur.nom}'
                })
            
            return JsonResponse({
                'success': False, 
                'error': f'Erreur inconnue: {str(e)}'
            })
        
    except Exception as e:
        print(f"❌ Erreur api_reserver_agent: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})
@csrf_exempt
@require_GET
def api_mes_reservations(request):
    """API pour voir les réservations du chauffeur"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        from datetime import date, timedelta
        
        try:
            Reservation = apps.get_model('gestion', 'Reservation')
        except:
            # Fallback si le modèle n'existe pas
            return JsonResponse({
                'success': False,
                'error': 'Module de réservation non disponible'
            })
        
        # Récupérer toutes les réservations du chauffeur
        reservations = Reservation.objects.filter(
            chauffeur_id=chauffeur_id
        ).select_related('agent', 'heure_transport').order_by('-date_reservation', 'heure_transport__heure')
        
        # Filtrer par date si fourni
        date_filter = request.GET.get('date')
        if date_filter:
            try:
                filter_date = date.fromisoformat(date_filter)
                reservations = reservations.filter(date_reservation=filter_date)
            except:
                pass
        
        # Préparer les données
        reservations_data = []
        for r in reservations:
            # Vérifier si peut être modifiée (pour aujourd'hui ou futur)
            peut_annuler = r.date_reservation > date.today()
            
            # Vérifier si c'est pour demain
            est_pour_demain = r.date_reservation == date.today() + timedelta(days=1)
            
            reservations_data.append({
                'id': r.id,
                'agent': {
                    'id': r.agent.id,
                    'nom': r.agent.nom,
                    'adresse': r.agent.adresse,
                    'telephone': r.agent.telephone,
                    'societe': r.agent.get_societe_display(),
                },
                'date': r.date_reservation.strftime('%Y-%m-%d'),
                'date_display': r.date_reservation.strftime('%d/%m/%Y'),
                'type_transport': r.type_transport,
                'type_display': 'Ramassage' if r.type_transport == 'ramassage' else 'Départ',
                'heure': {
                    'id': r.heure_transport.id,
                    'valeur': r.heure_transport.heure,
                    'libelle': r.heure_transport.libelle,
                },
                'statut': r.statut,
                'statut_display': r.get_statut_display(),
                'notes': r.notes or '',
                'created_at': r.created_at.strftime('%d/%m/%Y %H:%M'),
                'peut_annuler': peut_annuler,  # Logique calculée ici
                'est_pour_demain': est_pour_demain,  # Logique calculée ici
            })
        
        return JsonResponse({
            'success': True,
            'reservations': reservations_data,
            'total': len(reservations_data),
            'reservations_demain': len([r for r in reservations_data if r['est_pour_demain']]),
        })
        
    except Exception as e:
        print(f"❌ Erreur api_mes_reservations: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})
@csrf_exempt
@require_POST
def api_annuler_reservation(request, reservation_id):
    """API pour annuler une réservation - VERSION AVEC NOTIFICATION"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        from datetime import date
        
        # Récupérer les modèles
        try:
            Reservation = apps.get_model('gestion', 'Reservation')
            MobileNotification = apps.get_model('chauffeurs_mobile', 'MobileNotification')
        except:
            return JsonResponse({
                'success': False, 
                'error': 'Module de réservation non disponible'
            })
        
        # Récupérer la réservation
        reservation = Reservation.objects.get(id=reservation_id, chauffeur_id=chauffeur_id)
        
        # Vérifier si on peut annuler (date future)
        if reservation.date_reservation <= date.today():
            return JsonResponse({
                'success': False, 
                'error': 'Cette réservation ne peut plus être annulée (date passée)'
            })
        
        # Créer une notification (optionnel)
        try:
            MobileNotification.objects.create(
                chauffeur=reservation.chauffeur,
                type_notification='info',
                message=f"Réservation annulée - Agent: {reservation.agent.nom} ({reservation.get_type_transport_display()})",
                vue=False
            )
        except:
            pass  # Ne pas bloquer si la notification échoue
        
        # Annuler la réservation
        reservation.statut = 'annulee'
        reservation.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Réservation annulée avec succès',
            'reservation_id': reservation.id,
            'agent_id': reservation.agent.id,
            'agent_nom': reservation.agent.nom,
            'refresh_required': True  # Indique au front de rafraîchir
        })
        
    except Reservation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Réservation non trouvée'})
    except Exception as e:
        print(f"❌ Erreur api_annuler_reservation: {e}")
        return JsonResponse({'success': False, 'error': str(e)})
@csrf_exempt
@require_GET
def api_reservations_demain(request):
    """API pour voir les réservations de demain"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        from datetime import date, timedelta
        
        print(f"📅 API réservations demain appelée pour chauffeur {chauffeur_id}")
        
        # Récupérer les modèles
        try:
            from django.apps import apps
            Chauffeur = apps.get_model('gestion', 'Chauffeur')
            Reservation = apps.get_model('gestion', 'Reservation')
            HeureTransport = apps.get_model('gestion', 'HeureTransport')
            print("✅ Modèles importés avec succès")
        except Exception as e:
            print(f"❌ Erreur import modèles: {e}")
            return JsonResponse({
                'success': False, 
                'error': 'Configuration incomplète',
                'details': str(e)
            })
        
        demain = date.today() + timedelta(days=1)
        print(f"📅 Date de demain: {demain}")
        
        # Récupérer le chauffeur
        try:
            chauffeur = Chauffeur.objects.get(id=chauffeur_id)
            print(f"👤 Chauffeur trouvé: {chauffeur.nom}")
        except Chauffeur.DoesNotExist:
            print(f"❌ Chauffeur {chauffeur_id} non trouvé")
            return JsonResponse({
                'success': False,
                'error': 'Chauffeur non trouvé'
            })
        
        # Récupérer les réservations existantes pour demain
        reservations_demain = Reservation.objects.filter(
            date_reservation=demain
        ).select_related('agent', 'heure_transport')
        
        print(f"📋 {reservations_demain.count()} réservation(s) trouvée(s) pour demain")
        
        # Récupérer les heures dynamiques configurées
        heures_ramassage = HeureTransport.objects.filter(
            type_transport='ramassage',
            active=True
        ).order_by('ordre')
        
        heures_depart = HeureTransport.objects.filter(
            type_transport='depart', 
            active=True
        ).order_by('ordre')
        
        print(f"⏰ {heures_ramassage.count()} heure(s) ramassage, {heures_depart.count()} heure(s) départ")
        
        # Préparer la réponse
        response_data = {
            'success': True,
            'date_demain': demain.strftime('%Y-%m-%d'),
            'date_demain_display': demain.strftime('%d/%m/%Y'),
            'chauffeur': {
                'id': chauffeur.id,
                'nom': chauffeur.nom,
            },
            'heures_ramassage': [
                {'id': h.id, 'heure': h.heure, 'libelle': h.libelle}
                for h in heures_ramassage
            ],
            'heures_depart': [
                {'id': h.id, 'heure': h.heure, 'libelle': h.libelle}
                for h in heures_depart
            ],
            'reservations_existantes': [
                {
                    'id': r.id,
                    'agent_id': r.agent.id,
                    'agent_nom': r.agent.nom,
                    'chauffeur_id': r.chauffeur.id,
                    'chauffeur_nom': r.chauffeur.nom,
                    'type_transport': r.type_transport,
                    'heure_id': r.heure_transport.id,
                    'heure_libelle': r.heure_transport.libelle,
                    'statut': r.statut,
                    'est_mienne': r.chauffeur.id == chauffeur_id
                }
                for r in reservations_demain
            ]
        }
        
        print(f"📤 Envoi réponse: {len(str(response_data))} bytes")
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"❌ Erreur api_reservations_demain: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': str(e),
            'traceback': traceback.format_exc()
        })
@csrf_exempt
@require_GET
def api_agents_disponibles_demain(request):
    """API pour voir les agents PROGRAMMÉS À CETTE HEURE pour demain - VERSION AVEC AGENTS RÉSERVÉS VISIBLES"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        from datetime import date, timedelta
        
        # Récupérer les paramètres
        demain = date.today() + timedelta(days=1)
        type_transport = request.GET.get('type_transport', 'ramassage')
        heure_id = request.GET.get('heure_id')
        
        if not heure_id:
            return JsonResponse({'success': False, 'error': 'Heure non spécifiée'})
        
        # Récupérer les modèles
        try:
            from django.apps import apps
            Agent = apps.get_model('gestion', 'Agent')
            Reservation = apps.get_model('gestion', 'Reservation')
            HeureTransport = apps.get_model('gestion', 'HeureTransport')
            Chauffeur = apps.get_model('gestion', 'Chauffeur')
        except Exception as e:
            print(f"❌ Erreur import modèles: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Configuration incomplète'
            })
        
        # 1. Récupérer l'heure de transport
        heure_transport = HeureTransport.objects.get(id=heure_id, active=True)
        heure_valeur = heure_transport.heure
        
        print(f"🔍 Recherche agents PROGRAMMÉS pour {type_transport} à {heure_valeur}h")
        
        # 2. Récupérer TOUTES les réservations pour demain à cette heure
        reservations_demain = Reservation.objects.filter(
            date_reservation=demain,
            heure_transport=heure_transport,
            type_transport=type_transport,
            statut__in=['reservee', 'confirmee']
        ).select_related('chauffeur', 'agent')
        
        print(f"📌 {reservations_demain.count()} réservation(s) trouvée(s)")
        
        # Créer un dict pour vérifier rapidement si un agent est réservé
        reservations_dict = {}
        chauffeurs_reservants = {}  # Pour stocker qui a réservé
        
        for reservation in reservations_demain:
            reservations_dict[reservation.agent_id] = {
                'reserved': True,
                'chauffeur_id': reservation.chauffeur_id,
                'chauffeur_nom': reservation.chauffeur.nom,
                'reservation_id': reservation.id,
                'est_mienne': reservation.chauffeur_id == int(chauffeur_id)
            }
            chauffeurs_reservants[reservation.agent_id] = reservation.chauffeur.nom
        
        # 3. IMPORTANT : CHARGER LE PLANNING POUR FILTRER
        # Convertir demain en jour de semaine
        jours_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        jour_semaine = jours_fr[demain.weekday()]
        
        print(f"📅 Demain: {demain} -> {jour_semaine}")
        
        # 4. Charger le planning (comme dans votre vue liste_transports)
        try:
            from gestion.utils import GestionnaireTransport
            
            gestionnaire = GestionnaireTransport()
            
            # Essayer de charger le planning depuis la session
            if not gestionnaire.recharger_planning_depuis_session():
                print("⚠️ Planning non chargé dans la session")
                # Retourner une liste vide ou des agents de test
                return JsonResponse({
                    'success': True,
                    'date': demain.strftime('%Y-%m-%d'),
                    'date_display': demain.strftime('%d/%m/%Y'),
                    'type_transport': type_transport,
                    'heure': {
                        'id': heure_transport.id,
                        'libelle': heure_transport.libelle,
                        'valeur': heure_transport.heure,
                    },
                    'agents': [],  # Renommé pour plus de clarté
                    'total_agents': 0,
                    'total_disponibles': 0,
                    'total_reserves': 0,
                    'message': "Planning non chargé. Veuillez d'abord charger le planning EMS.xlsx"
                })
            
            # 5. Récupérer les agents PROGRAMMÉS pour ce jour et cette heure
            agents_programmes = []
            
            # Utiliser la même logique que dans liste_transports
            class FiltreFormPlanning:
                def __init__(self, jour, type_transport, heure_valeur):
                    self.cleaned_data = {
                        'jour': jour,
                        'type_transport': type_transport,
                        'heure_ete': False,
                        'filtre_agents': 'tous'
                    }
                    # Ajouter l'heure pour traiter_donnees
                    self.data = {'heure_specifique': str(heure_valeur)}
            
            form_filtre = FiltreFormPlanning(jour_semaine, type_transport, heure_valeur)
            liste_transports = gestionnaire.traiter_donnees(form_filtre)
            
            print(f"📊 {len(liste_transports)} agent(s) programmé(s) pour {jour_semaine} {type_transport} {heure_valeur}h")
            
            # 6. Préparer la liste de TOUS les agents (disponibles ET réservés)
            agents_list = []
            total_disponibles = 0
            total_reserves = 0
            
            for transport in liste_transports:
                agent_nom = transport['agent']
                
                # Chercher l'agent dans la base de données
                agent_obj = Agent.objects.filter(nom__icontains=agent_nom).first()
                
                if agent_obj:
                    # Vérifier si l'agent est réservé
                    est_reserve = agent_obj.id in reservations_dict
                    est_mien = est_reserve and reservations_dict[agent_obj.id]['est_mienne']
                    
                    if est_reserve:
                        total_reserves += 1
                        chauffeur_reservant = reservations_dict[agent_obj.id]['chauffeur_nom']
                    else:
                        total_disponibles += 1
                        chauffeur_reservant = None
                    
                    # Ajouter l'agent à la liste (disponible OU réservé)
                    agents_list.append({
                        'id': agent_obj.id,
                        'nom': agent_obj.nom,
                        'adresse': agent_obj.adresse or 'Non spécifiée',
                        'telephone': agent_obj.telephone or 'Non spécifié',
                        'societe': agent_obj.get_societe_display(),
                        'est_complet': agent_obj.est_complet() if hasattr(agent_obj, 'est_complet') else True,
                        'planning_heure': transport.get('heure', heure_valeur),
                        'est_programme': True,
                        'est_reserve': est_reserve,
                        'est_mien': est_mien,
                        'chauffeur_reservant': chauffeur_reservant,
                        'peut_reserver': not est_reserve,  # Peut réserver seulement si pas déjà réservé
                        'reservation_id': reservations_dict[agent_obj.id]['reservation_id'] if est_reserve else None
                    })
            
            print(f"✅ {len(agents_list)} agent(s) au total: {total_disponibles} disponible(s), {total_reserves} réservé(s)")
            
            # 7. Formatage de la réponse
            return JsonResponse({
                'success': True,
                'date': demain.strftime('%Y-%m-%d'),
                'date_display': demain.strftime('%d/%m/%Y'),
                'jour_semaine': jour_semaine,
                'type_transport': type_transport,
                'heure': {
                    'id': heure_transport.id,
                    'libelle': heure_transport.libelle,
                    'valeur': heure_transport.heure,
                },
                'agents': agents_list,  # Tous les agents
                'stats': {
                    'total_agents': len(agents_list),
                    'total_disponibles': total_disponibles,
                    'total_reserves': total_reserves,
                    'disponibles_pourcent': round((total_disponibles / len(agents_list) * 100) if len(agents_list) > 0 else 0, 1)
                },
                'message': f"{total_disponibles} agent(s) disponible(s) sur {len(agents_list)}"
            })
            
        except Exception as e:
            print(f"❌ Erreur chargement planning: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'error': f'Erreur chargement planning: {str(e)}'
            })
        
    except HeureTransport.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Heure non trouvée'})
    except Exception as e:
        print(f"❌ Erreur api_agents_disponibles_demain: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})
# API pour l'historique
@csrf_exempt
@require_GET
def api_historique(request):
    """API pour voir toutes les courses (passées) avec filtrage par mois par défaut et les agents transportés"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        Agent = apps.get_model('gestion', 'Agent')
        
        # Récupérer les filtres
        date_debut_str = request.GET.get('date_debut')
        date_fin_str = request.GET.get('date_fin')
        statut_filter = request.GET.get('statut')
        
        # Base queryset - toutes les courses du chauffeur
        courses = Course.objects.filter(chauffeur_id=chauffeur_id)
        
        # Si aucune date n'est spécifiée, prendre le mois en cours par défaut
        if not date_debut_str and not date_fin_str:
            now = timezone.now()
            date_debut = datetime(now.year, now.month, 1).date()
            # Dernier jour du mois
            if now.month == 12:
                date_fin = datetime(now.year + 1, 1, 1).date() - timedelta(days=1)
            else:
                date_fin = datetime(now.year, now.month + 1, 1).date() - timedelta(days=1)
            
            courses = courses.filter(date_reelle__range=[date_debut, date_fin])
            print(f"📅 Filtre par défaut: mois en cours ({date_debut} à {date_fin})")
        
        # Si seulement date début est spécifiée
        elif date_debut_str and not date_fin_str:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
            courses = courses.filter(date_reelle__gte=date_debut)
            print(f"📅 Filtre: à partir de {date_debut}")
        
        # Si seulement date fin est spécifiée
        elif not date_debut_str and date_fin_str:
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
            courses = courses.filter(date_reelle__lte=date_fin)
            print(f"📅 Filtre: jusqu'à {date_fin}")
        
        # Si les deux dates sont spécifiées
        elif date_debut_str and date_fin_str:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
            courses = courses.filter(date_reelle__range=[date_debut, date_fin])
            print(f"📅 Filtre: intervalle {date_debut} à {date_fin}")
        
        # Filtrer par statut si spécifié
        if statut_filter and statut_filter != 'tous':
            courses = courses.filter(statut=statut_filter)
            print(f"📊 Filtre statut: {statut_filter}")
        
        # Trier par date (plus récent d'abord)
        courses = courses.order_by('-date_reelle', '-heure')
        
        print(f"📋 Nombre de courses trouvées: {courses.count()}")
        
        courses_data = []
        for course in courses:
            # Récupérer les agents affectés à cette course
            affectations = Affectation.objects.filter(course=course).select_related('agent')
            
            # Liste des agents avec leurs informations
            agents_list = []
            for affectation in affectations:
                if affectation.agent:
                    agents_list.append({
                        'id': affectation.agent.id,
                        'nom': affectation.agent.nom or 'Non spécifié',
                        'adresse': affectation.agent.adresse or 'Non spécifiée',
                        'telephone': affectation.agent.telephone or 'Non spécifié',
                        'societe': affectation.agent.get_societe_display() if hasattr(affectation.agent, 'get_societe_display') else 'Non spécifiée',
                    })
            
            # Prix de la course
            prix_course = course.get_prix_course() if hasattr(course, 'get_prix_course') else 0
            prix_total = float(course.prix_total or prix_course)
            
            courses_data.append({
                'id': course.id,
                'date': course.date_reelle.strftime('%Y-%m-%d'),
                'date_display': course.date_reelle.strftime('%d/%m/%Y'),
                'type': course.type_transport,
                'type_display': 'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                'heure': course.heure,
                'heure_display': f"{course.heure}h",
                'nb_agents': affectations.count(),
                'agents': agents_list,  # Ajout de la liste des agents
                'statut': course.statut,
                'statut_display': course.get_statut_display(),
                'prix': prix_total,
                'prix_display': f"{prix_total:.2f} €",
                'notes': course.notes_validation or '',
                'mois': course.date_reelle.strftime('%Y-%m'),  # Pour le regroupement
            })
        
        # Statistiques
        total_courses = len(courses_data)
        courses_validees = len([c for c in courses_data if c['statut'] in ['validee', 'payee']])
        revenu_total = sum([c['prix'] for c in courses_data if c['statut'] in ['validee', 'payee']])
        
        # Calculer les dates par défaut pour l'affichage
        now = timezone.now()
        date_debut_default = datetime(now.year, now.month, 1).date()
        if now.month == 12:
            date_fin_default = datetime(now.year + 1, 1, 1).date() - timedelta(days=1)
        else:
            date_fin_default = datetime(now.year, now.month + 1, 1).date() - timedelta(days=1)
        
        return JsonResponse({
            'success': True,
            'courses': courses_data,
            'filtres': {
                'date_debut': date_debut_str or date_debut_default.strftime('%Y-%m-%d'),
                'date_fin': date_fin_str or date_fin_default.strftime('%Y-%m-%d'),
                'statut': statut_filter or 'tous',
            },
            'stats': {
                'total': total_courses,
                'validees': courses_validees,
                'revenu_total': round(revenu_total, 2),
                'periode': f"{date_debut_default.strftime('%d/%m/%Y')} - {date_fin_default.strftime('%d/%m/%Y')}"
            }
        })
        
    except Exception as e:
        print(f"❌ Erreur historique: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})
# API pour les courses de sélection
@csrf_exempt
@require_GET
def api_courses_selection(request):
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        date_str = request.GET.get('date', None)
        if date_str:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            selected_date = timezone.now().date()
        
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        courses = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            date_reelle=selected_date
        ).order_by('heure')
        
        courses_data = []
        for course in courses:
            agents_data = []
            
            try:
                affectations = course.affectation_set.select_related('agent').all()
                
                for affectation in affectations[:3]:
                    if affectation.agent:
                        agents_data.append({
                            'nom': affectation.agent.nom or 'Non spécifié',
                            'adresse': affectation.agent.adresse or 'Non spécifié',
                        })
                
                if affectations.count() > 3:
                    agents_data.append({
                        'nom': f'+ {affectations.count() - 3} autres',
                        'adresse': ''
                    })
                    
            except Exception as e:
                print(f"⚠️ Erreur agents pour course {course.id}: {e}")
                agents_data = []
            
            courses_data.append({
                'id': course.id,
                'date': course.date_reelle.strftime('%d/%m/%Y'),
                'type_transport': course.type_transport,
                'type_display': 'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                'heure': course.heure,
                'heure_display': f"{course.heure}h",
                'nb_agents': course.affectation_set.count(),
                'agents': agents_data,
                'statut': course.statut,
                'statut_display': course.get_statut_display() if hasattr(course, 'get_statut_display') else course.statut,
                'prix': float(course.get_prix_course() or 0) if hasattr(course, 'get_prix_course') else 0,
                'peut_valider': course.statut in ['en_attente', 'en_cours'],
            })
        
        return JsonResponse({
            'success': True,
            'courses': courses_data,
            'date': selected_date.strftime('%Y-%m-%d'),
            'date_display': selected_date.strftime('%d/%m/%Y'),
            'total': len(courses_data),
            'message': f"{len(courses_data)} courses trouvées"
        })
        
    except Exception as e:
        print(f"❌ Erreur courses_selection: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'courses': [],
            'total': 0
        })

# API pour annuler une course
@csrf_exempt
@require_POST
def api_annuler_course(request):
    """API pour annuler une course"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')
        
        Course = apps.get_model('gestion', 'Course')
        course = Course.objects.get(id=course_id, chauffeur_id=chauffeur_id)
        
        course.statut = 'annulee'
        course.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Course annulée',
            'statut': course.statut,
            'statut_display': 'Annulée'
        })
        
    except Course.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Course non trouvée'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# API pour créer une course
@csrf_exempt
@require_POST
def api_creer_course(request):
    """API pour créer une course avec agents sélectionnés"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        data = json.loads(request.body)
        
        date_str = data.get('date')
        type_transport = data.get('type_transport')
        heure = data.get('heure')
        agents_ids = data.get('agents', [])
        
        if not all([date_str, type_transport, heure, agents_ids]):
            return JsonResponse({
                'success': False,
                'error': 'Données manquantes'
            })
        # ⬇️ AJOUTER CETTE VALIDATION ⬇️
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        aujourd_hui = timezone.now().date()
        
        if date_obj != aujourd_hui:
            return JsonResponse({
                'success': False,
                'error': "Vous ne pouvez créer des courses que pour aujourdhui"
            })
        
        # ⬇️ VALIDER L'HEURE (optionnel) ⬇️
        heure_int = int(heure)
        
        # Récupérer les modèles
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        Agent = apps.get_model('gestion', 'Agent')
        
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        heure_int = int(heure)
        
        # Vérifier si une course existe déjà
        course, created = Course.objects.get_or_create(
            chauffeur=chauffeur,
            date_reelle=date_obj,
            type_transport=type_transport,
            heure=heure_int,
            defaults={
                'jour': date_obj.strftime('%A'),
                'statut': 'en_attente'
            }
        )
        
        # Ajouter les affectations
        agents_affectes = []
        for agent_id in agents_ids:
            try:
                agent = Agent.objects.get(id=agent_id)
                
                # Vérifier si l'agent n'est pas déjà affecté ce jour
                existe_deja = Affectation.objects.filter(
                    agent=agent,
                    date_reelle=date_obj
                ).exists()
                
                if not existe_deja:
                    affectation = Affectation.objects.create(
                        course=course,
                        chauffeur=chauffeur,
                        agent=agent,
                        type_transport=type_transport,
                        heure=heure_int,
                        jour=date_obj.strftime('%A'),
                        date_reelle=date_obj,
                        prix_course=course.get_prix_course() if hasattr(course, 'get_prix_course') else 0
                    )
                    agents_affectes.append(agent.nom)
                else:
                    print(f"⚠️ Agent {agent.nom} déjà affecté ce jour")
                    
            except Agent.DoesNotExist:
                print(f"⚠️ Agent ID {agent_id} non trouvé")
                continue
        
        # Mettre à jour le statut
        course.statut = 'en_attente'
        course.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Course créée avec {len(agents_affectes)} agent(s)',
            'course_id': course.id,
            'agents_affectes': agents_affectes,
            'created': created
        })
        
    except Exception as e:
        print(f"❌ Erreur création course: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# API pour les agents disponibles
@csrf_exempt
@require_GET
def api_agents_disponibles(request):
    """API pour voir les agents disponibles pour aujourd'hui - EXCLUT LES DÉJÀ DANS UNE COURSE"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        # Récupérer les paramètres
        date_str = request.GET.get('date')
        type_transport = request.GET.get('type_transport')
        heure = request.GET.get('heure')
        
        # Forcer la date à aujourd'hui si non spécifiée
        if not date_str:
            date_str = timezone.now().date().isoformat()
        
        if not all([date_str, type_transport, heure]):
            return JsonResponse({
                'success': False,
                'error': 'Paramètres manquants: type_transport, heure requis'
            })
        
        # Valider que c'est aujourd'hui
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        aujourd_hui = timezone.now().date()
        
        if date_obj != aujourd_hui:
            return JsonResponse({
                'success': False,
                'error': "Vous ne pouvez voir les agents disponibles que pour aujourd'hui"
            })
        
        # Récupérer les modèles
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        Agent = apps.get_model('gestion', 'Agent')
        Reservation = apps.get_model('gestion', 'Reservation')
        
        # Convertir la date
        heure_int = int(heure)
        
        print(f"🔍 Recherche agents pour: {date_obj} - {type_transport} - {heure_int}h")
        
        # 1. Vérifier si le chauffeur a déjà une course à cette heure
        course_existante = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            date_reelle=date_obj,
            type_transport=type_transport,
            heure=heure_int
        ).first()
        
        if course_existante:
            # Récupérer les agents déjà affectés à cette course
            agents_affectes = course_existante.affectation_set.all()
            agents_ids = [a.agent_id for a in agents_affectes]
            
            return JsonResponse({
                'success': True,
                'course_id': course_existante.id,
                'agents_affectes': [
                    {
                        'id': a.agent.id,
                        'nom': a.agent.nom,
                        'adresse': a.agent.adresse,
                        'telephone': a.agent.telephone,
                        'societe': a.agent.get_societe_display(),
                        'est_affecte': True,
                        'est_mien': True
                    }
                    for a in agents_affectes
                ],
                'statut_course': course_existante.statut
            })
        
        # 2. Récupérer TOUS les agents DÉJÀ DANS UNE COURSE aujourd'hui
        # (peu importe l'heure ou le type de transport)
        agents_deja_dans_course = Affectation.objects.filter(
            date_reelle=date_obj
        ).values_list('agent_id', flat=True).distinct()
        
        print(f"🚗 {len(agents_deja_dans_course)} agent(s) déjà dans une course aujourd'hui")
        
        # 3. Récupérer les agents RÉSERVÉS pour aujourd'hui (pour les afficher en premier)
        reservations_aujourdhui = Reservation.objects.filter(
            date_reservation=date_obj,
            statut__in=['reservee', 'confirmee']
        ).select_related('chauffeur', 'agent')
        
        # Filtrer par type de transport
        reservations_filtrees = [r for r in reservations_aujourdhui if r.type_transport == type_transport]
        
        print(f"📅 {len(reservations_filtrees)} réservation(s) pour aujourd'hui ({type_transport})")
        
        # 4. Récupérer TOUS les agents (exclure ceux avec voiture personnelle)
        tous_agents = Agent.objects.filter(
            voiture_personnelle=False
        ).order_by('nom')
        
        # 5. Séparer les agents en trois catégories
        agents_reserves = []      # Réservés pour aujourd'hui
        agents_disponibles = []   # Pas dans une course
        agents_dans_course = []   # Déjà dans une course (ceux-ci doivent être exclus)
        
        # Dictionnaire pour les réservations par agent
        reservations_par_agent = {}
        for reservation in reservations_filtrees:
            reservations_par_agent[reservation.agent_id] = {
                'chauffeur_nom': reservation.chauffeur.nom,
                'est_mien': reservation.chauffeur_id == int(chauffeur_id),
                'reservation_id': reservation.id,
                'heure_reservation': reservation.heure_transport.heure if reservation.heure_transport else None
            }
        
        for agent in tous_agents:
            agent_data = {
                'id': agent.id,
                'nom': agent.nom,
                'adresse': agent.adresse,
                'telephone': agent.telephone,
                'societe': agent.get_societe_display(),
                'est_complet': agent.est_complet() if hasattr(agent, 'est_complet') else True,
            }
            
            # Vérifier si l'agent est déjà dans une course
            if agent.id in agents_deja_dans_course:
                # Agent déjà dans une course → EXCLURE DE LA LISTE
                agents_dans_course.append(agent_data)
                continue
            
            # Vérifier si l'agent a une réservation pour aujourd'hui
            if agent.id in reservations_par_agent:
                # Agent réservé → ajouter aux réservés
                agent_data.update(reservations_par_agent[agent.id])
                agent_data['est_reserve'] = True
                agents_reserves.append(agent_data)
            else:
                # Agent disponible
                agent_data['est_disponible'] = True
                agents_disponibles.append(agent_data)
        
        print(f"📊 {len(agents_reserves)} réservé(s), {len(agents_disponibles)} disponible(s), {len(agents_dans_course)} déjà dans une course (exclus)")
        
        # 6. Organiser l'ordre d'affichage
        agents_final = []
        
        # a) D'abord les agents RÉSERVÉS (via page Réservation)
        #    - Mes réservations en premier
        mes_reserves = [a for a in agents_reserves if a.get('est_mien', False)]
        autres_reserves = [a for a in agents_reserves if not a.get('est_mien', False)]
        agents_final.extend(mes_reserves)
        agents_final.extend(autres_reserves)
        
        # b) Ensuite les agents DISPONIBLES
        agents_final.extend(agents_disponibles)
        
        return JsonResponse({
            'success': True,
            'agents': agents_final,
            'stats': {
                'total': len(agents_final),
                'reserves': len(agents_reserves),
                'disponibles': len(agents_disponibles),
                'exclus': len(agents_dans_course),  # Ceux déjà dans une course
                'mes_reserves': len(mes_reserves)
            },
            'date': date_str,
            'type_transport': type_transport,
            'heure': heure_int
        })
        
    except Exception as e:
        print(f"❌ Erreur agents_disponibles: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
# API pour terminer une course
@csrf_exempt
@require_POST
def api_terminer_course(request):
    """API pour qu'un chauffeur termine une course"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')
        
        Course = apps.get_model('gestion', 'Course')
        course = Course.objects.get(id=course_id, chauffeur_id=chauffeur_id)
        
        if course.statut not in ['en_attente', 'en_cours']:
            return JsonResponse({
                'success': False, 
                'error': f'Course déjà {course.get_statut_display()}'
            })
        
        course.statut = 'terminee'
        course.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Course terminée avec succès',
            'statut': course.statut,
            'statut_display': course.get_statut_display()
        })
        
    except Course.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Course non trouvée'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# API pour demander validation
@csrf_exempt
@require_POST
def api_demander_validation(request):
    """API pour qu'un chauffeur demande la validation d'une course"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        data = json.loads(request.body)
        course_id = data.get('course_id')
        notes = data.get('notes', '')
        
        Course = apps.get_model('gestion', 'Course')
        course = Course.objects.get(id=course_id, chauffeur_id=chauffeur_id)
        
        if course.statut != 'terminee':
            return JsonResponse({
                'success': False, 
                'error': 'La course doit être terminée avant validation'
            })
        
        # Utiliser la méthode du modèle si elle existe
        if hasattr(course, 'demander_validation'):
            course.demander_validation(notes)
        else:
            # Fallback
            course.statut = 'demande_validation'
            course.notes_validation = notes
            course.demande_validation_at = timezone.now()
            course.save()
        
        return JsonResponse({
            'success': True,
            'message': "Demande de validation envoyée à l'admin",
            'statut': course.statut,
            'statut_display': course.get_statut_display()
        })
        
    except Course.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Course non trouvée'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# API pour voir les courses VALIDÉES
@csrf_exempt
@require_GET
def api_courses_validees(request):
    """API pour voir les courses VALIDÉES par l'admin"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        # Courses VALIDÉES seulement (statut='validee')
        courses = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            statut='validee'
        ).order_by('-date_reelle', '-heure')
        
        courses_data = []
        total_montant = 0
        
        for course in courses:
            # Compter les agents
            nb_agents = Affectation.objects.filter(course=course).count()
            
            # Calculer le montant
            montant = 0
            if hasattr(course, 'prix_total') and course.prix_total:
                montant = float(course.prix_total)
            elif hasattr(course, 'get_prix_course'):
                montant = float(course.get_prix_course() or 0)
            
            total_montant += montant
            
            courses_data.append({
                'id': course.id,
                'date': course.date_reelle.strftime('%Y-%m-%d'),
                'date_display': course.date_reelle.strftime('%d/%m/%Y'),
                'type': course.type_transport,
                'type_display': 'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                'heure': course.heure,
                'heure_display': f"{course.heure}h",
                'nb_agents': nb_agents,
                'montant': montant,
                'montant_display': f"{montant:.2f} €",
                'statut': course.statut,
                'statut_display': 'Validée',
            })
        
        return JsonResponse({
            'success': True,
            'courses': courses_data,
            'stats': {
                'total': len(courses_data),
                'total_montant': total_montant,
                'total_montant_display': f"{total_montant:.2f} €",
            },
            'message': f"{len(courses_data)} courses validées"
        })
        
    except Exception as e:
        print(f"❌ Erreur courses_validees: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'courses': [],
            'stats': {'total': 0, 'total_montant': 0}
        })

# API pour voir les courses EN ATTENTE
@csrf_exempt
@require_GET
def api_courses_en_attente(request):
    """API pour voir les courses EN ATTENTE de validation admin"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        # Courses EN ATTENTE seulement (statut='en_attente')
        courses = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            statut='en_attente'
        ).order_by('-created_at', 'date_reelle', 'heure')
        
        courses_data = []
        
        for course in courses:
            nb_agents = Affectation.objects.filter(course=course).count()
            
            courses_data.append({
                'id': course.id,
                'date': course.date_reelle.strftime('%Y-%m-%d'),
                'date_display': course.date_reelle.strftime('%d/%m/%Y'),
                'type': course.type_transport,
                'type_display': 'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                'heure': course.heure,
                'heure_display': f"{course.heure}h",
                'nb_agents': nb_agents,
                'statut': course.statut,
                'statut_display': 'En attente',
                'created_at': course.created_at.strftime('%d/%m/%Y %H:%M') if hasattr(course, 'created_at') else '',
            })
        
        return JsonResponse({
            'success': True,
            'courses': courses_data,
            'total': len(courses_data),
            'message': f"{len(courses_data)} courses en attente de validation"
        })
        
    except Exception as e:
        print(f"❌ Erreur courses_en_attente: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'courses': [],
            'total': 0
        })

# API pour voir les courses ANNULÉES
@csrf_exempt
@require_GET
def api_courses_annulees(request):
    """API pour voir les courses ANNULÉES par l'admin"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        # Courses ANNULÉES seulement (statut='annulee')
        courses = Course.objects.filter(
            chauffeur_id=chauffeur_id,
            statut='annulee'
        ).order_by('-date_reelle', '-heure')
        
        courses_data = []
        
        for course in courses:
            nb_agents = Affectation.objects.filter(course=course).count()
            
            courses_data.append({
                'id': course.id,
                'date': course.date_reelle.strftime('%Y-%m-%d'),
                'date_display': course.date_reelle.strftime('%d/%m/%Y'),
                'type': course.type_transport,
                'type_display': 'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                'heure': course.heure,
                'heure_display': f"{course.heure}h",
                'nb_agents': nb_agents,
                'statut': course.statut,
                'statut_display': 'Annulée',
                'notes_validation': course.notes_validation or 'Non spécifiée',
            })
        
        return JsonResponse({
            'success': True,
            'courses': courses_data,
            'total': len(courses_data),
            'message': f"{len(courses_data)} courses annulées"
        })
        
    except Exception as e:
        print(f"❌ Erreur courses_annulees: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'courses': [],
            'total': 0
        })
@csrf_exempt
@require_GET
def api_super_chauffeurs_list(request):
    """API pour voir tous les chauffeurs (super-chauffeur seulement)"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    print(f"🔍 API super/chauffeurs/ appelée - Session: {dict(request.session)}")
    print(f"🔍 Chauffeur ID depuis session: {chauffeur_id}")
    
    if not chauffeur_id:
        print("❌ Pas de chauffeur_id dans la session")
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        # Importer les modèles de manière robuste
        try:
            from django.apps import apps
            Chauffeur = apps.get_model('gestion', 'Chauffeur')
            Course = apps.get_model('gestion', 'Course')
        except Exception as e:
            print(f"❌ Erreur import modèles: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Modèles non disponibles: {str(e)}'
            })
        
        # Vérifier si c'est un super-chauffeur
        try:
            chauffeur = Chauffeur.objects.get(id=chauffeur_id)
            print(f"✅ Chauffeur trouvé: {chauffeur.nom}")
            print(f"🔍 Champs du modèle: {[f.name for f in chauffeur._meta.fields]}")
            
            # Vérifier le champ super_chauffeur
            if hasattr(chauffeur, 'super_chauffeur'):
                is_super = chauffeur.super_chauffeur
                print(f"🎯 super_chauffeur attribut direct: {is_super}")
            else:
                # Vérifier si le champ existe dans la base de données
                print("⚠️ Champ 'super_chauffeur' non trouvé dans le modèle")
                
                # Fallback : autoriser l'accès pour le test
                is_super = True  # Pour le test, autoriser l'accès
                print("⚠️ ATTENTION: Champ super_chauffeur non défini - autorisation temporaire")
            
            print(f"🎯 Est super chauffeur? {is_super}")
            
            if not is_super:
                print("❌ Le chauffeur n'est PAS un super_chauffeur")
                return JsonResponse({
                    'success': False,
                    'error': 'Accès réservé aux super-chauffeurs',
                    'is_super': False,
                    'champs_model': [f.name for f in chauffeur._meta.fields]  # Debug
                }, status=403)
                
        except Chauffeur.DoesNotExist:
            print(f"❌ Chauffeur {chauffeur_id} non trouvé")
            return JsonResponse({'success': False, 'error': 'Chauffeur non trouvé'})
        
        print("✅ Le chauffeur EST un super_chauffeur - continuer...")
        
        # Récupérer TOUS les chauffeurs (pas seulement actifs pour le test)
        all_chauffeurs = Chauffeur.objects.all().order_by('nom')
        print(f"📊 {all_chauffeurs.count()} chauffeur(s) trouvé(s)")
        
        chauffeurs_data = []
        today = timezone.now().date()
        
        for ch in all_chauffeurs:
            # Compter les courses du mois (simplifié)
            courses_count = Course.objects.filter(
                chauffeur=ch,
                date_reelle__year=today.year,
                date_reelle__month=today.month
            ).count()
            
            # Compter les courses validées
            courses_validees = Course.objects.filter(
                chauffeur=ch,
                date_reelle__year=today.year,
                date_reelle__month=today.month,
                statut__in=['validee', 'payee']
            ).count()
            
            # Calculer le revenu (simplifié)
            revenu = 0
            try:
                courses_val = Course.objects.filter(
                    chauffeur=ch,
                    date_reelle__year=today.year,
                    date_reelle__month=today.month,
                    statut__in=['validee', 'payee']
                )
                for course in courses_val:
                    if hasattr(course, 'prix_total') and course.prix_total:
                        try:
                            revenu += float(course.prix_total)
                        except (ValueError, TypeError):
                            pass
            except Exception as e:
                print(f"⚠️ Erreur calcul revenu {ch.id}: {e}")
            
            chauffeur_info = {
                'id': ch.id,
                'nom': ch.nom,
                'telephone': ch.telephone,
                'type_chauffeur': getattr(ch, 'type_chauffeur', 'taxi'),
                'vehicule': getattr(ch, 'numero_voiture', 'Non spécifié'),
                'actif': ch.actif,
                'super_chauffeur': getattr(ch, 'super_chauffeur', False),
            }
            
            # Ajouter statistiques
            chauffeur_info['statistiques'] = {
                'courses_mois': courses_count,
                'courses_validees': courses_validees,
                'revenu_mois': round(revenu, 2) if revenu else 0,
                'moyenne_course': round(revenu / courses_validees, 2) if courses_validees > 0 else 0
            }
            
            chauffeurs_data.append(chauffeur_info)
        
        return JsonResponse({
            'success': True,
            'is_super_chauffeur': True,
            'chauffeurs': chauffeurs_data,
            'total': len(chauffeurs_data),
            'periode': f"{today.strftime('%m/%Y')}",
            'debug_info': {
                'chauffeur_session_id': chauffeur_id,
                'chauffeur_nom': chauffeur.nom,
                'super_chauffeur': getattr(chauffeur, 'super_chauffeur', False)
            }
        })
        
    except Exception as e:
        print(f"❌ Erreur api_super_chauffeurs_list: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': str(e),
            'traceback': traceback.format_exc()[:500]
        })
@csrf_exempt
@require_GET
def api_super_chauffeur_detail(request, chauffeur_id):
    """API pour voir le détail d'un chauffeur (super-chauffeur seulement)"""
    current_chauffeur_id = request.session.get('chauffeur_id')
    
    if not current_chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        # Vérifier si c'est un super-chauffeur
        current_chauffeur = Chauffeur.objects.get(id=current_chauffeur_id)
        
        if not getattr(current_chauffeur, 'super_chauffeur', False):
            return JsonResponse({
                'success': False,
                'error': 'Accès réservé aux super-chauffeurs'
            }, status=403)
        
        # Récupérer le chauffeur cible
        target_chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        
        # Récupérer les courses récentes (30 derniers jours)
        date_debut = timezone.now().date() - timedelta(days=30)
        courses = Course.objects.filter(
            chauffeur=target_chauffeur,
            date_reelle__gte=date_debut
        ).order_by('-date_reelle', '-heure')
        
        courses_data = []
        total_revenu = 0
        
        for course in courses:
            nb_agents = Affectation.objects.filter(course=course).count()
            prix = 0
            if hasattr(course, 'prix_total') and course.prix_total:
                prix = float(course.prix_total)
            elif hasattr(course, 'get_prix_course'):
                prix = float(course.get_prix_course() or 0)
            
            if course.statut in ['validee', 'payee']:
                total_revenu += prix
            
            courses_data.append({
                'id': course.id,
                'date': course.date_reelle.strftime('%Y-%m-%d'),
                'date_display': course.date_reelle.strftime('%d/%m/%Y'),
                'type': course.type_transport,
                'type_display': 'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                'heure': course.heure,
                'heure_display': f"{course.heure}h",
                'nb_agents': nb_agents,
                'statut': course.statut,
                'statut_display': course.get_statut_display(),
                'prix': prix,
                'prix_display': f"{prix:.2f} €",
                'notes': course.notes_validation or ''
            })
        
        # Statistiques globales
        total_courses = Course.objects.filter(chauffeur=target_chauffeur).count()
        total_validees = Course.objects.filter(
            chauffeur=target_chauffeur,
            statut__in=['validee', 'payee']
        ).count()
        
        # Revenu total
        all_courses = Course.objects.filter(
            chauffeur=target_chauffeur,
            statut__in=['validee', 'payee']
        )
        revenu_total = 0
        for course in all_courses:
            if hasattr(course, 'prix_total') and course.prix_total:
                revenu_total += float(course.prix_total)
        
        return JsonResponse({
            'success': True,
            'is_super_chauffeur': True,
            'current_chauffeur': {
                'id': current_chauffeur.id,
                'nom': current_chauffeur.nom,
                'super_chauffeur': True
            },
            'target_chauffeur': {
                'id': target_chauffeur.id,
                'nom': target_chauffeur.nom,
                'telephone': target_chauffeur.telephone,
                'type_chauffeur': target_chauffeur.type_chauffeur,
                'vehicule': target_chauffeur.numero_voiture,
                'actif': target_chauffeur.actif,
                'super_chauffeur': getattr(target_chauffeur, 'super_chauffeur', False),
                'adresse': getattr(target_chauffeur, 'adresse', ''),
                'email': getattr(target_chauffeur, 'email', ''),
                'societe': getattr(target_chauffeur, 'societe', '')
            },
            'courses': courses_data,
            'statistiques': {
                'total_courses': total_courses,
                'total_validees': total_validees,
                'total_revenu': round(revenu_total, 2),
                'moyenne_mensuelle': round(revenu_total / 12, 2) if revenu_total > 0 else 0,
                'courses_30_jours': len(courses_data),
                'revenu_30_jours': round(total_revenu, 2)
            }
        })
        
    except Chauffeur.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Chauffeur non trouvé'})
    except Exception as e:
        print(f"❌ Erreur api_super_chauffeur_detail: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_GET
def api_super_courses_today(request):
    """API pour voir toutes les courses d'aujourd'hui (super-chauffeur seulement)"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        Chauffeur = apps.get_model('gestion', 'Chauffeur')
        Course = apps.get_model('gestion', 'Course')
        Affectation = apps.get_model('gestion', 'Affectation')
        
        # Vérifier si c'est un super-chauffeur
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        
        if not getattr(chauffeur, 'super_chauffeur', False):
            return JsonResponse({
                'success': False,
                'error': 'Accès réservé aux super-chauffeurs'
            }, status=403)
        
        # Date d'aujourd'hui
        aujourd_hui = timezone.now().date()
        
        # Récupérer toutes les courses d'aujourd'hui
        courses = Course.objects.filter(date_reelle=aujourd_hui).order_by('heure', 'chauffeur__nom')
        
        courses_data = []
        
        for course in courses:
            nb_agents = Affectation.objects.filter(course=course).count()
            
            # Récupérer les agents
            agents = Affectation.objects.filter(course=course).select_related('agent')
            agents_list = []
            for affectation in agents[:3]:  # Limiter à 3 pour l'affichage
                if affectation.agent:
                    agents_list.append(affectation.agent.nom)
            
            courses_data.append({
                'id': course.id,
                'chauffeur_id': course.chauffeur.id,
                'chauffeur_nom': course.chauffeur.nom,
                'type': course.type_transport,
                'type_display': 'Ramassage' if course.type_transport == 'ramassage' else 'Départ',
                'heure': course.heure,
                'heure_display': f"{course.heure}h",
                'nb_agents': nb_agents,
                'agents': agents_list,
                'agents_count': nb_agents,
                'statut': course.statut,
                'statut_display': course.get_statut_display(),
                'prix': float(course.get_prix_course() or 0) if hasattr(course, 'get_prix_course') else 0,
            })
        
        # Statistiques
        total_courses = courses.count()
        courses_validees = courses.filter(statut__in=['validee', 'payee']).count()
        courses_en_cours = courses.filter(statut__in=['en_attente', 'en_cours']).count()
        courses_terminees = courses.filter(statut='terminee').count()
        
        return JsonResponse({
            'success': True,
            'is_super_chauffeur': True,
            'date': aujourd_hui.strftime('%d/%m/%Y'),
            'courses': courses_data,
            'statistiques': {
                'total': total_courses,
                'validees': courses_validees,
                'en_cours': courses_en_cours,
                'terminees': courses_terminees,
                'chauffeurs_actifs': len(set([c['chauffeur_id'] for c in courses_data]))
            }
        })
        
    except Exception as e:
        print(f"❌ Erreur api_super_courses_today: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})
@csrf_exempt
@require_GET
def api_super_reservations_demain(request):
    """API pour voir TOUTES les réservations de demain ET les agents non réservés"""
    chauffeur_id = request.session.get('chauffeur_id')
    
    if not chauffeur_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)
    
    try:
        from datetime import date, timedelta
        
        # Récupérer les modèles
        try:
            from django.apps import apps
            Chauffeur = apps.get_model('gestion', 'Chauffeur')
            Reservation = apps.get_model('gestion', 'Reservation')
            HeureTransport = apps.get_model('gestion', 'HeureTransport')
            Agent = apps.get_model('gestion', 'Agent')
        except Exception as e:
            print(f"❌ Erreur import modèles: {e}")
            return JsonResponse({
                'success': False, 
                'error': 'Configuration incomplète'
            })
        
        # Vérifier si c'est un super-chauffeur
        chauffeur = Chauffeur.objects.get(id=chauffeur_id)
        
        if not getattr(chauffeur, 'super_chauffeur', False):
            return JsonResponse({
                'success': False,
                'error': 'Accès réservé aux super-chauffeurs'
            }, status=403)
        
        demain = date.today() + timedelta(days=1)
        
        # Récupérer TOUTES les réservations pour demain
        reservations = Reservation.objects.filter(
            date_reservation=demain
        ).select_related('chauffeur', 'agent', 'heure_transport').order_by('heure_transport__heure', 'chauffeur__nom')
        
        # Récupérer tous les agents actifs (sans voiture personnelle)
        tous_agents = Agent.objects.filter(
            voiture_personnelle=False
        ).order_by('nom')
        
        # Récupérer les agents qui ont été réservés
        agents_reserves_ids = reservations.values_list('agent_id', flat=True).distinct()
        agents_reserves = Agent.objects.filter(id__in=agents_reserves_ids)
        
        # Récupérer les agents NON réservés
        agents_non_reserves = Agent.objects.filter(
            voiture_personnelle=False
        ).exclude(id__in=agents_reserves_ids).order_by('nom')
        
        # Récupérer les heures de transport
        heures_ramassage = HeureTransport.objects.filter(
            type_transport='ramassage',
            active=True
        ).order_by('ordre')
        
        heures_depart = HeureTransport.objects.filter(
            type_transport='depart', 
            active=True
        ).order_by('ordre')
        
        # Compter par chauffeur
        stats_par_chauffeur = {}
        total_reservations = reservations.count()
        
        for reservation in reservations:
            chauffeur_id = reservation.chauffeur.id
            if chauffeur_id not in stats_par_chauffeur:
                stats_par_chauffeur[chauffeur_id] = {
                    'chauffeur_id': chauffeur_id,
                    'chauffeur_nom': reservation.chauffeur.nom,
                    'total': 0,
                    'ramassage': 0,
                    'depart': 0,
                    'reservations': []
                }
            
            stats_par_chauffeur[chauffeur_id]['total'] += 1
            if reservation.type_transport == 'ramassage':
                stats_par_chauffeur[chauffeur_id]['ramassage'] += 1
            else:
                stats_par_chauffeur[chauffeur_id]['depart'] += 1
            
            stats_par_chauffeur[chauffeur_id]['reservations'].append({
                'id': reservation.id,
                'agent_id': reservation.agent.id,
                'agent_nom': reservation.agent.nom,
                'agent_telephone': reservation.agent.telephone,
                'agent_societe': reservation.agent.get_societe_display(),
                'type_transport': reservation.type_transport,
                'type_display': 'Ramassage' if reservation.type_transport == 'ramassage' else 'Départ',
                'heure': reservation.heure_transport.heure,
                'heure_libelle': reservation.heure_transport.libelle,
                'statut': reservation.statut,
                'statut_display': reservation.get_statut_display(),
                'notes': reservation.notes or ''
            })
        
        # Préparer la liste des agents non réservés
        agents_non_reserves_list = []
        for agent in agents_non_reserves:
            agents_non_reserves_list.append({
                'id': agent.id,
                'nom': agent.nom,
                'telephone': agent.telephone or 'Non spécifié',
                'societe': agent.get_societe_display(),
                'adresse': agent.adresse or 'Non spécifiée',
                'est_complet': agent.est_complet() if hasattr(agent, 'est_complet') else True
            })
        
        # Calculer les statistiques
        total_agents = tous_agents.count()
        agents_reserves_count = agents_reserves.count()
        agents_non_reserves_count = agents_non_reserves.count()
        
        # Préparer la réponse
        return JsonResponse({
            'success': True,
            'is_super_chauffeur': True,
            'date_demain': demain.strftime('%Y-%m-%d'),
            'date_demain_display': demain.strftime('%d/%m/%Y'),
            
            # Données réservations
            'total_reservations': total_reservations,
            'chauffeurs': list(stats_par_chauffeur.values()),
            
            # Données agents
            'agents_non_reserves': agents_non_reserves_list,
            
            # Statistiques
            'stats': {
                'total_chauffeurs': len(stats_par_chauffeur),
                'total_reservations': total_reservations,
                'reservations_ramassage': sum(c['ramassage'] for c in stats_par_chauffeur.values()),
                'reservations_depart': sum(c['depart'] for c in stats_par_chauffeur.values()),
                'total_agents': total_agents,
                'agents_reserves': agents_reserves_count,
                'agents_non_reserves': agents_non_reserves_count,
                'pourcentage_reserves': round((agents_reserves_count / total_agents * 100) if total_agents > 0 else 0, 1),
                'pourcentage_disponibles': round((agents_non_reserves_count / total_agents * 100) if total_agents > 0 else 0, 1)
            },
            
            # Heures
            'heures_ramassage': [
                {'id': h.id, 'heure': h.heure, 'libelle': h.libelle}
                for h in heures_ramassage
            ],
            'heures_depart': [
                {'id': h.id, 'heure': h.heure, 'libelle': h.libelle}
                for h in heures_depart
            ]
        })
        
    except Exception as e:
        print(f"❌ Erreur api_super_reservations_demain: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})

