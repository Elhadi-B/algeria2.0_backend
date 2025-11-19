#!/usr/bin/env python
"""Quick script to add sample teams"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pitching_day.settings')
django.setup()

from judging.models import Team

teams = [
    Team(project_name='SolarCharge', short_description='Portable solar charger for bicycles', members='Alice;Bob;Eve', image_path='/uploads/solar.jpg'),
    Team(project_name='HealthTracker AI', short_description='AI-powered health monitoring app', members='John;Sarah', image_path='/uploads/health.jpg'),
    Team(project_name='EduTech Platform', short_description='Online learning platform for kids', members='Mike;Emma;David', image_path='/uploads/edutech.png'),
    Team(project_name='FoodWaste Solutions', short_description='App connecting restaurants with surplus food to charities', members='Lisa;Tom', image_path='/uploads/foodwaste.jpg'),
    Team(project_name='SmartHome Hub', short_description='Centralized smart home control system', members='Jennifer;Robert', image_path='/uploads/smarthome.jpg'),
]

for team in teams:
    team.save()
    print(f'Created: {team.project_name}')

print(f'\nTotal teams: {Team.objects.count()}')
