from django.core.management.base import BaseCommand
from judging.models import Team


class Command(BaseCommand):
    help = 'Create sample teams for testing'

    def handle(self, *args, **options):
        # Sample teams data
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

        # Create teams
        created_teams = []
        for team_data in teams_data:
            team, created = Team.objects.get_or_create(
                project_name=team_data['project_name'],
                defaults={
                    'short_description': team_data['short_description'],
                    'members': team_data['members'],
                    'image_path': team_data['image_path'],
                    'extra_info': team_data['extra_info']
                }
            )
            if created:
                created_teams.append(team)
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created team: {team.project_name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'ℹ️  Team already exists: {team.project_name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n📊 Total teams created: {len(created_teams)}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'📊 Total teams in database: {Team.objects.count()}')
        )
