# Modèles pour l'interface mobile
from django.db import models
from django.utils import timezone

class MobileNotification(models.Model):
    
    TYPE_CHOICES = [
        ('validation', 'Demande de validation'),
        ('info', 'Information'),
        ('alerte', 'Alerte'),
    ]
    
    chauffeur = models.ForeignKey('gestion.Chauffeur', on_delete=models.CASCADE)
    type_notification = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.TextField()
    vue = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Notification mobile"
        verbose_name_plural = "Notifications mobiles"
    
    def __str__(self):
        return f"{self.chauffeur.nom} - {self.message[:50]}"

class MobileCourseStatus(models.Model):
    
    STATUS_CHOICES = [
        ('a_faire', 'À faire'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('validee', 'Validée'),
        ('probleme', 'Problème'),
    ]
    
    course = models.ForeignKey('gestion.Course', on_delete=models.CASCADE)
    chauffeur = models.ForeignKey('gestion.Chauffeur', on_delete=models.CASCADE)
    statut_mobile = models.CharField(max_length=20, choices=STATUS_CHOICES, default='a_faire')
    heure_reelle = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Statut mobile"
        verbose_name_plural = "Statuts mobiles"
        unique_together = ['course', 'chauffeur']
    
    def __str__(self):
        return f"{self.course} - {self.get_statut_mobile_display()}"
