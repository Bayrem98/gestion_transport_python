import pandas as pd
import re
from datetime import datetime, timedelta
import os
from django.conf import settings
from django.core.cache import cache
from .models import HeureTransport, Affectation, Agent, Course, Societe

class GestionnaireTransport:
    def get_heures_config(self, type_transport):
        cache_key = f'heures_config_{type_transport}'
        heures = cache.get(cache_key)
        if not heures:
            heures = HeureTransport.objects.filter(
                type_transport=type_transport, 
                active=True
            ).order_by('ordre')
            cache.set(cache_key, heures, 3600)  # Cache 1 heure
        return [(heure_obj.heure, heure_obj.libelle) for heure_obj in heures]
    def __init__(self):
        self.df_planning = None
        self.df_agents = None
        self.dates_par_jour = {}
        self.temp_path = os.path.join(settings.BASE_DIR, 'temp_planning.xlsx')
        
    def charger_planning(self, fichier):
        try:
            with open(self.temp_path, 'wb+') as destination:
                for chunk in fichier.chunks():
                    destination.write(chunk)
            
            self.extraire_dates_reelles(self.temp_path)
            
            self.df_planning = pd.read_excel(self.temp_path, skiprows=2, header=None)
            self.df_planning = self.df_planning.dropna(how='all').reset_index(drop=True)
            
            noms_colonnes = ['Salarie', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche', 'Qualification']
            
            if len(self.df_planning.columns) > len(noms_colonnes):
                self.df_planning = self.df_planning.iloc[:, :len(noms_colonnes)]
            
            self.df_planning.columns = noms_colonnes[:len(self.df_planning.columns)]
                
            return True
                
        except Exception as e:
            print(f"Erreur chargement planning: {e}")
            return False

    def charger_agents_excel(self, fichier):
        "Charge les agents depuis un fichier Excel uploadé"
        try:
            with open(os.path.join(settings.BASE_DIR, 'temp_agents.xlsx'), 'wb+') as destination:
                for chunk in fichier.chunks():
                    destination.write(chunk)
            
            self.df_agents = pd.read_excel(os.path.join(settings.BASE_DIR, 'temp_agents.xlsx'))
            return True
        except Exception as e:
            print(f"Erreur chargement agents: {e}")
            return False

    def recharger_planning_depuis_session(self):
        try:
            if os.path.exists(self.temp_path):
                self.extraire_dates_reelles(self.temp_path)
                
                self.df_planning = pd.read_excel(self.temp_path, skiprows=2, header=None)
                self.df_planning = self.df_planning.dropna(how='all').reset_index(drop=True)
                
                noms_colonnes = ['Salarie', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche', 'Qualification']
                if len(self.df_planning.columns) > len(noms_colonnes):
                    self.df_planning = self.df_planning.iloc[:, :len(noms_colonnes)]
                
                self.df_planning.columns = noms_colonnes[:len(self.df_planning.columns)]
                self.extraire_dates_reelles(self.temp_path)
                print(f"📅 Dates extraites après rechargement: {self.dates_par_jour}")
                return True
            else:
                return False
        except Exception as e:
            print(f"Erreur rechargement planning: {e}")
            return False

    def extraire_dates_reelles(self, fichier_path):
      
        try:
            print("📅 Tentative d'extraction des dates depuis le fichier Excel...")
            
            # Méthode 1: Lire le fichier avec pandas
            df_raw = pd.read_excel(fichier_path, header=None)
            
            # Chercher la ligne contenant les dates
            date_row_index = None
            for idx in range(min(3, len(df_raw))):  # Regarder les 3 premières lignes
                row = df_raw.iloc[idx]
                # Vérifier si cette ligne contient des dates
                date_count = 0
                for cell in row:
                    if pd.notna(cell):
                        cell_str = str(cell)
                        # Rechercher des motifs de date
                        if re.search(r'\d{1,2}[\/\-]\d{1,2}', cell_str):
                            date_count += 1
                
                if date_count >= 3:  # Si au moins 3 cellules semblent être des dates
                    date_row_index = idx
                    break
            
            if date_row_index is not None:
                date_row = df_raw.iloc[date_row_index]
                print(f"📊 Ligne de dates trouvée à l'index {date_row_index}")
                
                # Mapping des colonnes vers les jours
                colonne_vers_jour = {
                    1: 'Lundi', 2: 'Mardi', 3: 'Mercredi', 4: 'Jeudi',
                    5: 'Vendredi', 6: 'Samedi', 7: 'Dimanche'
                }
                
                for col_idx, jour_nom in colonne_vers_jour.items():
                    if col_idx < len(date_row):
                        cell_value = date_row[col_idx]
                        
                        if pd.notna(cell_value):
                            cell_str = str(cell_value).strip()
                            print(f"  {jour_nom}: '{cell_str}'")
                            
                            # Essayer de convertir en date
                            try:
                                # Si c'est déjà un objet datetime
                                if isinstance(cell_value, (datetime, pd.Timestamp)):
                                    date_obj = cell_value
                                else:
                                    # Essayer de parser la chaîne
                                    date_formats = [
                                        '%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y',
                                        '%d/%m', '%d-%m', '%d %B %Y', '%d %b %Y'
                                    ]
                                    
                                    date_obj = None
                                    for fmt in date_formats:
                                        try:
                                            date_obj = datetime.strptime(cell_str, fmt)
                                            # Si l'année n'est pas spécifiée, ajouter l'année courante
                                            if date_obj.year == 1900:
                                                date_obj = date_obj.replace(year=datetime.now().year)
                                            break
                                        except ValueError:
                                            continue
                                
                                if date_obj:
                                    self.dates_par_jour[jour_nom] = date_obj.strftime("%d/%m/%Y")
                                    print(f"    ✅ Converti en: {self.dates_par_jour[jour_nom]}")
                                else:
                                    # Recherche de motif dans la chaîne
                                    match = re.search(r'(\d{1,2})[\/\-](\d{1,2})', cell_str)
                                    if match:
                                        jour = int(match.group(1))
                                        mois = int(match.group(2))
                                        annee = datetime.now().year
                                        try:
                                            date_obj = datetime(annee, mois, jour)
                                            self.dates_par_jour[jour_nom] = date_obj.strftime("%d/%m/%Y")
                                            print(f"    ✅ Extrait: {self.dates_par_jour[jour_nom]}")
                                        except:
                                            pass
                            except Exception as e:
                                print(f"    ❌ Erreur conversion: {e}")
            
            # Si aucune date n'a été extraite, générer des dates par défaut
            if not self.dates_par_jour:
                print("⚠️ Aucune date extraite, génération automatique...")
                self.generer_dates_par_defaut()
            
            print("📅 Résultat de l'extraction des dates:", self.dates_par_jour)
                
        except Exception as e:
            print(f"❌ Erreur lors de l'extraction des dates: {e}")
            import traceback
            traceback.print_exc()
            print("📅 Génération des dates par défaut...")
            self.generer_dates_par_defaut()

    def charger_agents(self, fichier_path):
        try:
            self.df_agents = pd.read_excel(fichier_path)
            return True
        except Exception as e:
            print(f"Erreur chargement agents: {e}")
            return False
    
    def calculer_date_par_defaut(self, jour_nom):
        aujourd_hui = datetime.now()
        jours_semaine = {'Lundi': 0, 'Mardi': 1, 'Mercredi': 2, 'Jeudi': 3, 'Vendredi': 4, 'Samedi': 5, 'Dimanche': 6}
        
        if jour_nom in jours_semaine:
            jour_cible = jours_semaine[jour_nom]
            jour_actuel = aujourd_hui.weekday()
            
            decalage = (jour_cible - jour_actuel) % 7
            if decalage == 0:
                decalage = 7
            
            date_calculee = aujourd_hui + timedelta(days=decalage)
            return date_calculee.strftime("%d/%m/%Y")
        
        return aujourd_hui.strftime("%d/%m/%Y")
    
    def generer_dates_par_defaut(self):
        aujourd_hui = datetime.now()
        jours_ordre = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        
        jour_actuel = aujourd_hui.weekday()
        jours_vers_lundi = (0 - jour_actuel) % 7
        date_debut = aujourd_hui + timedelta(days=jours_vers_lundi)
        
        for i, jour in enumerate(jours_ordre):
            date_jour = date_debut + timedelta(days=i)
            self.dates_par_jour[jour] = date_jour.strftime("%d/%m/%Y")
    
    def get_info_agent(self, nom_agent):
        try:
            # Chercher l'agent dans la base de données
            agent_db = Agent.objects.filter(nom__icontains=nom_agent).first()
            if agent_db:
                return {
                    "adresse": agent_db.adresse,
                    "telephone": agent_db.telephone,
                    "societe": agent_db.get_societe_display(),
                    "voiture_personnelle": agent_db.voiture_personnelle,
                    "est_complet": agent_db.est_complet(),
                    "agent_obj": agent_db  # Ajouter l'objet agent pour récupérer l'ID
                }
            else:
                # Si l'agent n'existe pas, le créer avec des valeurs par défaut
                agent = Agent.objects.create(
                    nom=nom_agent,
                    adresse="Adresse à compléter",
                    telephone="00000000",
                    societe_texte="Société à compléter",
                    voiture_personnelle=False
                )
                return {
                    "adresse": agent.adresse,
                    "telephone": agent.telephone,
                    "societe": agent.get_societe_display(),
                    "voiture_personnelle": agent.voiture_personnelle,
                    "est_complet": agent.est_complet(),
                    "agent_obj": agent
                }
                
        except Exception as e:
            print(f"Erreur recherche/création agent {nom_agent}: {e}")
            return {
                "adresse": "Adresse non renseignee",
                "telephone": "Telephone non renseigne", 
                "societe": "Societe non renseignee",
                "voiture_personnelle": False,
                "est_complet": False,
                "agent_obj": None
            }

    def extraire_heures(self, planning_str):
        if pd.isna(planning_str) or str(planning_str).strip() in ['', 'REPOS', 'ABSENCE', 'OFF', 'MALADIE', 'CONGÉ PAYÉ', 'CONGÉ MATERNITÉ']:
            return None, None
        
        texte = str(planning_str).strip().upper()
        
        # CORRECTION COMPLÈTE DES REGEX
        texte_propre = re.sub(r'[^0-9H\s\-:]', ' ', texte)
        texte_propre = re.sub(r'\s+', ' ', texte_propre).strip()
        
        patterns = [
            r'(\d{1,2})H?\s*[-]\s*(\d{1,2})H?',
            r'(\d{1,2})H\s*(\d{1,2})H',
            r'(\d{1,2})\s*[-]\s*(\d{1,2})',
            r'R\s*(\d{1,2})H?\s*[-]\s*(\d{1,2})H?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, texte_propre)
            if match:
                heure_debut = int(match.group(1))
                heure_fin = int(match.group(2))
                
                if heure_fin < heure_debut and heure_fin < 12:
                    heure_fin += 24
                
                return heure_debut, heure_fin
        
        heures_trouvees = re.findall(r'\b\d{1,2}\b', texte_propre)
        if len(heures_trouvees) >= 2:
            heure_debut = int(heures_trouvees[0])
            heure_fin = int(heures_trouvees[1])
            
            if heure_fin < heure_debut and heure_fin < 12:
                heure_fin += 24
            
            return heure_debut, heure_fin
        
        return None, None
    
    def get_heures_config(self, type_transport):
        "Retourne les heures configurées pour un type de transport donné"
        try:
            heures = HeureTransport.objects.filter(
                type_transport=type_transport, 
                active=True
            ).order_by('ordre')
            return [(heure_obj.heure, heure_obj.libelle) for heure_obj in heures]
        except:
            # Valeurs par défaut
            if type_transport == 'ramassage':
                return [(6, 'Ramassage 6h'), (7, 'Ramassage 7h'), (8, 'Ramassage 8h'), (22, 'Ramassage 22h')]
            else:
                return [(22, 'Départ 22h'), (23, 'Départ 23h'), (0, 'Départ 0h'), (1, 'Départ 1h'), (2, 'Départ 2h'), (3, 'Départ 3h')]

    def traiter_donnees(self, filtre_form):
        if self.df_planning is None or self.df_planning.empty:
            return []
        
        liste_transports = []
        
        jour_selectionne = filtre_form.cleaned_data.get('jour', 'Tous')
        type_transport_selectionne = filtre_form.cleaned_data.get('type_transport', 'tous')
        heure_ete_active = filtre_form.cleaned_data.get('heure_ete', False)
        filtre_agents = filtre_form.cleaned_data.get('filtre_agents', 'tous')
        
        # Récupérer les paramètres GET pour les heures spécifiques
        request_data = filtre_form.data if hasattr(filtre_form, 'data') else {}
        
        # Détecter les heures spécifiques cochées
        heures_ramassage_selectionnees = []
        heures_depart_selectionnees = []
        
        for key, value in request_data.items():
            if key.startswith('ramassage_') and value == 'true':
                try:
                    heure = int(key.replace('ramassage_', '').replace('h', ''))
                    heures_ramassage_selectionnees.append(heure)
                except:
                    pass
            elif key.startswith('depart_') and value == 'true':
                try:
                    heure = int(key.replace('depart_', '').replace('h', ''))
                    heures_depart_selectionnees.append(heure)
                except:
                    pass
        
        # Récupérer les heures configurées
        if type_transport_selectionne in ['tous', 'ramassage']:
            heures_ramassage_config = self.get_heures_config('ramassage')
            heures_ramassage = [heure for heure, libelle in heures_ramassage_config]
        else:
            heures_ramassage = []
        
        if type_transport_selectionne in ['tous', 'depart']:
            heures_depart_config = self.get_heures_config('depart')
            heures_depart = [heure for heure, libelle in heures_depart_config]
        else:
            heures_depart = []
        
        # Filtrer par heures spécifiques si sélectionnées
        if heures_ramassage_selectionnees and type_transport_selectionne in ['tous', 'ramassage']:
            heures_ramassage = [h for h in heures_ramassage if h in heures_ramassage_selectionnees]
        
        if heures_depart_selectionnees and type_transport_selectionne in ['tous', 'depart']:
            heures_depart = [h for h in heures_depart if h in heures_depart_selectionnees]
        
        # Si heure_specifique est fournie, utiliser uniquement cette heure
        if 'heure_specifique' in request_data and request_data['heure_specifique']:
            try:
                heure_specifique = int(request_data['heure_specifique'])
                if type_transport_selectionne == 'ramassage':
                    heures_ramassage = [heure_specifique] if heure_specifique in heures_ramassage else []
                elif type_transport_selectionne == 'depart':
                    heures_depart = [heure_specifique] if heure_specifique in heures_depart else []
                else:  # 'tous'
                    if heure_specifique in heures_ramassage:
                        heures_ramassage = [heure_specifique]
                        heures_depart = []
                    elif heure_specifique in heures_depart:
                        heures_depart = [heure_specifique]
                        heures_ramassage = []
            except:
                pass
        
        jours_mapping = {
            'Lundi': 'Lundi', 'Mardi': 'Mardi', 'Mercredi': 'Mercredi', 
            'Jeudi': 'Jeudi', 'Vendredi': 'Vendredi', 'Samedi': 'Samedi', 'Dimanche': 'Dimanche'
        }
        
        for index, agent in self.df_planning.iterrows():
            if pd.isna(agent['Salarie']) or str(agent['Salarie']).strip() == '':
                continue
            
            nom_agent = str(agent['Salarie']).strip()
            info_agent = self.get_info_agent(nom_agent)
            
            # Appliquer le filtre agents complet/incomplet
            if filtre_agents == 'complets' and not info_agent['est_complet']:
                continue
            elif filtre_agents == 'incomplets' and info_agent['est_complet']:
                continue
            
            # EXCLUSION AUTOMATIQUE - Si l'agent a une voiture personnelle, on le saute complètement
            if info_agent['voiture_personnelle']:
                continue
            
            jours_a_verifier = []
            if jour_selectionne == 'Tous':
                for jour_col, jour_nom in jours_mapping.items():
                    if jour_col in agent.index:
                        jours_a_verifier.append((jour_col, jour_nom))
            else:
                if jour_selectionne in agent.index:
                    jours_a_verifier.append((jour_selectionne, jour_selectionne))
            
            for jour_col, jour_nom in jours_a_verifier:
                planning = agent[jour_col]
                heure_debut, heure_fin = self.extraire_heures(planning)
                
                if heure_debut is not None and heure_fin is not None:
                    if heure_ete_active:
                        heure_debut_ajustee = heure_debut - 1
                        heure_fin_ajustee = heure_fin - 1
                    else:
                        heure_debut_ajustee = heure_debut
                        heure_fin_ajustee = heure_fin
                    
                    # Ramassage - Vérifier avec l'heure ajustée
                    if type_transport_selectionne in ['tous', 'ramassage'] and heure_debut_ajustee in heures_ramassage:
                        agent_data = {
                            'agent': nom_agent,
                            'jour': jour_nom,
                            'heure': heure_debut_ajustee,
                            'heure_affichage': f"{heure_debut_ajustee}h",
                            'adresse': info_agent['adresse'],
                            'telephone': info_agent['telephone'],
                            'societe': info_agent['societe'],
                            'date_reelle': self.dates_par_jour.get(jour_nom, 'Date non definie'),
                            'type_transport': 'ramassage',
                            'est_complet': info_agent['est_complet'],
                            'agent_id': info_agent['agent_obj'].id if info_agent['agent_obj'] else None
                        }
                        liste_transports.append(agent_data)
                    
                    # Départ - Vérifier avec l'heure ajustée
                    heure_fin_comparaison = heure_fin_ajustee
                    if heure_fin_comparaison >= 24:
                        heure_fin_comparaison = heure_fin_comparaison - 24
                    
                    if type_transport_selectionne in ['tous', 'depart'] and heure_fin_comparaison in heures_depart:
                        heure_fin_affichee = heure_fin_ajustee
                        if heure_fin_ajustee >= 24:
                            heure_fin_affichee = heure_fin_ajustee - 24
                        
                        agent_data = {
                            'agent': nom_agent,
                            'jour': jour_nom,
                            'heure': heure_fin_ajustee,
                            'heure_affichage': f"{heure_fin_affichee}h",
                            'adresse': info_agent['adresse'],
                            'telephone': info_agent['telephone'],
                            'societe': info_agent['societe'],
                            'date_reelle': self.dates_par_jour.get(jour_nom, 'Date non definie'),
                            'type_transport': 'depart',
                            'est_complet': info_agent['est_complet'],
                            'agent_id': info_agent['agent_obj'].id if info_agent['agent_obj'] else None
                        }
                        liste_transports.append(agent_data)
        
        ordre_jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        liste_transports.sort(key=lambda x: (ordre_jours.index(x['jour']), x['type_transport'], x['heure']))
        
        return liste_transports

    def get_agents_non_affectes(self, jour, type_transport, heure, date_reelle):
        "Retourne les agents non encore affectés pour ce jour/type/heure"
        try:
            # Convertir la date
            date_obj = datetime.strptime(date_reelle, "%d/%m/%Y").date()
            
            # Agents déjà affectés
            agents_affectes = Affectation.objects.filter(
                jour=jour,
                type_transport=type_transport,
                heure=heure,
                date_reelle=date_obj
            ).values_list('agent__nom', flat=True)
            
            # Filtrer les agents du planning qui ne sont pas encore affectés
            agents_non_affectes = []
            
            if self.df_planning is not None:
                for index, agent in self.df_planning.iterrows():
                    if pd.isna(agent['Salarie']) or str(agent['Salarie']).strip() == '':
                        continue
                    
                    nom_agent = str(agent['Salarie']).strip()
                    
                    # Vérifier si l'agent est déjà affecté
                    if nom_agent not in agents_affectes:
                        info_agent = self.get_info_agent(nom_agent)
                        
                        # Vérifier si l'agent a une voiture personnelle
                        if not info_agent['voiture_personnelle']:
                            agents_non_affectes.append(nom_agent)
            
            return agents_non_affectes
            
        except Exception as e:
            print(f"Erreur get_agents_non_affectes: {e}")
            return []
