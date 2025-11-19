import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pitching_day.settings')
django.setup()

from judging.models import Team

teams_data = [
    {
        'project_name': 'SolarCharge',
        'short_description': 'Portable solar charger for bicycles and electric vehicles. Harnesses solar energy to provide sustainable charging solutions for mobile devices and small electronics.',
        'members': 'Alice Johnson;Bob Smith;Eve Williams',
        'image_path': '/uploads/teams/solarcharge.jpg',
        'extra_info': {'stage': 'prototype', 'industry': 'clean-energy'}
    },
    {
        'project_name': 'HealthTracker AI',
        'short_description': 'AI-powered health monitoring app that uses machine learning to track vital signs, predict health issues, and provide personalized wellness recommendations.',
        'members': 'John Davis;Sarah Martinez',
        'image_path': '/uploads/teams/healthtracker.jpg',
        'extra_info': {'stage': 'beta', 'industry': 'health-tech'}
    },
    {
        'project_name': 'EduTech Platform',
        'short_description': 'Online learning platform for kids with interactive games, personalized learning paths, and parent progress tracking. Makes education fun and engaging.',
        'members': 'Mike Chen;Emma Wilson;David Brown',
        'image_path': '/uploads/teams/edutech.png',
        'extra_info': {'stage': 'beta', 'industry': 'edtech', 'target_age': '5-12'}
    },
    {
        'project_name': 'FoodWaste Solutions',
        'short_description': 'App connecting restaurants with surplus food to local charities and food banks. Reduces food waste while helping feed communities.',
        'members': 'Lisa Anderson;Tom Rodriguez',
        'image_path': '/uploads/teams/foodwaste.jpg',
        'extra_info': {'stage': 'prototype', 'industry': 'social-impact'}
    },
    {
        'project_name': 'SmartHome Hub',
        'short_description': 'Centralized smart home control system that integrates all IoT devices, provides voice control, and learns user preferences for automation.',
        'members': 'Jennifer Lee;Robert Kim',
        'image_path': '/uploads/teams/smarthome.jpg',
        'extra_info': {'stage': 'prototype', 'industry': 'iot'}
    }
]

created_count = 0
for team_data in teams_data:
    team, created = Team.objects.get_or_create(
        project_name=team_data['project_name'],
        defaults=team_data
    )
    if created:
        created_count += 1
        print(f'✅ Created: {team.project_name}')
    else:
        print(f'ℹ️  Already exists: {team.project_name}')

print(f'\n📊 Created {created_count} new teams')
print(f'📊 Total teams in database: {Team.objects.count()}')
