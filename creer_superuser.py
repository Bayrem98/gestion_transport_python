import os
import django
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transport_app.settings')
django.setup()

from gestion.models import Agent, Affectation, Course
import pandas as pd
from datetime import datetime

def verifier_et_creer_agents():
    print("🔍 Vérification des agents dans la base de données...")
    
    # Vérifier les agents liés aux affectations
    affectations = Affectation.objects.all().select_related('agent')
    
    agents_problemes = []
    for affectation in affectations:
        agent = affectation.agent
        print(f"Agent: {agent.nom} (ID: {agent.id}) - {affectation.course}")
        
        if agent.id <= 0:
            agents_problemes.append(agent)
    
    if agents_problemes:
        print(f"⚠️ {len(agents_problemes)} agents avec ID problématique")
        
        # Solution: recréer les agents depuis le planning
        print("🔄 Recréation des agents depuis le planning...")
        
        # Charger le planning
        planning_path = os.path.join('gestion_transport', 'EMS.xlsx')
        if os.path.exists(planning_path):
            try:
                df = pd.read_excel(planning_path, skiprows=2, header=None)
                df.columns = ['Salarie', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche', 'Qualification']
                
                agents_crees = 0
                for index, row in df.iterrows():
                    nom_agent = str(row['Salarie']).strip()
                    if nom_agent and nom_agent not in ['', 'nan', 'None']:
                        # Vérifier si l'agent existe déjà
                        agent, created = Agent.objects.get_or_create(
                            nom=nom_agent,
                            defaults={
                                'adresse': 'Adresse à compléter',
                                'telephone': '00000000',
                                'societe_texte': 'Société à compléter',
                                'voiture_personnelle': False
                            }
                        )
                        
                        if created:
                            agents_crees += 1
                            print(f"✅ Agent créé: {agent.nom} (ID: {agent.id})")
                
                print(f"🎉 {agents_crees} agents créés avec succès")
                
            except Exception as e:
                print(f"❌ Erreur lors de la lecture du planning: {e}")
    else:
        print("✅ Tous les agents ont des IDs valides")
    
    # Afficher le nombre total d'agents
    total_agents = Agent.objects.count()
    print(f"📊 Total agents en base de données: {total_agents}")
    
    # Afficher les 10 premiers agents
    print("
📋 Liste des 10 premiers agents:")
    for agent in Agent.objects.all()[:10]:
        print(f"  - {agent.id}: {agent.nom}")

if __name__ == "__main__":
    verifier_et_creer_agents()

from django.contrib.auth.models import User
from gestion.models import Societe, HeureTransport, Agent, Chauffeur, Course

def creer_donnees_par_defaut():
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@transport.com',
            password='admin123'
        )
        print("SUPER UTILISATEUR CREE : admin / admin123")
    else:
        print("SUPER UTILISATEUR EXISTE DEJA")
    
    # Créer des sociétés par défaut
    societes_par_defaut = [
        {
            'nom': 'Hannibal',
            'matricule_fiscale': 'MF1238010ZAM000',
            'adresse': 'Rue rabat complexe zaoui sousse 4000',
            'telephone': '73213830',
            'email': 'compta@astragale-tunisie.com',
            'contact_personne': 'ATEF'
        },
        {
            'nom': 'ASTRAGALE',
            'matricule_fiscale': 'MF1157457DAM000',
            'adresse': 'Rue rabat complexe zaoui sousse 4000',
            'telephone': '73213830',
            'email': 'compta@astragale-tunisie.com',
            'contact_personne': 'ATEF'
        },
        {
            'nom': 'ULYSSE',
            'matricule_fiscale': 'MF1317377WAM',
            'adresse': 'Rue rabat complexe zaoui sousse 4000',
            'telephone': '73213830',
            'email': 'compta@astragale-tunisie.com',
            'contact_personne': 'ATEF'
        },
        {
            'nom': 'PENELOPE',
            'matricule_fiscale': 'MF1317388TAM',
            'adresse': 'Rue rabat complexe zaoui sousse 4000',
            'telephone': '73213830',
            'email': 'compta@astragale-tunisie.com',
            'contact_personne': 'ATEF'
        },
    ]
    
    for societe_data in societes_par_defaut:
        societe, created = Societe.objects.get_or_create(
            nom=societe_data['nom'],
            defaults=societe_data
        )
        if created:
            print(f"Société créée: {societe}")
    
    print("Sociétés par défaut créées avec succès")
    
    heures_par_defaut = [
        {'type_transport': 'ramassage', 'heure': 6, 'libelle': 'Ramassage 6h', 'ordre': 1, 'active': True},
        {'type_transport': 'ramassage', 'heure': 7, 'libelle': 'Ramassage 7h', 'ordre': 2, 'active': True},
        {'type_transport': 'ramassage', 'heure': 8, 'libelle': 'Ramassage 8h', 'ordre': 3, 'active': True},
        {'type_transport': 'ramassage', 'heure': 22, 'libelle': 'Ramassage 22h', 'ordre': 4, 'active': True},
        
        {'type_transport': 'depart', 'heure': 22, 'libelle': 'Départ 22h', 'ordre': 1, 'active': True},
        {'type_transport': 'depart', 'heure': 23, 'libelle': 'Départ 23h', 'ordre': 2, 'active': True},
        {'type_transport': 'depart', 'heure': 0, 'libelle': 'Départ 0h', 'ordre': 3, 'active': True},
        {'type_transport': 'depart', 'heure': 1, 'libelle': 'Départ 1h', 'ordre': 4, 'active': True},
        {'type_transport': 'depart', 'heure': 2, 'libelle': 'Départ 2h', 'ordre': 5, 'active': True},
        {'type_transport': 'depart', 'heure': 3, 'libelle': 'Départ 3h', 'ordre': 6, 'active': True},
    ]
    
    for heure_data in heures_par_defaut:
        heure, created = HeureTransport.objects.get_or_create(
            type_transport=heure_data['type_transport'],
            heure=heure_data['heure'],
            defaults={
                'libelle': heure_data['libelle'],
                'ordre': heure_data['ordre'],
                'active': heure_data['active']
            }
        )
        if created:
            print(f"Heure créée: {heure}")
    
    print("Heures de transport par défaut créées avec succès")
    
    # Récupérer les sociétés créées
    hannibal = Societe.objects.get(nom='Hannibal')
    ASTRAGALE = Societe.objects.get(nom='ASTRAGALE')
    ULYSSE = Societe.objects.get(nom='ULYSSE')
    
    agents_test = [
        {
            'nom': 'Aalya (Leila SAID)',
            'adresse': 'Cite ghodrane 3045 maison n°131',
            'telephone': '95021416',
            'societe': hannibal,
            'voiture_personnelle': False
        },
        {
            'nom': 'Abby (Takwa GUIZENI)',
            'adresse': 'hay riadh',
            'telephone': '58053355', 
            'societe': hannibal,
            'voiture_personnelle': False
        },
        {
            'nom': 'Adel (Adel BOUAFIA)',
            'adresse': 'hay riadh',
            'telephone': '22084242',
            'societe': hannibal,
            'voiture_personnelle': True
        },
        {
            'nom': 'Mohamed BEN ALI',
            'adresse': 'Ariana Ville',
            'telephone': '12345678',
            'societe': ASTRAGALE,
            'voiture_personnelle': False
        },
        {
            'nom': 'Sophie DUPONT',
            'adresse': 'Lac 2',
            'telephone': '87654321',
            'societe': ULYSSE,
            'voiture_personnelle': False
        }
    ]
    
    for agent_data in agents_test:
        agent, created = Agent.objects.get_or_create(
            nom=agent_data['nom'],
            defaults=agent_data
        )
        if created:
            print(f"Agent créé: {agent}")
    
    print("Agents de test créés avec succès")
    
    # Créer des chauffeurs par défaut
    chauffeurs_par_defaut = [
        {
            'nom': 'Ali Ben Ahmed',
            'type_chauffeur': 'taxi',
            'telephone': '12345678',
            'numero_identite': '12345678',
            'numero_voiture': '205TU1234',
            'societe': '',
            'prix_course_par_defaut': 15.0
        },
        {
            'nom': 'Mohamed Trabelsi',
            'type_chauffeur': 'prive',
            'telephone': '87654321',
            'numero_identite': '87654321',
            'numero_voiture': '136TU5678',
            'societe': 'Transport Plus',
            'prix_course_par_defaut': 10.0
        },
        {
            'nom': 'Karim Société',
            'type_chauffeur': 'societe',
            'telephone': '55555555',
            'numero_identite': '55555555',
            'numero_voiture': '100TU9999',
            'societe': 'Société Transport',
            'prix_course_par_defaut': 0.0
        },
    ]
    
    for chauffeur_data in chauffeurs_par_defaut:
        chauffeur, created = Chauffeur.objects.get_or_create(
            nom=chauffeur_data['nom'],
            defaults=chauffeur_data
        )
        if created:
            print(f"Chauffeur créé: {chauffeur}")
    
    print("Chauffeurs par défaut créés avec succès")
    
    # ============ AJOUT DU POINT DE DÉPART FIXE ============
    print("
🔄 Configuration du point de départ fixe pour toutes les courses...")
    
    # Vérifier et mettre à jour les courses existantes
    from gestion.models import Course
    courses = Course.objects.all()
   
    courses_mises_a_jour = 0
    for course in courses:
        if not course.point_depart_adresse:
            course.point_depart_adresse = "rue rabat complexe zaoui sousse 4000"
            course.point_depart_latitude = 35.8338
            course.point_depart_longitude = 10.6296
            course.save()
            courses_mises_a_jour += 1
    
    print(f"✅ {courses_mises_a_jour} courses configurées avec le point de départ fixe")
    print("📍 Adresse de départ: rue rabat complexe zaoui sousse 4000")
    print("📍 Coordonnées: Latitude 35.8342, Longitude 10.6296")
    # ========================================================
    
    print("
Liste des utilisateurs existants:")
    for user in User.objects.all():
        print(f"  - {user.username} ({user.email}) - Staff: {user.is_staff}")

if __name__ == "__main__":
    creer_donnees_par_defaut()
