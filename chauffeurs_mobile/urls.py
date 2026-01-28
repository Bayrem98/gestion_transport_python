from django.urls import path
from . import views

app_name = 'chauffeurs_mobile'

urlpatterns = [
    path('', views.mobile_login_view, name='mobile_home'),
    # Pages web ESSENTIELLES
    path('login/', views.mobile_login_view, name='mobile_login'),
    path('dashboard/', views.mobile_dashboard_view, name='mobile_dashboard'),
    path('selection/', views.mobile_selection_view, name='mobile_selection'),
    path('historique/', views.mobile_historique_view, name='mobile_historique'),
    path('profile/', views.mobile_profile_view, name='mobile_profile'),
        # API Profil
    path('api/export/historique/', views.api_export_historique, name='mobile_api_export_historique'),
    path('api/profile/', views.api_profile, name='mobile_api_profile'),
    path('api/profile/update/', views.api_profile_update, name='mobile_api_profile_update'),
    path('api/profile/change-password/', views.api_change_password, name='mobile_api_change_password'),    # API ESSENTIELLES
    path('api/login/', views.api_login, name='mobile_api_login'),
    path('api/logout/', views.api_logout, name='mobile_api_logout'),
    path('api/dashboard/', views.api_dashboard, name='mobile_api_dashboard'),
    path('api/historique/', views.api_historique, name='mobile_api_historique'),
    path('api/courses/selection/', views.api_courses_selection, name='mobile_api_courses_selection'),
    path('api/course/creer/', views.api_creer_course, name='mobile_api_creer_course'),
    path('api/course/annuler/', views.api_annuler_course, name='mobile_api_annuler_course'),
    path('api/agents/disponibles/', views.api_agents_disponibles, name='mobile_api_agents_disponibles'),
    path('api/courses/validees/', views.api_courses_validees, name='mobile_api_courses_validees'),
    path('api/courses/en-attente/', views.api_courses_en_attente, name='mobile_api_courses_en_attente'),
    path('api/courses/annulees/', views.api_courses_annulees, name='mobile_api_courses_annulees'),
    path('api/course/terminer/', views.api_terminer_course, name='mobile_api_terminer_course'),
    path('api/course/demander-validation/', views.api_demander_validation, name='mobile_api_demander_validation'),
    path('api/reservations/demain/', views.api_reservations_demain, name='mobile_api_reservations_demain'),
    path('api/reservations/reserver/', views.api_reserver_agent, name='mobile_api_reserver_agent'),
    path('api/reservations/mes-reservations/', views.api_mes_reservations, name='mobile_api_mes_reservations'),
    path('api/reservations/annuler/<int:reservation_id>/', views.api_annuler_reservation, name='mobile_api_annuler_reservation'),
    path('api/agents/disponibles/demain/', views.api_agents_disponibles_demain, name='mobile_api_agents_disponibles_demain'),
    path('reservation/', views.mobile_reservation_view, name='mobile_reservation'),
    # NOUVELLES URLs SUPER-CHAFFEUR
    path('api/super/chauffeurs/', views.api_super_chauffeurs_list, name='mobile_api_super_chauffeurs'),
    path('api/super/chauffeur/<int:chauffeur_id>/', views.api_super_chauffeur_detail, name='mobile_api_super_chauffeur_detail'),
    path('api/super/courses/aujourdhui/', views.api_super_courses_today, name='mobile_api_super_courses_today'),
    
    # Pages web super chauffeur
    path('super/dashboard/', views.mobile_super_dashboard_view, name='mobile_super_dashboard'),
    path('super/chauffeur/<int:chauffeur_id>/', views.mobile_super_chauffeur_detail_view, name='mobile_super_chauffeur_detail'),
    path('api/super/reservations/demain/', views.api_super_reservations_demain, name='mobile_api_super_reservations_demain'),
]
